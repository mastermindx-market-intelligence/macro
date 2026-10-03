"""tests/test_mechanism_pathways.py — Mechanism Pathway Compiler v1 unit tests.

Tests cover:
- Trigger precedence order: market_drivers clear → risk_radar scare → factor
  rotation flip → snap_unattributed null; each branch individually.
- Scare→family map correctness; unattributed scares (vol, growth) emit null.
- Stale-trigger guard: stale market_drivers → no_pathway(trigger_stale).
- Insufficient-coverage null: coverage < 0.5 → no_pathway(insufficient_coverage).
- Coverage arithmetic with stale legs.
- Coherence categorical: assert no float coherence key anywhere in output.
- Schema / authority block presence.
- Language-law lint: banned words absent from all generated text.
- no_pathway records printed with reason field.
- Tie resolution: fixed precedence order.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from engine.neuralweb.mechanism_pathways import (
    AUTHORITY_BLOCK,
    SCHEMA,
    SCARE_FAMILY_MAP,
    _UNATTRIBUTED_SCARES,
    _classify_source_clock,
    _derive_coherence,
    _no_pathway,
    compile,
    contains_banned_words,
)

# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

# Fixed reference clock — every test injects this into compile() so the
# suite is wall-clock independent (F3 discipline, 2026-10-03).
_TEST_NOW = datetime(2026, 10, 2, 23, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _fixed_compiler_clock(monkeypatch):
    """Wall-clock-independent compiler clock (C1).

    Replaces the single `_utcnow` seam in mechanism_pathways so the suite
    never reads the wall clock. The fixture is applied to every test in
    this module.
    """
    monkeypatch.setattr(
        "engine.neuralweb.mechanism_pathways._utcnow",
        lambda: datetime(2026, 10, 2, 23, 0, tzinfo=timezone.utc),
    )
    return _TEST_NOW


# A fresh past asof, defined relative to the test clock (1 calendar day ago).
# Tests that previously relied on `_FRESH_ASOF = "2099-01-01"` for "always
# fresh" now use this past-but-in-window date so the new R3 future-rejection
# cannot accidentally accept it. Tests that don't exercise clock semantics
# still get the same effective behavior: in-window.
_FRESH_ASOF = (_TEST_NOW.replace(hour=0, minute=0, second=0, microsecond=0)
               - timedelta(days=1)).strftime("%Y-%m-%d")
_STALE_ASOF = "2000-01-01"  # far-past date — always stale


def _make_regime(
    md_verdict: str = "clear",
    md_primary: str = "ai_semis",
    md_runner_up: str = "china_stimulus",
    md_asof: str = _FRESH_ASOF,
    md_agreement: float = 0.80,
    md_direction: str = "AI/semis unwind",
    md_direction_zh: str = "AI/半导体回调",
    md_evidence_legs: list | None = None,
    md_scores: list | None = None,
    rr_dominant_scare: str = "",
    rr_state: str = "caution",
    rr_asof: str = _FRESH_ASOF,
    regime_one: dict | None = None,
) -> dict:
    if md_evidence_legs is None:
        md_evidence_legs = [
            {"en": "semis RS", "zh": "半导体相对强度", "z": -3.0},
            {"en": "growth vs value", "zh": "成长对价值", "z": 1.0},
        ]
    if md_scores is None:
        md_scores = [
            {"driver": "ai_semis", "label": "AI / semis", "label_zh": "AI/半导体",
             "family": "equity-leadership", "projection": -1.36, "strength": 1.36,
             "direction": "AI/semis unwind"},
            {"driver": "china_stimulus", "label": "China stimulus",
             "family": "china", "projection": -0.92, "strength": 0.92,
             "direction": "China risk-off"},
            {"driver": "credit_stress", "label": "Credit stress",
             "family": "credit", "projection": 0.5, "strength": 0.5,
             "direction": "credit widening"},
        ]
    return {
        "asof": md_asof,
        "date": md_asof,
        "market_drivers": {
            "asof": md_asof,
            "verdict": md_verdict,
            "primary": md_primary,
            "runner_up": md_runner_up,
            "agreement": md_agreement,
            "direction": md_direction,
            "direction_zh": md_direction_zh,
            "dir_sign": "-1",
            "strength": 1.36,
            "dominance_ratio": 1.48,
            "confidence": "high",
            "evidence_legs": md_evidence_legs,
            "scores": md_scores,
            "headline": md_direction,
        },
        "risk_radar": {
            "schema": "risk_radar.v2",
            "asof": rr_asof,
            "state": rr_state,
            "dominant_scare": rr_dominant_scare,
            "dominant_label_en": f"{rr_dominant_scare} scare",
            "dominant_label_zh": f"{rr_dominant_scare}",
            "top_score": 75.0,
            "headline_en": f"Risk radar: {rr_dominant_scare}",
            "headline_zh": "",
            "scares": [],
        },
        "regime_one": regime_one or {
            "schema": "regime_one.v1",
            "asof": md_asof,
            "tape": {"quad": "Q1"},
            "macro": {"quad": "Q1"},
            "degraded": False,
        },
    }


def _make_regime_files(tmp_path: Path, regime: dict, transmission: dict | None = None) -> Path:
    """Write regime/latest.json (and optionally transmission/latest.json) to tmp_path."""
    regime_dir = tmp_path / "data" / "regime"
    regime_dir.mkdir(parents=True, exist_ok=True)
    (regime_dir / "latest.json").write_text(json.dumps(regime), encoding="utf-8")

    if transmission is not None:
        tx_dir = tmp_path / "data" / "transmission"
        tx_dir.mkdir(parents=True, exist_ok=True)
        (tx_dir / "latest.json").write_text(json.dumps(transmission), encoding="utf-8")

    return tmp_path


def _default_transmission(asof: str = _FRESH_ASOF) -> dict:
    """Return a transmission fixture matching the real emitted schema.

    The real schema from engine/rate_inflation_transmission.py:498-500 is:
        {"asset": str, "label": str, "ic": float|None, "effect": str (default "—"),
         "verdict": str ("headwind"|"tailwind"|"neutral"|"UNMEASURED")}

    headwind/tailwind/neutral/UNMEASURED are in the "verdict" field.
    "CONFIRMED" is NOT a valid verdict value.
    "effect" is a passthrough from the IC matrix defaulting to "—".
    (F2 fix — previously this fixture used "CONFIRMED" in verdict and
    headwind/tailwind in effect, which are both wrong.)
    """
    return {
        "asof": asof,
        "chains": [
            {
                "id": "real_rate",
                "trigger": "real10y_chg63",
                "active": True,
                "title": {"en": "Real-rate channel", "zh": "实际利率传导"},
                "orders": [
                    {
                        "order": 1,
                        "text": {
                            "en": "Rising real yields de-rate long-duration equity.",
                            "zh": "实际收益率上行压制长久期资产。",
                        },
                        "assets": [
                            {"asset": "QQQ", "label": "Invesco QQQ", "ic": -0.42,
                             "effect": "—", "verdict": "headwind"},
                            {"asset": "TLT", "label": "iShares 20Y", "ic": 0.31,
                             "effect": "—", "verdict": "tailwind"},
                        ],
                    },
                    {
                        "order": 2,
                        "text": {"en": "Higher USD draws capital in.", "zh": "美元走强吸引资本。"},
                        "assets": [
                            {"asset": "GLD", "label": "SPDR Gold", "ic": -0.28,
                             "effect": "—", "verdict": "headwind"},
                        ],
                    },
                    {
                        "order": 3,
                        "text": {"en": "Credit conditions tighten over weeks.", "zh": "数周内信用条件收紧。"},
                        "assets": [
                            {"asset": "HYG", "label": "iShares HY", "ic": -0.35,
                             "effect": "—", "verdict": "headwind"},
                        ],
                    },
                ],
            }
        ],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _all_text_fields(obj: Any, acc: list[str] | None = None) -> list[str]:
    """Recursively collect all string values from a nested dict/list."""
    if acc is None:
        acc = []
    if isinstance(obj, str):
        acc.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _all_text_fields(v, acc)
    elif isinstance(obj, list):
        for item in obj:
            _all_text_fields(item, acc)
    return acc


# typing import for helper above
from typing import Any


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestCoherenceDerivation:
    def test_high_agreement_supported(self):
        assert _derive_coherence(0.80) == "supported"

    def test_mid_agreement_partial(self):
        assert _derive_coherence(0.50) == "partial"

    def test_low_agreement_conflicted(self):
        assert _derive_coherence(0.20) == "conflicted"

    def test_none_agreement_partial(self):
        assert _derive_coherence(None) == "partial"

    def test_coherence_never_float(self):
        for val in [0.0, 0.3, 0.6, 0.9, 1.0, None]:
            result = _derive_coherence(val)
            assert isinstance(result, str), f"coherence must be str, got {type(result)} for {val}"
            assert result in ("supported", "partial", "conflicted")


class TestSchemaAndAuthorityBlock:
    def test_schema_present(self, tmp_path):
        regime = _make_regime()
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        assert result.get("schema") == SCHEMA

    def test_display_only_true(self, tmp_path):
        regime = _make_regime()
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        assert result.get("display_only") is True

    def test_not_a_signal_true(self, tmp_path):
        regime = _make_regime()
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        assert result.get("not_a_signal") is True

    def test_authority_block_present(self, tmp_path):
        regime = _make_regime()
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        auth = result.get("authority", {})
        assert auth.get("may_rank") is False
        assert auth.get("may_gate") is False
        assert auth.get("may_size") is False
        assert auth.get("may_escalate") is False
        assert "ranking" in auth.get("forbidden_uses", [])
        assert "mastermind_arming" in auth.get("forbidden_uses", [])

    def test_authority_block_keys(self, tmp_path):
        regime = _make_regime()
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        auth = result.get("authority", {})
        for key in ("tier", "horizon_role", "weights", "scored_path_surfaces",
                    "display_only", "not_a_signal", "forbidden_uses"):
            assert key in auth, f"authority missing key: {key}"


class TestTriggerPrecedence:
    def test_branch1_market_drivers_clear(self, tmp_path):
        """Branch 1: verdict==clear → primary from market_drivers."""
        regime = _make_regime(md_verdict="clear", md_primary="ai_semis")
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        pathways = result.get("pathways", [])
        assert len(pathways) >= 1
        primary = pathways[0]
        assert primary["pathway_role"] == "primary"
        assert primary["driver"] == "ai_semis"
        assert result.get("no_pathway") is None or result.get("no_pathway", {}).get("reason") is None

    def test_branch2_risk_radar_scare_when_not_clear(self, tmp_path):
        """Branch 2: verdict!=clear → fall to risk_radar scare."""
        regime = _make_regime(
            md_verdict="mixed",
            rr_dominant_scare="credit",
            rr_state="caution",
            rr_asof=_FRESH_ASOF,
        )
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        pathways = result.get("pathways", [])
        assert len(pathways) >= 1, "should have at least one pathway from credit scare"
        primary = pathways[0]
        assert primary["family"] == "credit_stress"

    def test_branch1_has_precedence_over_branch2(self, tmp_path):
        """Branch 1 beats branch 2: clear verdict wins even if scare is present."""
        regime = _make_regime(
            md_verdict="clear",
            md_primary="ai_semis",
            rr_dominant_scare="credit",
            rr_state="caution",
        )
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        pathways = result.get("pathways", [])
        assert pathways[0]["driver"] == "ai_semis", "market_drivers clear must win over scare"

    def test_branch3_factor_rotation(self, tmp_path):
        """Branch 3: no clear driver + no scare → factor rotation."""
        regime = _make_regime(
            md_verdict="quiet",
            rr_dominant_scare="",
            rr_state="calm",
        )
        _make_regime_files(tmp_path, regime)
        # Write factor_intelligence_state.json with a flip
        fi_dir = tmp_path / "data" / "neuralweb"
        fi_dir.mkdir(parents=True, exist_ok=True)
        fi_state = {
            "as_of": _FRESH_ASOF,
            "style_regime": {"state": "pending_flip", "label": "Value→Growth"},
        }
        (fi_dir / "factor_intelligence_state.json").write_text(
            json.dumps(fi_state), encoding="utf-8"
        )
        result = compile(root=tmp_path)
        pathways = result.get("pathways", [])
        assert len(pathways) == 1
        assert pathways[0]["family"] == "factor_rotation"

    def test_branch4_no_attributable_driver_null(self, tmp_path):
        """Branch 4: nothing fires → no_attributable_driver no_pathway.

        RUL-CC-12 §4 deviation ratified 2026-07-06: snap boolean is outside
        the RUL-CC-11 read-set; reason is no_attributable_driver (F3 fix).
        """
        regime = _make_regime(
            md_verdict="quiet",
            rr_dominant_scare="",
            rr_state="calm",
        )
        _make_regime_files(tmp_path, regime)
        # No factor_intelligence_state file
        result = compile(root=tmp_path)
        assert result.get("pathways") == []
        np_rec = result.get("no_pathway", {})
        assert np_rec is not None
        assert np_rec.get("reason") in ("no_attributable_driver", "no_trigger")
        assert np_rec.get("printed") is True

    def test_branch2_unattributed_scare_growth_null(self, tmp_path):
        """Branch 2: growth scare has no family → scare_unattributed null."""
        regime = _make_regime(
            md_verdict="mixed",
            rr_dominant_scare="growth",
            rr_state="caution",
        )
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        assert result.get("pathways") == []
        np_rec = result.get("no_pathway", {})
        assert np_rec.get("reason") == "scare_unattributed"
        assert np_rec.get("printed") is True

    def test_branch2_unattributed_scare_vol_null(self, tmp_path):
        """Branch 2: vol scare → scare_unattributed null."""
        regime = _make_regime(
            md_verdict="quiet",
            rr_dominant_scare="vol",
            rr_state="alert",
        )
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        assert result.get("pathways") == []
        np_rec = result.get("no_pathway", {})
        assert np_rec.get("reason") == "scare_unattributed"


class TestScareToFamilyMap:
    def test_credit_scare_maps_to_credit_stress(self, tmp_path):
        regime = _make_regime(md_verdict="mixed", rr_dominant_scare="credit", rr_state="caution")
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        assert result["pathways"][0]["family"] == "credit_stress"

    def test_rates_scare_maps_to_real_rate_shock(self, tmp_path):
        regime = _make_regime(md_verdict="mixed", rr_dominant_scare="rates", rr_state="caution")
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        assert result["pathways"][0]["family"] == "real_rate_shock"

    def test_bubble_scare_maps_to_ai_semis(self, tmp_path):
        regime = _make_regime(md_verdict="mixed", rr_dominant_scare="bubble", rr_state="caution")
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        assert result["pathways"][0]["family"] == "ai_semis"

    def test_global_scare_maps_to_usd_shock(self, tmp_path):
        regime = _make_regime(md_verdict="mixed", rr_dominant_scare="global", rr_state="caution")
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        assert result["pathways"][0]["family"] == "usd_shock"

    def test_unattributed_scares_in_constant(self):
        assert "vol" in _UNATTRIBUTED_SCARES
        assert "growth" in _UNATTRIBUTED_SCARES

    def test_scare_map_completeness(self):
        for scare in ("credit", "rates", "bubble", "global"):
            assert scare in SCARE_FAMILY_MAP, f"scare '{scare}' missing from SCARE_FAMILY_MAP"


class TestStaleTriggerGuard:
    def test_stale_market_drivers_emits_no_pathway(self, tmp_path):
        """Stale md asof → no_pathway(reason=trigger_stale)."""
        regime = _make_regime(md_asof=_STALE_ASOF)
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        assert result.get("pathways") == []
        np_rec = result.get("no_pathway", {})
        assert np_rec.get("reason") == "trigger_stale"

    def test_stale_risk_radar_emits_no_pathway(self, tmp_path):
        """Stale risk_radar asof → trigger_stale when falling to branch 2."""
        regime = _make_regime(
            md_verdict="mixed",
            rr_dominant_scare="credit",
            rr_state="caution",
            rr_asof=_STALE_ASOF,
        )
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        np_rec = result.get("no_pathway", {})
        assert np_rec.get("reason") == "trigger_stale"

    def test_fresh_data_with_clear_verdict_produces_pathway(self, tmp_path):
        regime = _make_regime(md_asof=_FRESH_ASOF, md_verdict="clear")
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        assert len(result.get("pathways", [])) >= 1

    def test_no_pathway_record_is_always_printed(self, tmp_path):
        """Every no_pathway record must have printed=True (RUL-CC-4)."""
        regime = _make_regime(md_asof=_STALE_ASOF)
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        np_rec = result.get("no_pathway")
        assert np_rec is not None
        assert np_rec.get("printed") is True


class TestCoverageScore:
    def test_coverage_score_present(self, tmp_path):
        """market_drivers-clear pathway has float coverage_score in [0,1]."""
        regime = _make_regime(md_verdict="clear")
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        if result.get("pathways"):
            cov = result["pathways"][0]["coverage_score"]
            # Primary pathway (built from evidence_legs) always has a float score.
            assert isinstance(cov, float)
            assert 0.0 <= cov <= 1.0

    def test_coverage_score_with_all_fresh_legs(self, tmp_path):
        regime = _make_regime(
            md_verdict="clear",
            md_evidence_legs=[
                {"en": "leg1", "zh": "腿1", "z": 2.0},
                {"en": "leg2", "zh": "腿2", "z": -1.5},
            ],
        )
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        if result.get("pathways"):
            assert result["pathways"][0]["coverage_score"] == 1.0

    def test_coverage_score_with_stale_legs(self, tmp_path):
        """Legs with z=None are counted as stale → lower coverage score."""
        regime = _make_regime(
            md_verdict="clear",
            md_evidence_legs=[
                {"en": "leg1", "zh": "腿1", "z": 2.0},
                {"en": "leg2_stale", "zh": "腿2缺失", "z": None},
                {"en": "leg3_stale", "zh": "腿3缺失", "z": None},
            ],
        )
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        if result.get("pathways"):
            cov = result["pathways"][0]["coverage_score"]
            assert cov < 1.0, "stale legs should reduce coverage"
            stale = result["pathways"][0]["stale_legs"]
            assert len(stale) == 2

    def test_insufficient_coverage_emits_null(self, tmp_path):
        """All legs stale → coverage=0 → no_pathway(insufficient_coverage)."""
        regime = _make_regime(
            md_verdict="clear",
            md_evidence_legs=[
                {"en": "leg1", "zh": "腿1", "z": None},
                {"en": "leg2", "zh": "腿2", "z": None},
                {"en": "leg3", "zh": "腿3", "z": None},
            ],
        )
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        np_rec = result.get("no_pathway", {})
        assert np_rec.get("reason") == "insufficient_coverage"
        assert np_rec.get("printed") is True

    def test_coverage_arithmetic_two_of_four_stale(self, tmp_path):
        """2 fresh + 2 stale → coverage = 0.5 → exactly at floor, should still emit."""
        regime = _make_regime(
            md_verdict="clear",
            md_evidence_legs=[
                {"en": "leg1", "zh": "腿1", "z": 1.0},
                {"en": "leg2", "zh": "腿2", "z": -1.0},
                {"en": "leg3_stale", "zh": "腿3", "z": None},
                {"en": "leg4_stale", "zh": "腿4", "z": None},
            ],
        )
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        if result.get("pathways"):
            cov = result["pathways"][0]["coverage_score"]
            assert abs(cov - 0.5) < 0.01

    # F5: scare-trigger pathway coverage tests
    def test_scare_pathway_coverage_is_null_not_fabricated(self, tmp_path):
        """Scare pathway (0 required legs) must emit coverage_score=null, not 1.0 (F5 fix).

        Previously the code fabricated coverage_score=1.0 for scare-trigger pathways
        that had no evidence_legs.  Fix: emit null + coverage_basis="scare_trigger".
        """
        regime = _make_regime(
            md_verdict="mixed",
            rr_dominant_scare="credit",
            rr_state="caution",
        )
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        pathways = result.get("pathways", [])
        assert pathways, "credit scare should produce a pathway"
        pw = pathways[0]
        assert pw.get("coverage_score") is None, (
            f"scare pathway coverage_score must be null, got {pw.get('coverage_score')!r}"
        )
        assert pw.get("coverage_basis") == "scare_trigger", (
            f"scare pathway must have coverage_basis='scare_trigger', got {pw.get('coverage_basis')!r}"
        )

    def test_scare_pathway_not_rejected_by_insufficient_coverage(self, tmp_path):
        """Scare pathway (null coverage) must not be rejected by the < 0.5 floor."""
        regime = _make_regime(
            md_verdict="mixed",
            rr_dominant_scare="credit",
            rr_state="caution",
        )
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        np_rec = result.get("no_pathway")
        if np_rec:
            assert np_rec.get("reason") != "insufficient_coverage", (
                "scare pathways must not be rejected by insufficient_coverage floor"
            )
        assert len(result.get("pathways", [])) >= 1, "scare pathway must be emitted"


class TestCoherenceCategorical:
    def test_coherence_is_string_not_float(self, tmp_path):
        regime = _make_regime(md_verdict="clear")
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        for pw in result.get("pathways", []):
            coh = pw.get("coherence")
            assert isinstance(coh, str), f"coherence must be str, got {type(coh)}"
            assert not isinstance(coh, (int, float)), "coherence must not be numeric"

    def test_coherence_values_are_valid_categories(self, tmp_path):
        regime = _make_regime(md_verdict="clear")
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        for pw in result.get("pathways", []):
            assert pw["coherence"] in ("supported", "partial", "conflicted"), (
                f"invalid coherence: {pw['coherence']}"
            )

    def test_no_float_coherence_key_anywhere_in_artifact(self, tmp_path):
        """Recursively verify no float value appears under a 'coherence' key."""
        regime = _make_regime(md_verdict="clear")
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)

        def _check_no_float_coherence(obj: Any, path: str = "") -> None:
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k == "coherence":
                        assert isinstance(v, str), f"float coherence at {path}.{k}: {v!r}"
                    _check_no_float_coherence(v, f"{path}.{k}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    _check_no_float_coherence(item, f"{path}[{i}]")

        _check_no_float_coherence(result)


class TestLanguageLaw:
    """RUL-CC-5: banned words must not appear in any generated text."""

    BANNED = ("caused", "proved", "proof", "validated")

    def test_no_banned_words_in_clear_pathway(self, tmp_path):
        regime = _make_regime(md_verdict="clear")
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        all_text = " ".join(_all_text_fields(result))
        for word in self.BANNED:
            assert word not in all_text.lower(), f"banned word '{word}' found in artifact text"

    def test_no_banned_words_in_scare_pathway(self, tmp_path):
        regime = _make_regime(md_verdict="mixed", rr_dominant_scare="credit", rr_state="caution")
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        all_text = " ".join(_all_text_fields(result))
        for word in self.BANNED:
            assert word not in all_text.lower(), f"banned word '{word}' in scare pathway text"

    def test_no_banned_words_in_no_pathway(self, tmp_path):
        regime = _make_regime(md_asof=_STALE_ASOF)
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        all_text = " ".join(_all_text_fields(result))
        for word in self.BANNED:
            assert word not in all_text.lower(), f"banned word '{word}' in no_pathway text"

    def test_contains_banned_words_helper(self):
        assert contains_banned_words("this caused the market to move") == ["caused"]
        assert contains_banned_words("this is validated data") == ["validated"]
        assert contains_banned_words("no problem here") == []

    def test_contains_banned_words_case_insensitive(self):
        assert "proved" in contains_banned_words("PROVED by evidence")
        assert "proof" in contains_banned_words("Proof of concept")


class TestAlternates:
    def test_at_most_two_alternates(self, tmp_path):
        regime = _make_regime(md_verdict="clear", md_primary="ai_semis")
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        alternates = [pw for pw in result.get("pathways", []) if pw.get("pathway_role") == "alternate"]
        assert len(alternates) <= 2

    def test_primary_is_first_pathway(self, tmp_path):
        regime = _make_regime(md_verdict="clear", md_primary="ai_semis")
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        pathways = result.get("pathways", [])
        if pathways:
            assert pathways[0]["pathway_role"] == "primary"

    def test_runner_up_seeded_as_alternate(self, tmp_path):
        regime = _make_regime(
            md_verdict="clear",
            md_primary="ai_semis",
            md_runner_up="china_stimulus",
        )
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        alternates = [pw for pw in result.get("pathways", []) if pw.get("pathway_role") == "alternate"]
        alt_drivers = [a["driver"] for a in alternates]
        assert "china_stimulus" in alt_drivers


class TestNodeEdgeSchema:
    def test_nodes_have_required_fields(self, tmp_path):
        regime = _make_regime(md_verdict="clear")
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        required = {
            "node_id", "as_of", "domain", "source_artifact", "entity",
            "observation", "direction", "value", "z_or_percentile",
            "source_tier", "lag_class", "pathway_role", "evidence_refs",
        }
        for pw in result.get("pathways", []):
            for node in pw.get("nodes", []):
                missing = required - set(node.keys())
                assert not missing, f"node missing fields: {missing}"

    def test_edges_have_required_fields(self, tmp_path):
        regime = _make_regime(md_verdict="clear")
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        required = {
            "src_node", "dst_node", "mechanism_type", "expected_lag",
            "expected_sign", "observed_sign", "status", "evidence_refs",
        }
        for pw in result.get("pathways", []):
            for edge in pw.get("edges", []):
                missing = required - set(edge.keys())
                assert not missing, f"edge missing fields: {missing}"

    def test_edge_expected_lag_valid(self, tmp_path):
        regime = _make_regime(md_verdict="clear")
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        valid_lags = {"same_day", "days_1_5", "weeks_1_4"}
        for pw in result.get("pathways", []):
            for edge in pw.get("edges", []):
                assert edge["expected_lag"] in valid_lags

    def test_edge_status_valid(self, tmp_path):
        regime = _make_regime(md_verdict="clear")
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        valid_statuses = {"measured", "theory_prior", "context_only", "conflicted", "missing", "stale"}
        for pw in result.get("pathways", []):
            for edge in pw.get("edges", []):
                assert edge["status"] in valid_statuses


class TestNullsAlwaysPrinted:
    def test_no_pathway_always_has_reason(self, tmp_path):
        """Any no_pathway record must have 'reason' and 'printed'=True."""
        for md_asof in [_STALE_ASOF, _FRESH_ASOF]:
            if md_asof == _FRESH_ASOF:
                # Force a null by using quiet verdict + no factor flip
                regime = _make_regime(md_verdict="quiet", rr_dominant_scare="", rr_state="calm",
                                      md_asof=_FRESH_ASOF)
            else:
                regime = _make_regime(md_asof=_STALE_ASOF)
            _make_regime_files(tmp_path / md_asof.replace("-", "_"), regime)
            result = compile(root=tmp_path / md_asof.replace("-", "_"))
            if result.get("no_pathway"):
                np_rec = result["no_pathway"]
                assert "reason" in np_rec, "no_pathway must have 'reason'"
                assert np_rec.get("printed") is True, "no_pathway.printed must be True"

    def test_missing_regime_file_returns_no_pathway(self, tmp_path):
        """If regime/latest.json is absent, returns no_pathway artifact (not exception)."""
        result = compile(root=tmp_path)  # empty tmp_path
        assert result.get("schema") == SCHEMA
        np_rec = result.get("no_pathway", {})
        assert np_rec.get("reason") is not None


class TestJsonRoundtrip:
    def test_artifact_is_json_serializable(self, tmp_path):
        regime = _make_regime(md_verdict="clear")
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        # Must not raise
        serialized = json.dumps(result, ensure_ascii=False)
        deserialized = json.loads(serialized)
        assert deserialized.get("schema") == SCHEMA

    def test_stale_artifact_is_json_serializable(self, tmp_path):
        regime = _make_regime(md_asof=_STALE_ASOF)
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path)
        json.dumps(result, ensure_ascii=False)  # must not raise


class TestTransmissionSchema:
    """F2: transmission cell schema — headwind/tailwind in 'verdict', not 'effect'."""

    def test_transmission_entity_non_degenerate(self, tmp_path):
        """Transmission nodes must populate 'entity' from measured assets (verdict field).

        F2 fix: the old code read a.get("verdict") == "CONFIRMED" which always
        returned empty (CONFIRMED is not a valid verdict in the real schema),
        making entity always "transmission channel".  Fix reads from "verdict" ∈
        {headwind, tailwind} instead.
        """
        regime = _make_regime(md_verdict="clear", md_primary="real_rate_shock")
        # Use real_rate_shock family so transmission chains attach
        regime["market_drivers"]["scores"] = [
            {"driver": "real_rate_shock", "label": "Real rates", "family": "rates",
             "projection": -1.36, "strength": 1.36, "direction": "AI/semis unwind"},
        ]
        transmission = _default_transmission()
        _make_regime_files(tmp_path, regime, transmission)
        result = compile(root=tmp_path)
        pathways = result.get("pathways", [])
        assert pathways, "should produce pathways"
        # Find any transmission domain node
        all_nodes = [n for pw in pathways for n in pw.get("nodes", [])
                     if n.get("domain") == "transmission"]
        assert all_nodes, "the real-rate driver must attach transmission nodes"
        if all_nodes:
            # At least one transmission node must have a non-degenerate entity
            # (i.e., it resolved actual asset names from the verdict field)
            non_default = [n for n in all_nodes if n.get("entity") != "transmission channel"]
            assert non_default, (
                f"all transmission nodes have generic entity 'transmission channel'; "
                f"expected at least one to resolve from verdict-headwind/tailwind assets. "
                f"Nodes: {[n.get('entity') for n in all_nodes]}"
            )

    def test_transmission_prior_sign_not_realized_observation(self, tmp_path):
        """The actual calibration verdict becomes a prior, not observed causality.

        This supersedes the old F2 observed-sign expectation. Its fixture used
        an AI primary (which attached no rate chain) and a conditional assertion,
        so it did not exercise the promised behavior at all.
        """
        regime = _make_regime(md_verdict="clear", md_primary="real_rate_shock")
        regime["market_drivers"]["scores"] = [
            {"driver": "real_rate_shock", "label": "Real rates", "family": "rates",
             "projection": -1.36, "strength": 1.36, "direction": "AI/semis unwind"},
        ]
        transmission = _default_transmission()
        _make_regime_files(tmp_path, regime, transmission)
        result = compile(root=tmp_path)
        pathways = result.get("pathways", [])
        all_edges = [e for pw in pathways for e in pw.get("edges", [])
                     if "transmission" in e.get("dst_node", "")]
        assert all_edges, "the real-rate driver must attach transmission links"
        assert any(e["expected_sign"] in ("positive", "negative") for e in all_edges)
        assert all(e["observed_sign"] is None for e in all_edges)
        assert all(e["status"] in ("context_only", "theory_prior") for e in all_edges)

    def test_transmission_fixture_uses_real_schema(self):
        """Verify _default_transmission() uses the real schema fields (not CONFIRMED)."""
        tx = _default_transmission()
        for chain in tx.get("chains", []):
            for order in chain.get("orders", []):
                for asset in order.get("assets", []):
                    assert "verdict" in asset, "real schema requires 'verdict' field"
                    assert asset["verdict"] != "CONFIRMED", (
                        "'CONFIRMED' is not a valid verdict in the real emitted schema; "
                        "valid values are headwind/tailwind/neutral/UNMEASURED"
                    )
                    assert "asset" in asset, "real schema requires 'asset' field"


# ---------------------------------------------------------------------------
# 2026-10-03 clock and aggregate repair regressions (R1/R2/R3/R4)
# ---------------------------------------------------------------------------

class TestSourceClockCarrier:
    """F1 regression: source clocks are carried through to nodes, not minted.

    The audit found that `compile()` builds an `as_of` from `datetime.now(tz=utc)`
    and passes that same build-date to every driver / evidence-leg node,
    regardless of the source record's own md_asof or chain asof. _is_stale
    admitted future dates, so a future-dated source became today-dated
    measured evidence before the reader validated it.
    """

    def test_compile_carries_source_md_asof_into_pathway_and_nodes(self, tmp_path):
        """When md_asof is a real past date, every node must carry that date."""
        # Use a fresh past date (1 day before the test clock)
        fresh_past = _FRESH_ASOF
        regime = _make_regime(md_asof=fresh_past, md_primary="ai_semis", md_verdict="clear")
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path, now=_TEST_NOW)
        pathways = result.get("pathways", [])
        assert pathways, "expected at least one pathway"
        primary = pathways[0]
        # Pathway record carries the source clock, not the build clock
        assert primary["as_of"] == fresh_past, (
            f"pathway as_of must be the source md_asof ({fresh_past}), got {primary['as_of']!r}"
        )
        # Driver + leg nodes carry the source clock too
        for node in primary["nodes"]:
            assert node["as_of"] == fresh_past, (
                f"node {node['node_id']!r} as_of must be source md_asof "
                f"({fresh_past}), got {node['as_of']!r}"
            )

    def test_compile_does_not_mint_today_for_missing_md_asof(self, tmp_path, md_state):
        """C2: missing market_drivers.asof must yield no_pathway(trigger_stale)
        even when the regime wrapper carries `asof` and `date`. The compiler
        must NEVER substitute the wrapper date for a missing driver clock.
        Parametrised over three md clock states: key absent, value None, value "".
        """
        # Build the regime directly so wrapper dates stay put and we control
        # the market_drivers.asof state precisely.
        wrapper_date = "2026-10-01"
        regime = {
            "asof": wrapper_date,
            "date": wrapper_date,
            "market_drivers": {
                "verdict": "clear",
                "primary": "ai_semis",
                "runner_up": "china_stimulus",
                "agreement": 0.80,
                "direction": "AI/semis unwind",
                "direction_zh": "AI/半导体回调",
                "dir_sign": "-1",
                "strength": 1.36,
                "dominance_ratio": 1.48,
                "confidence": "high",
                "evidence_legs": [
                    {"en": "semis RS", "zh": "半导体相对强度", "z": -3.0},
                    {"en": "growth vs value", "zh": "成长对价值", "z": 1.0},
                ],
                "scores": [
                    {"driver": "ai_semis", "label": "AI / semis", "label_zh": "AI/半导体",
                     "family": "equity-leadership", "projection": -1.36, "strength": 1.36,
                     "direction": "AI/semis unwind"},
                ],
                "headline": "AI/semis unwind",
            },
            "risk_radar": {
                "schema": "risk_radar.v2",
                "asof": wrapper_date,
                "state": "caution",
                "dominant_scare": "",
                "dominant_label_en": "",
                "dominant_label_zh": "",
                "top_score": 75.0,
                "headline_en": "Risk radar: ",
                "headline_zh": "",
                "scares": [],
            },
            "regime_one": {
                "schema": "regime_one.v1",
                "asof": wrapper_date,
                "tape": {"quad": "Q1"},
                "macro": {"quad": "Q1"},
                "degraded": False,
            },
        }
        md = regime["market_drivers"]
        if md_state == "absent":
            md.pop("asof", None)
        elif md_state == "none":
            md["asof"] = None
        elif md_state == "empty":
            md["asof"] = ""
        else:
            raise AssertionError(f"unknown md_state {md_state!r}")
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path, now=_TEST_NOW)
        pathways = result.get("pathways", [])
        assert not pathways, (
            f"missing md_asof (state={md_state}) must trigger no_pathway even "
            f"with wrapper dates present, got {pathways!r}"
        )
        np = result.get("no_pathway", {})
        assert np.get("reason") == "trigger_stale", (
            f"missing md_asof (state={md_state}) must surface reason "
            f"'trigger_stale', got {np.get('reason')!r}"
        )
        tc = np.get("trigger_context", {})
        assert tc.get("as_of_reason") == "unknown_date", (
            f"missing md_asof (state={md_state}) must surface "
            f"as_of_reason 'unknown_date', got {tc.get('as_of_reason')!r}"
        )

    test_compile_does_not_mint_today_for_missing_md_asof = pytest.mark.parametrize(
        "md_state", ["absent", "none", "empty"]
    )(test_compile_does_not_mint_today_for_missing_md_asof)

    def test_compile_rejects_future_md_asof_with_reason_not_stale(self, tmp_path):
        """R3 + R4: a future-dated source must not be admitted as fresh.
        _is_stale used to return False for negative days; the F1 fix must
        treat a future source clock as NOT usable, distinct from stale.
        """
        future_date = "2099-01-01"  # unambiguously future
        regime = _make_regime(md_asof=future_date, md_primary="ai_semis", md_verdict="clear")
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path, now=_TEST_NOW)
        # Future-dated source must trigger the stale-trigger guard
        np = result.get("no_pathway", {})
        assert np.get("reason") == "trigger_stale", (
            f"future-dated md_asof must emit trigger_stale, got {np.get('reason')!r}"
        )
        tc = np.get("trigger_context", {})
        assert tc.get("as_of_reason") == "future_dated", (
            f"future-dated md_asof must surface reason 'future_dated', got "
            f"{tc.get('as_of_reason')!r}"
        )


class TestFactorRotationClock:
    """R6: zero-edge pathway with factor rotation driver.
    The producer emits coverage_score=1.0 with edges=[]. The reader must
    derive coverage from the single source's clock, not copy the producer's
    claim. A stale/future/undated factor source must yield null coverage.
    """

    def test_factor_rotation_carries_source_clock(self, tmp_path):
        """The factor rotation driver node must carry the factor source clock,
        not today's build date.
        """
        fresh_past = _FRESH_ASOF
        regime = _make_regime(md_verdict="quiet", rr_state="calm", rr_dominant_scare="",
                              md_asof=fresh_past)
        regime.pop("regime_one", None)
        factor_path = tmp_path / "data/neuralweb/factor_intelligence_state.json"
        factor_path.parent.mkdir(parents=True, exist_ok=True)
        factor_path.write_text(json.dumps({
            "as_of": fresh_past,
            "style_regime": "flip_pending",
            "flips": [{"from": "value", "to": "growth"}],
        }), encoding="utf-8")
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path, now=_TEST_NOW)
        pathways = result.get("pathways", [])
        factor = [p for p in pathways if p["family"] == "factor_rotation"]
        assert factor, "factor rotation pathway expected"
        primary = factor[0]
        assert primary["as_of"] == fresh_past, (
            f"factor pathway as_of must be the source factor asof, got {primary['as_of']!r}"
        )
        driver = primary["nodes"][0]
        assert driver["as_of"] == fresh_past, (
            f"factor driver node as_of must be source clock, got {driver['as_of']!r}"
        )


class TestDependentLegsR7:
    """R7: dependent legs derived from one source record must not be counted
    as independent confirmations.
    """

    def test_pathway_records_distinct_source_count(self, tmp_path):
        """A pathway whose legs all share one source clock must expose a
        `distinct_sources` field. When all share one, distinct_sources=1;
        coherence is therefore NOT a passive counter of independent votes.
        """
        fresh_past = _FRESH_ASOF
        regime = _make_regime(md_asof=fresh_past, md_primary="ai_semis", md_verdict="clear")
        _make_regime_files(tmp_path, regime)
        result = compile(root=tmp_path, now=_TEST_NOW)
        pathways = result.get("pathways", [])
        primary = pathways[0]
        # The field must exist and reflect single-source reality
        assert "distinct_sources" in primary, (
            "R7 requires explicit distinct_sources count on every pathway"
        )
        # All nodes in a market_drivers pathway share md_asof → distinct_sources = 1
        assert primary["distinct_sources"] == 1, (
            f"market_drivers pathway should have distinct_sources=1 (one source), "
            f"got {primary['distinct_sources']}"
        )
        assert primary.get("independent_confirmations_disallowed") is True, (
            "R7 requires explicit insufficient-confirmation marker on single-source pathways"
        )


# ---------------------------------------------------------------------------
# C3 (slice 2): compile(now=...) must thread its clock into every
# source-clock classification made during the compile call tree
# (_attach_transmission_edges, _build_pathway, _build_factor_rotation_pathway).
# ---------------------------------------------------------------------------

class TestCompileThreadsNowToSourceClockClassifiers:
    """C3: a compile(now=...) call must read its injected clock for every
    _classify_source_clock() call made during the compile, not the patched
    wall clock. The autouse `_fixed_compiler_clock` fixture pins
    `_utcnow()` to 2026-10-02T23:00Z — without C3, every node would inherit
    that patched value while the pathway itself used the injected `now`,
    producing a pathway with `available` and nodes with `future_dated`.
    """

    def test_compile_now_threads_to_every_source_clock_classifier(self, tmp_path):
        """All source asofs = 2030-01-01; compile(now=2030-01-02T00:00Z).
        Without C3, the three call sites (:524/:678/:808) read `_utcnow()`
        (2026-10-02T23:00Z) → source 2030-01-01 is future_dated. With C3
        they read the injected `now` → source is 1 calendar day old →
        available.
        """
        future_past_asof = "2030-01-01"  # 1 day before the injected now
        regime = _make_regime(
            md_asof=future_past_asof,
            rr_asof=future_past_asof,
        )
        transmission = _default_transmission(asof=future_past_asof)
        root = _make_regime_files(tmp_path, regime, transmission)

        injected_now = datetime(2030, 1, 2, 0, 0, tzinfo=timezone.utc)
        result = compile(root=root, now=injected_now)

        pathways = result.get("pathways", [])
        assert pathways, (
            f"C3: compile(now=2030-01-02) on asof=2030-01-01 fixture must "
            f"produce at least one pathway, got {result.get('no_pathway')!r}"
        )
        primary = pathways[0]
        assert primary.get("as_of_reason") == "available", (
            f"C3: pathway as_of_reason must be 'available' (source 1 day "
            f"before injected now), got {primary.get('as_of_reason')!r}"
        )
        for node in primary.get("nodes", []):
            assert node.get("as_of_reason") == "available", (
                f"C3: node {node.get('node_id')!r} as_of_reason must be "
                f"'available', got {node.get('as_of_reason')!r} "
                f"(red proof: this would be 'future_dated' if C3 is not in)"
            )


# ---------------------------------------------------------------------------
# C4 (slice 2): one parity table for the compiler's _classify_source_clock.
# Rows mirror the reader's parity table (E4 in tests/test_mechanism_evidence.py).
# NOW = 2026-10-02T23:00:00Z, the canonical test clock.
# ---------------------------------------------------------------------------

_C4_NOW = datetime(2026, 10, 2, 23, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize('value,expected_status', [
    (None, 'unknown_date'),
    ('', 'unknown_date'),
    ('not-a-date', 'unknown_date'),
    ([], 'unknown_date'),
    (20261002, 'unknown_date'),                # int is unparseable per C4
    (1.5, 'unknown_date'),                      # float is unparseable per C4
    (True, 'unknown_date'),                     # bool is unparseable per C4
    ({'foo': 'bar'}, 'unknown_date'),           # dict is unparseable per C4
    ('2026-10-02T12:00:00', 'unknown_date'),    # naive datetime: refuse to invent TZ
    ('2026-10-04', 'future_dated'),             # date-only > latest_earth at NOW
    ('2026-10-02T22:30:00-01:00', 'future_dated'),  # tz-aware later than NOW
    ('2026-10-02T23:30:00+00:00', 'future_dated'),
    ('2020-01-01', 'stale'),                    # date-only calendar-age >= 5d
    ('2026-10-02', 'available'),
    ('2026-10-03', 'available'),                # one day ahead — still on Earth today
])
def test_e4_parity_table_for_compiler_clock_classifier(value, expected_status):
    """C4: compiler parity table — every row feeds the compiler's clock
     classifier and asserts the same status the reader expects (E4). NOW =
     2026-10-02T23:00:00Z. The compiler MUST reject non-string inputs and
     naive datetimes; otherwise the parity mirrors the reader's table.
     """
    out = _classify_source_clock(value, now=_C4_NOW)
    assert out["as_of_reason"] == expected_status, (
        f"C4: clock {value!r} (type {type(value).__name__}) expected "
        f"{expected_status!r}, got {out['as_of_reason']!r}"
    )


def test_classify_source_clock_rejects_non_string_inputs():
    """C4: any non-string input (int, float, bool, list, dict, datetime
    object) returns unknown_date — the compiler refuses to interpret
    values that do not name a clock.
    """
    non_strings = [20261002, 1.5, True, [], {}, datetime(2026, 10, 2)]
    for v in non_strings:
        out = _classify_source_clock(v, now=_C4_NOW)
        assert out["as_of"] is None, (
            f"C4: non-string {v!r} (type {type(v).__name__}) must yield "
            f"as_of=None, got {out['as_of']!r}"
        )
        assert out["as_of_reason"] == "unknown_date", (
            f"C4: non-string {v!r} (type {type(v).__name__}) must yield "
            f"reason 'unknown_date', got {out['as_of_reason']!r}"
        )


def test_classify_source_clock_naive_datetime_returns_unknown_date():
    """C4: a naive datetime string (no offset, e.g. '2026-10-02T12:00:00')
    returns unknown_date — the source's TZ is unobservable and the
    compiler must refuse to invent one (R3).
    """
    out = _classify_source_clock("2026-10-02T12:00:00", now=_C4_NOW)
    assert out["as_of"] is None
    assert out["as_of_reason"] == "unknown_date"


def test_classify_source_clock_future_date_only_uses_latest_earth_date():
    """C4: a date-only source D is 'future_dated' only when D >
    (now_utc + 14h).date(). '2026-10-03' at NOW=2026-10-02T23:00Z → latest
    earth date is 2026-10-03 → not future; '2026-10-04' is future.
    """
    # Available: 2026-10-03 == latest_earth(2026-10-02T23:00Z)
    out_available = _classify_source_clock("2026-10-03", now=_C4_NOW)
    assert out_available["as_of_reason"] == "available", (
        f"C4: '2026-10-03' at NOW=2026-10-02T23:00Z is on Earth today; "
        f"got {out_available['as_of_reason']!r}"
    )
    # Future: 2026-10-04 > latest_earth(2026-10-02T23:00Z)
    out_future = _classify_source_clock("2026-10-04", now=_C4_NOW)
    assert out_future["as_of_reason"] == "future_dated", (
        f"C4: '2026-10-04' at NOW=2026-10-02T23:00Z is past the date-line; "
        f"got {out_future['as_of_reason']!r}"
    )
