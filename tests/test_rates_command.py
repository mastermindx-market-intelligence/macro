"""Tests for engine.rates_inflation_command — Forward Path board.

Pure-function unit tests; no network access; file-reading tests use tmp_path.
Mirrors the style of tests/test_transmission_context.py.

Run: python3 -m pytest tests/test_rates_command.py -x -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.rates_inflation_command import (  # noqa: E402
    build_board,
    compact_state,
    diff_changes,
    build_changes,
    compose_stance,
    _compute_net_state,
    _render_cuts,
    H1_HAWKISH_THRESHOLD_BP,
    H1_DOVISH_THRESHOLD_BP,
    D1_GAP_BP_THRESHOLD,
    D3_IMPLIED_BP_LOW,
    D3_IMPLIED_BP_HIGH,
    _NET_STATE_LABELS,
)
from engine.yield_momentum import build_yield_momentum  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers to build synthetic compact states
# ---------------------------------------------------------------------------

def _cs(
    net_state="two_sided",
    hawk_score=0,
    ease_score=0,
    curve_regime="bear_steepener",
    anchoring="anchored",
    infl_dir="steady",
    implied_bp_12m=10,
) -> dict:
    return {
        "net_state": net_state,
        "hawk_score": hawk_score,
        "ease_score": ease_score,
        "curve_regime": curve_regime,
        "anchoring": anchoring,
        "infl_dir": infl_dir,
        "usd_dir": None,
        "implied_bp_12m": implied_bp_12m,
    }


# ---------------------------------------------------------------------------
# 1. Net-state machine — every branch exhaustively
# ---------------------------------------------------------------------------

class TestNetState:
    def test_repricing_hawkish_requires_h1_and_net_ge_2(self):
        state = _compute_net_state(
            hawk_score=4, ease_score=1, zq_d20_bp=20.0, h1_active=True
        )
        assert state == "repricing_hawkish"

    def test_repricing_hawkish_h1_active_exactly_net_2(self):
        state = _compute_net_state(
            hawk_score=3, ease_score=1, zq_d20_bp=20.0, h1_active=True
        )
        assert state == "repricing_hawkish"

    def test_pressure_building_when_h1_not_active_but_net_ge_2(self):
        state = _compute_net_state(
            hawk_score=4, ease_score=1, zq_d20_bp=5.0, h1_active=False
        )
        assert state == "pressure_building"

    def test_pressure_building_h1_none_net_ge_2(self):
        # H1 unavailable (None) — not active, but net >=2 -> pressure_building
        state = _compute_net_state(
            hawk_score=3, ease_score=1, zq_d20_bp=None, h1_active=None
        )
        assert state == "pressure_building"

    def test_repricing_dovish_mirror_d20_le_minus15_net_ease_ge_2(self):
        state = _compute_net_state(
            hawk_score=1, ease_score=4, zq_d20_bp=-20.0, h1_active=False
        )
        assert state == "repricing_dovish"

    def test_pressure_fading_no_dovish_h1_mirror(self):
        state = _compute_net_state(
            hawk_score=0, ease_score=3, zq_d20_bp=-5.0, h1_active=False
        )
        assert state == "pressure_fading"

    def test_pressure_fading_h1_none_ease_ge_2(self):
        state = _compute_net_state(
            hawk_score=0, ease_score=2, zq_d20_bp=None, h1_active=None
        )
        assert state == "pressure_fading"

    def test_two_sided_small_net(self):
        state = _compute_net_state(
            hawk_score=2, ease_score=2, zq_d20_bp=5.0, h1_active=False
        )
        assert state == "two_sided"

    def test_two_sided_zero_scores(self):
        state = _compute_net_state(
            hawk_score=0, ease_score=0, zq_d20_bp=0.0, h1_active=False
        )
        assert state == "two_sided"

    def test_repricing_hawkish_h1_false_blocks_repricing(self):
        # hawk-ease=4 but H1 not active -> pressure_building not repricing_hawkish
        state = _compute_net_state(
            hawk_score=5, ease_score=1, zq_d20_bp=5.0, h1_active=False
        )
        assert state == "pressure_building"

    def test_pressure_fading_not_dovish_when_d20_flat(self):
        state = _compute_net_state(
            hawk_score=1, ease_score=4, zq_d20_bp=0.0, h1_active=False
        )
        assert state == "pressure_fading"

    def test_net_state_labels_complete(self):
        """Every net_state key has EN+ZH labels."""
        for key in ["repricing_hawkish", "pressure_building",
                    "repricing_dovish", "pressure_fading", "two_sided"]:
            lbl = _NET_STATE_LABELS[key]
            assert "en" in lbl and "zh" in lbl
            assert lbl["en"] and lbl["zh"]
            assert "consensus" not in lbl["en"].lower()
            assert "共识" not in lbl["zh"]
            assert "validated" not in lbl["en"].lower()


# ---------------------------------------------------------------------------
# 2. Cuts/hikes sign rendering
# ---------------------------------------------------------------------------

class TestRenderCuts:
    def test_minus2_is_two_hikes(self):
        result = _render_cuts(-2)
        assert "hike" in result["en"].lower()
        assert "two" in result["en"].lower()
        assert "加息" in result["zh"]

    def test_plus2_is_two_cuts(self):
        result = _render_cuts(2)
        assert "cut" in result["en"].lower()
        assert "two" in result["en"].lower()
        assert "降息" in result["zh"]

    def test_zero_is_hold(self):
        result = _render_cuts(0)
        assert "hold" in result["en"].lower()
        assert "按兵" in result["zh"]

    def test_minus1_is_one_hike(self):
        result = _render_cuts(-1)
        assert "hike" in result["en"].lower()
        assert "one" in result["en"].lower()

    def test_plus1_is_one_cut(self):
        result = _render_cuts(1)
        assert "cut" in result["en"].lower()
        assert "one" in result["en"].lower()

    def test_minus3_is_three_hikes(self):
        result = _render_cuts(-3)
        assert "hike" in result["en"].lower()
        assert "three" in result["en"].lower()

    def test_none_is_unclear(self):
        result = _render_cuts(None)
        assert "unclear" in result["en"].lower() or "unclear" in result["en"]

    def test_small_fraction_is_hold(self):
        # 0.3 rounds to 0 -> hold
        result = _render_cuts(0.3)
        assert "hold" in result["en"].lower()


# ---------------------------------------------------------------------------
# 3. D1-D3 threshold checks (unit-test values, not build_board)
# ---------------------------------------------------------------------------

class TestDivergenceThresholds:
    def test_d1_threshold_constant(self):
        assert D1_GAP_BP_THRESHOLD == 50.0

    def test_d3_low_threshold(self):
        assert D3_IMPLIED_BP_LOW == 0.0

    def test_d3_high_threshold(self):
        assert D3_IMPLIED_BP_HIGH == 25.0

    def test_h1_hawkish_threshold(self):
        assert H1_HAWKISH_THRESHOLD_BP == 15.0

    def test_h1_dovish_threshold(self):
        assert H1_DOVISH_THRESHOLD_BP == -15.0


# ---------------------------------------------------------------------------
# 4. build_changes same-day idempotency
# ---------------------------------------------------------------------------

class TestBuildChanges:
    def _make_contract(self, asof, net_state="two_sided", hawk=0, ease=0) -> dict:
        return {
            "asof": asof,
            "expectations_pressure": {
                "net_state": net_state,
                "hawk_score": hawk,
                "ease_score": ease,
            },
            "board": {
                "rate_path_row": {"implied_bp_12m": 10},
                "inflation_row": {"anchoring": "anchored", "direction": "steady"},
                "risk_row": {"curve_regime_key": "bear_steepener"},
                "policy_row": {},
            },
            "changes": {"vs_asof": None, "items": []},
            "prev_state": {"as_of": None, "state": {}},
        }

    def test_first_run_no_old_returns_empty_changes(self):
        new = self._make_contract("2026-07-18")
        changes, prev = build_changes(None, new, "2026-07-18")
        assert changes["items"] == []
        assert changes["vs_asof"] is None
        assert prev["as_of"] is None

    def test_new_day_diffs_old_vs_new(self):
        old = self._make_contract("2026-07-17", net_state="two_sided")
        new = self._make_contract("2026-07-18", net_state="repricing_hawkish")
        changes, prev = build_changes(old, new, "2026-07-18")
        # There is a net_state diff
        assert any(item["key"] == "net_state" for item in changes["items"])
        assert changes["vs_asof"] == "2026-07-17"

    def test_same_day_reuses_prev_state(self):
        """Same-day rebuild reuses the stored prev_state (not old compact)."""
        old = self._make_contract("2026-07-18", net_state="two_sided")
        # Store a prev_state from yesterday
        old["prev_state"] = {
            "as_of": "2026-07-17",
            "state": _cs(net_state="pressure_building"),
        }
        new = self._make_contract("2026-07-18", net_state="repricing_hawkish")
        changes, prev = build_changes(old, new, "2026-07-18")
        # vs_asof should be the stored prev_state.as_of (2026-07-17)
        assert changes["vs_asof"] == "2026-07-17"
        # prev_state should be the stored one
        assert prev["as_of"] == "2026-07-17"

    def test_same_day_no_stored_prev_emits_empty(self):
        old = self._make_contract("2026-07-18", net_state="two_sided")
        # old has empty prev_state (first of the day)
        new = self._make_contract("2026-07-18", net_state="repricing_hawkish")
        changes, prev = build_changes(old, new, "2026-07-18")
        assert changes["items"] == []

    def test_usd_dir_compact_returns_leg_string(self):
        # T1 — compact_state reads the published string, not the policy_row dict.
        c = self._make_contract("2026-07-18")
        c["expectations_pressure"]["legs"] = [
            {"key": "E3_dollar_tightening", "value": "strengthening"},
        ]
        cs = compact_state(c)
        assert cs["usd_dir"] == "strengthening"
        assert not isinstance(cs["usd_dir"], dict)

    def test_usd_dir_compact_missing_leg_returns_none(self):
        c = self._make_contract("2026-07-18")
        c["expectations_pressure"]["legs"] = [
            {"key": "other_leg", "value": "x"},
        ]
        assert compact_state(c)["usd_dir"] is None

    def test_usd_dir_compact_none_value_returns_none(self):
        c = self._make_contract("2026-07-18")
        c["expectations_pressure"]["legs"] = [
            {"key": "E3_dollar_tightening", "value": None},
        ]
        assert compact_state(c)["usd_dir"] is None

    def test_usd_dir_no_item_when_policy_row_differs(self):
        # T2 — today's live failure: any policy_row diff used to print as
        # `usd_dir changed: {...whole dict...}`. Identical legs => no item.
        old = self._make_contract("2026-07-17")
        new = self._make_contract("2026-07-18")
        # Rich policy_row on old; richer on new — these are the "moves" we
        # must NOT see reflected as a usd_dir change.
        old["board"]["policy_row"] = {"regime": "qa", "stance_score": 0.3}
        new["board"]["policy_row"] = {
            "regime": "qa",
            "stance_score": 0.7,
            "extra_field": {"nested": [1, 2, 3]},
        }
        # Both share the same dollar direction
        usd_leg = {"key": "E3_dollar_tightening", "value": "weakening"}
        old["expectations_pressure"]["legs"] = [usd_leg]
        new["expectations_pressure"]["legs"] = [usd_leg]
        changes, _ = build_changes(old, new, "2026-07-18")
        assert not any(item["key"] == "usd_dir" for item in changes["items"])

    def test_usd_dir_same_day_legacy_baseline_skipped(self):
        # T4 — stored prev_state predates the repair; baseline `usd_dir` is
        # still a dict. Same-day rebuild must NOT raise and must NOT emit.
        old = self._make_contract("2026-07-18", net_state="two_sided")
        old["prev_state"] = {
            "as_of": "2026-07-17",
            "state": {
                "net_state": "two_sided",
                "usd_dir": {"state": "QUIET"},  # legacy dict form
            },
        }
        new = self._make_contract("2026-07-18", net_state="repricing_hawkish")
        usd_leg = {"key": "E3_dollar_tightening", "value": "weakening"}
        new["expectations_pressure"]["legs"] = [usd_leg]
        changes, _ = build_changes(old, new, "2026-07-18")
        assert not any(item["key"] == "usd_dir" for item in changes["items"])


# ---------------------------------------------------------------------------
# 5. diff_changes direction tests
# ---------------------------------------------------------------------------

class TestDiffChanges:
    def test_net_state_change_detected(self):
        prev = _cs(net_state="two_sided")
        curr = _cs(net_state="repricing_hawkish")
        items = diff_changes(prev, curr)
        assert any(i["key"] == "net_state" for i in items)

    def test_no_change_returns_empty(self):
        cs = _cs(net_state="two_sided", hawk_score=2, ease_score=2)
        assert diff_changes(cs, cs) == []

    def test_max_6_items_enforced(self):
        prev = _cs(net_state="two_sided", hawk_score=0, ease_score=0,
                   curve_regime="flat", anchoring="anchored",
                   infl_dir="steady", implied_bp_12m=10)
        curr = _cs(net_state="pressure_building", hawk_score=5, ease_score=1,
                   curve_regime="bear_steepener", anchoring="strained",
                   infl_dir="re-accelerating", implied_bp_12m=40)
        items = diff_changes(prev, curr)
        assert len(items) <= 6

    def test_none_to_value_skipped(self):
        prev = _cs(net_state=None)
        curr = _cs(net_state="two_sided")
        items = diff_changes(prev, curr)
        assert not any(i["key"] == "net_state" for i in items)

    def test_bilingual_items(self):
        prev = _cs(net_state="two_sided")
        curr = _cs(net_state="repricing_hawkish")
        items = diff_changes(prev, curr)
        for item in items:
            assert "en" in item and "zh" in item

    def test_usd_dir_change_worded(self):
        # T3 — EN/ZH wording for the dollar direction change.
        prev = _cs()
        prev["usd_dir"] = "strengthening"
        curr = _cs()
        curr["usd_dir"] = "flat"
        items = diff_changes(prev, curr)
        usd_items = [i for i in items if i["key"] == "usd_dir"]
        assert len(usd_items) == 1
        assert usd_items[0]["en"] == "Dollar direction: strengthening → flat"
        assert usd_items[0]["zh"] == "美元方向：走强 → 横盘"

    def test_usd_dir_dict_side_skipped(self):
        prev = _cs(); prev["usd_dir"] = {"state": "QUIET"}
        curr = _cs(); curr["usd_dir"] = "weakening"
        items = diff_changes(prev, curr)
        assert not any(i["key"] == "usd_dir" for i in items)


# ---------------------------------------------------------------------------
# 6. Fail-open: missing artifacts -> all legs null, no raise, artifact emits
# ---------------------------------------------------------------------------

class TestFailOpen:
    def test_empty_root_no_raise(self, tmp_path):
        """Point build_board at an empty tmp dir — should return valid artifact, not raise."""
        result = build_board(root=tmp_path)
        assert isinstance(result, dict)
        assert result["display_only"] is True
        assert result["authority"] is False
        assert "expectations_pressure" in result
        ep = result["expectations_pressure"]
        # Legs that REQUIRE an absent artifact must be active=None (fail-open).
        # Legs that can return a definite False without input data are allowed to.
        # Key legs that need ZQ parquet / market_state / yield_curve:
        null_expected = {"H1_path_repricing", "H2_breakeven_momentum", "H5_curve_regime",
                         "H6_anchoring_strain", "E1_equity_deleveraging", "E4_credit_stress",
                         "E5_policy_easing_chain"}
        for leg in ep["legs"]:
            if leg["key"] in null_expected:
                assert leg.get("active") is None, f"Expected null leg (empty root): {leg['key']}"
        # net_state should be two_sided (all null -> 0 vs 0)
        assert ep["net_state"] == "two_sided"
        # stance should still exist
        assert "stance" in result
        assert "en" in result["stance"]
        # caveats should mention missing data
        assert any("absent" in c.lower() or "unavailable" in c.lower() or "missing" in c.lower()
                   for c in result.get("caveats", [])), result["caveats"]

    def test_no_raise_on_corrupt_json(self, tmp_path):
        """Corrupt bond_health.json -> still returns artifact."""
        bonds_dir = tmp_path / "bonds"
        bonds_dir.mkdir()
        (bonds_dir / "bond_health.json").write_text("NOT JSON")
        result = build_board(root=tmp_path)
        assert isinstance(result, dict)
        assert result["authority"] is False

    def test_rates_command_carries_canonical_yield_momentum_read(self, tmp_path):
        transmission = tmp_path / "transmission"
        transmission.mkdir()
        (transmission / "latest.json").write_text(json.dumps({
            "asof": "2026-09-01",
            "yield_momentum": {
                "schema": "yield_momentum.v1",
                "display_only": True,
                "authority": False,
                "series": {"20y": {"status": "available"}},
            },
        }))

        result = build_board(root=tmp_path)

        assert result["yield_momentum"]["series"]["20y"]["status"] == "available"
        assert result["yield_momentum"]["display_only"] is True
        assert result["yield_momentum"]["authority"] is False

    def test_rates_command_preserves_stale_null_state_after_rate_freshness_expires(self, tmp_path):
        index = pd.bdate_range("2026-01-02", periods=100)
        frame = pd.DataFrame(
            {"us20y": [3.0 + offset / 100 for offset in range(90)] + [None] * 10},
            index=index,
        )
        yield_read = build_yield_momentum(frame)
        transmission = tmp_path / "transmission"
        transmission.mkdir()
        (transmission / "latest.json").write_text(json.dumps({
            "asof": yield_read["asof"],
            "yield_momentum": yield_read,
        }))

        result = build_board(root=tmp_path)

        twenty = result["yield_momentum"]["series"]["20y"]
        assert result["yield_momentum"]["asof"] == str(index[-1].date())
        assert twenty["status"] == "stale"
        assert twenty["as_of"] == str(index[-11].date())
        assert twenty["level"] is None
        assert set(twenty["velocity_bp"].values()) == {None}
        assert twenty["acceleration_bp"] is None
        assert twenty["turn_watch"] is None
        assert twenty["null_reason"]


# ---------------------------------------------------------------------------
# 7. Word-ban scans over emitted strings and keys
# ---------------------------------------------------------------------------

def _walk_strings(obj, path="root") -> list[tuple[str, str]]:
    """Walk dict/list recursively, yield (path, string_value) for all strings."""
    results = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            results.extend(_walk_strings(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            results.extend(_walk_strings(v, f"{path}[{i}]"))
    elif isinstance(obj, str):
        results.append((path, obj))
    return results


def _walk_keys(obj, path="root") -> list[str]:
    """Walk dict recursively, yield all key names as strings."""
    keys = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.append(k)
            keys.extend(_walk_keys(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for item in obj:
            keys.extend(_walk_keys(item, path))
    return keys


class TestWordBans:
    @pytest.fixture(scope="class")
    def live_artifact(self):
        """Build artifact against real data (if available) or empty root."""
        try:
            return build_board()
        except Exception:
            return None

    def test_no_consensus_in_strings(self, live_artifact):
        if live_artifact is None:
            pytest.skip("No live artifact")
        for path, s in _walk_strings(live_artifact):
            assert "consensus" not in s.lower(), f"Banned word 'consensus' at {path}: {s!r}"
            assert "共识" not in s, f"Banned word '共识' at {path}: {s!r}"

    def test_no_validated_in_strings(self, live_artifact):
        if live_artifact is None:
            pytest.skip("No live artifact")
        for path, s in _walk_strings(live_artifact):
            assert "validated" not in s.lower(), f"Banned word 'validated' at {path}: {s!r}"

    def test_naming_law_keys_no_forbidden_substrings(self, live_artifact):
        if live_artifact is None:
            pytest.skip("No live artifact")
        forbidden = ["forecast", "predicted", "expected_return"]
        for key in _walk_keys(live_artifact):
            for f in forbidden:
                assert f not in key.lower(), (
                    f"Naming-law violation: key '{key}' contains banned substring '{f}'"
                )

    def test_no_consensus_in_empty_root_artifact(self, tmp_path):
        artifact = build_board(root=tmp_path)
        for path, s in _walk_strings(artifact):
            assert "consensus" not in s.lower(), f"Banned word 'consensus' at {path}: {s!r}"
            assert "共识" not in s, f"Banned word '共识' at {path}: {s!r}"
            assert "validated" not in s.lower(), f"Banned word 'validated' at {path}: {s!r}"

    def test_naming_law_empty_root(self, tmp_path):
        artifact = build_board(root=tmp_path)
        forbidden = ["forecast", "predicted", "expected_return"]
        for key in _walk_keys(artifact):
            for f in forbidden:
                assert f not in key.lower(), (
                    f"Naming-law violation: key '{key}' contains banned substring '{f}'"
                )


# ---------------------------------------------------------------------------
# 8. Schema structure tests
# ---------------------------------------------------------------------------

class TestSchema:
    @pytest.fixture(scope="class")
    def artifact(self, tmp_path_factory):
        tmp = tmp_path_factory.mktemp("empty")
        return build_board(root=tmp)

    def test_schema_key(self, artifact):
        assert artifact["schema"] == "rates_command.v1"

    def test_display_only_true(self, artifact):
        assert artifact["display_only"] is True

    def test_authority_false(self, artifact):
        assert artifact["authority"] is False

    def test_board_has_four_rows(self, artifact):
        board = artifact["board"]
        assert "rate_path_row" in board
        assert "inflation_row" in board
        assert "risk_row" in board
        assert "policy_row" in board

    def test_expectations_pressure_structure(self, artifact):
        ep = artifact["expectations_pressure"]
        assert "legs" in ep
        assert "hawk_score" in ep
        assert "ease_score" in ep
        assert "net_state" in ep
        assert "state_label" in ep
        assert "en" in ep["state_label"] and "zh" in ep["state_label"]

    def test_eleven_legs_total(self, artifact):
        ep = artifact["expectations_pressure"]
        keys = [l["key"] for l in ep["legs"]]
        hawkish = [k for k in keys if k.startswith("H")]
        easing = [k for k in keys if k.startswith("E")]
        assert len(hawkish) == 6, f"Expected 6 hawkish legs, got {hawkish}"
        assert len(easing) == 5, f"Expected 5 easing legs, got {easing}"

    def test_divergence_has_three_flags(self, artifact):
        div = artifact["divergence"]
        keys = [d["key"] for d in div]
        assert "D1_dots_vs_market" in keys
        assert "D2_projection_vs_breakeven" in keys
        assert "D3_pressure_vs_market" in keys

    def test_stance_bilingual(self, artifact):
        stance = artifact["stance"]
        assert "en" in stance and "zh" in stance
        assert isinstance(stance["en"], str)
        assert isinstance(stance["zh"], str)

    def test_market_check_structure(self, artifact):
        mc = artifact["market_check"]
        assert "futures" in mc
        assert "benchmark_note_en" in mc
        assert "benchmark_note_zh" in mc

    def test_caveats_includes_futures_caveat(self, artifact):
        caveats = artifact["caveats"]
        assert any("futures" in c.lower() and "risk premium" in c.lower()
                   for c in caveats), f"Missing futures risk-premium caveat: {caveats}"

    def test_risk_row_real_speed_note(self, artifact):
        risk_row = artifact["board"]["risk_row"]
        note = risk_row.get("real_speed_note_en", "")
        assert "flags risk" in note.lower() or "risk" in note.lower()
        assert "not return" in note.lower()

    def test_risk_row_term_premium_note(self, artifact):
        risk_row = artifact["board"]["risk_row"]
        note = risk_row.get("term_premium_note_en", "")
        assert "kim-wright" in note.lower()
        assert "acm" in note.lower()


# ---------------------------------------------------------------------------
# 9. Leg structure validation
# ---------------------------------------------------------------------------

class TestLegStructure:
    @pytest.fixture(scope="class")
    def legs(self, tmp_path_factory):
        tmp = tmp_path_factory.mktemp("empty2")
        artifact = build_board(root=tmp)
        return artifact["expectations_pressure"]["legs"]

    def test_all_legs_have_required_keys(self, legs):
        required = {"key", "active", "weight", "value", "detail_en", "detail_zh", "null_reason"}
        for leg in legs:
            missing = required - set(leg.keys())
            assert not missing, f"Leg {leg.get('key')} missing keys: {missing}"

    def test_null_legs_have_null_reason(self, legs):
        for leg in legs:
            if leg["active"] is None:
                assert leg["null_reason"] is not None and leg["null_reason"] != "", (
                    f"Leg {leg['key']} has active=None but null_reason is empty"
                )

    def test_active_legs_no_null_reason(self, legs):
        for leg in legs:
            if leg["active"] is not None:
                # null_reason should be None (or empty) for definite legs
                assert leg["null_reason"] is None or leg["null_reason"] == "", (
                    f"Leg {leg['key']} has active={leg['active']} but non-empty null_reason: {leg['null_reason']}"
                )


# ---------------------------------------------------------------------------
# 10. forward_log lane gate: local run should NOT create the log
# ---------------------------------------------------------------------------

class TestForwardLogLane:
    def test_forward_log_not_created_without_nightly_lane(self, tmp_path, monkeypatch):
        """builder must NOT write forward_log.jsonl unless lane == 'nightly'."""
        import os
        monkeypatch.delenv("COLLECT_LANE", raising=False)
        monkeypatch.delenv("US_LANE", raising=False)

        # Build an artifact against empty root (won't write meaningful data)
        from scripts.build_rates_command import _append_forward_log
        artifact = {
            "asof": "2026-07-18",
            "expectations_pressure": {"net_state": "two_sided", "hawk_score": 0, "ease_score": 0},
            "divergence": [],
            "board": {"rate_path_row": {}},
        }
        log_path = tmp_path / "rates_command" / "forward_log.jsonl"
        _append_forward_log(tmp_path / "rates_command", artifact)
        assert not log_path.exists(), "forward_log.jsonl must NOT exist without nightly lane"

    def test_forward_log_created_with_nightly_lane(self, tmp_path, monkeypatch):
        """builder MUST write forward_log.jsonl when lane == 'nightly'."""
        monkeypatch.setenv("COLLECT_LANE", "nightly")
        from scripts.build_rates_command import _append_forward_log
        artifact = {
            "asof": "2026-07-18",
            "expectations_pressure": {"net_state": "two_sided", "hawk_score": 0, "ease_score": 0},
            "divergence": [
                {"key": "D1_dots_vs_market", "active": False},
                {"key": "D2_projection_vs_breakeven", "active": None},
                {"key": "D3_pressure_vs_market", "active": False},
            ],
            "board": {"rate_path_row": {"implied_bp_12m": 10, "gap": {"gap_bp": 7}}},
        }
        out_dir = tmp_path / "rates_command"
        out_dir.mkdir()
        _append_forward_log(out_dir, artifact)
        log_path = out_dir / "forward_log.jsonl"
        assert log_path.exists()
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 1
        row = json.loads(lines[0])
        assert row["schema"] == "rates_command_flag.v1"
        assert row["asof_night"] == "2026-07-18"

    def test_forward_log_keep_first(self, tmp_path, monkeypatch):
        """Second write for same asof_night must be skipped (keep-FIRST)."""
        monkeypatch.setenv("COLLECT_LANE", "nightly")
        from scripts.build_rates_command import _append_forward_log
        artifact = {
            "asof": "2026-07-18",
            "expectations_pressure": {"net_state": "two_sided", "hawk_score": 0, "ease_score": 0},
            "divergence": [],
            "board": {"rate_path_row": {}},
        }
        out_dir = tmp_path / "rates_command"
        out_dir.mkdir()
        _append_forward_log(out_dir, artifact)
        _append_forward_log(out_dir, artifact)  # second call: must skip
        log_path = out_dir / "forward_log.jsonl"
        lines = [l for l in log_path.read_text().strip().splitlines() if l.strip()]
        assert len(lines) == 1, f"Expected 1 line (keep-FIRST), got {len(lines)}"


# ---------------------------------------------------------------------------
# 8. T0 basis/countdown contract — A03/A04/A05 acceptance pins (RED until T0-FIX)
# ---------------------------------------------------------------------------

def _t0_write_json(path: Path, payload) -> None:
    """Write a T0 fixture JSON file (UTF-8 so ZH strings round-trip)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _t0_release_forecast_artifact() -> dict:
    """Synthetic release_forecast.v2 artefact for the A04/A05 pins.

    Every value is synthetic — never copied from data/. The cpi_headline item
    carries full qualification metadata (target/epochs/bases/maturity/
    benchmarks) exactly as the v2 artefact declares it.
    """
    return {
        "schema": "release_forecast.v2",
        "asof": "2026-10-09T15:17:19Z",
        "methodology_status": {
            "forecast_epoch": "legacy_cross_vintage_training_target_experimental",
            "accuracy_claim": "withheld_until_clean_aligned_forward_evidence",
            "street_consensus": "unavailable",
        },
        "upcoming": [
            {
                "release_type": "cpi_headline",
                "period": "2026-09",
                "release_date": "2026-10-14",
                "days_to": 5,
                "target": "mom_sa_pct",
                "model_epoch": "champion_legacy_target_v1",
                "target_epoch": "legacy_cross_vintage_initial_levels_v0",
                "primary_forecast_basis": "combined_v1_benchmark_augmented",
                "context_metrics_basis": "champion_legacy_target_v1",
                "coverage_flags": {"weight_coverage": 1.0, "model_maturity": 0},
                "benchmark_set": {
                    "naive_prior": {},
                    "trailing_3m": {},
                    "ar_model": {},
                    "cleveland_nowcast": {},
                    "market_implied": {},
                },
                "projection": {"point": 0.37},
                "surprise_skew": {"tag": "inline", "sigma": -0.14},
            }
        ],
    }


class TestT0BasisCountdownContract:
    """Executable contract for RIC acceptance cases A03/A04/A05.

    These tests are the contract the T0-FIX lane is judged against: the
    unmodified engine fails all three with AssertionError. The engine must be
    repaired to make them pass — the fixture values and expectations here are
    an orchestrator ruling and are never weakened.
    """

    def test_missing_path_has_no_named_source(self, tmp_path):
        """A03: no fed_path evidence ⇒ no named source; never a fabricated default."""
        # 1. Empty root (no files at all): no named source is allowed to appear.
        rp = build_board(root=tmp_path)["board"]["rate_path_row"]
        assert rp["source_en"] is None
        assert rp["source_zh"] is None

        # 2. fed_path present with numbers but NO implied_source_* keys: the
        #    numbers survive and the source stays unnamed.
        r2 = tmp_path / "present_without_source"
        _t0_write_json(r2 / "bonds" / "bond_health.json", {"fed_path": {
            "asof": "2026-10-08",
            "policy_rate": 3.88,
            "implied": {"m1": 3.85, "m3": 3.7, "m6": 3.5, "m12": 3.2},
            "implied_bp_12m": -68,
            "implied_cuts_12m": -3,
        }})
        rp2 = build_board(root=r2)["board"]["rate_path_row"]
        assert rp2["source_en"] is None
        assert rp2["source_zh"] is None
        assert rp2["policy_rate"] == 3.88
        assert rp2["implied_path"]["m12"] == 3.2
        assert rp2["implied_bp_12m"] == -68

        # 3. CONTROL: an explicit implied_source_* passes through verbatim
        #    (no relabelling to ZQ).
        r3 = tmp_path / "explicit_source"
        _t0_write_json(r3 / "bonds" / "bond_health.json", {"fed_path": {
            "asof": "2026-10-08",
            "policy_rate": 3.88,
            "implied": {"m1": 3.85, "m3": 3.7, "m6": 3.5, "m12": 3.2},
            "implied_bp_12m": -68,
            "implied_cuts_12m": -3,
            "implied_source_en": "SR3 SOFR futures",
            "implied_source_zh": "SR3 SOFR期货",
        }})
        rp3 = build_board(root=r3)["board"]["rate_path_row"]
        assert rp3["source_en"] == "SR3 SOFR futures"
        assert rp3["source_zh"] == "SR3 SOFR期货"

    def test_cpi_summary_preserves_target_epoch_and_maturity(self, tmp_path):
        """A04: nearest_cpi carries the artefact's target/epoch/basis/maturity
        qualifications verbatim; missing qualification is None, never a default."""
        _t0_write_json(
            tmp_path / "release_forecast" / "latest.json",
            _t0_release_forecast_artifact(),
        )
        nc = build_board(root=tmp_path)["board"]["inflation_row"]["nearest_cpi"]
        # 1. The model's target identity survives.
        assert nc.get("target") == "mom_sa_pct"
        # 2. Model/target epoch and bases travel with the value.
        assert nc.get("model_epoch") == "champion_legacy_target_v1"
        assert nc.get("target_epoch") == "legacy_cross_vintage_initial_levels_v0"
        assert nc.get("primary_forecast_basis") == "combined_v1_benchmark_augmented"
        assert nc.get("context_metrics_basis") == "champion_legacy_target_v1"
        # 3. Maturity zero is zero, not missing.
        assert "model_maturity" in nc and nc["model_maturity"] == 0 \
            and nc["model_maturity"] is not None
        # 4. Artefact-level methodology status is surfaced, not dropped.
        assert nc.get("forecast_epoch") == "legacy_cross_vintage_training_target_experimental"
        assert nc.get("accuracy_claim") == "withheld_until_clean_aligned_forward_evidence"
        # 5. Benchmark family is the sorted key set of benchmark_set.
        assert nc.get("benchmark_ids") == [
            "ar_model", "cleveland_nowcast", "market_implied", "naive_prior", "trailing_3m",
        ]
        # 6. First-print basis is UNKNOWN because the artefact declares none —
        #    never inferred.
        assert "first_print_basis" in nc and nc["first_print_basis"] is None
        # 7. Existing display fields are unchanged.
        assert nc["point"] == 0.37
        assert nc["days_to"] == 5
        assert nc["release_date"] == "2026-10-14"
        assert nc["surprise_skew_tag"] == "inline"

        # 8. MISSING-QUALIFICATION case: a bare artefact yields every
        #    qualification key present with value None — never a default string.
        r2 = tmp_path / "bare"
        _t0_write_json(r2 / "release_forecast" / "latest.json", {
            "schema": "release_forecast.v2",
            "asof": "2026-10-09T15:17:19Z",
            "upcoming": [{
                "release_type": "cpi_headline",
                "period": "2026-09",
                "release_date": "2026-10-14",
                "days_to": 5,
                "projection": {"point": 0.2},
            }],
        })
        nc2 = build_board(root=r2)["board"]["inflation_row"]["nearest_cpi"]
        for key in (
            "target", "model_epoch", "target_epoch", "primary_forecast_basis",
            "context_metrics_basis", "model_maturity", "forecast_epoch",
            "accuracy_claim", "benchmark_ids", "first_print_basis",
        ):
            assert key in nc2, key
            assert nc2[key] is None, (key, nc2[key])

        # 9. EXPLICIT first-print case: passes through verbatim.
        r3 = tmp_path / "first_print"
        artefact = _t0_release_forecast_artifact()
        artefact["upcoming"][0]["first_print_basis"] = "first_print"
        _t0_write_json(r3 / "release_forecast" / "latest.json", artefact)
        nc3 = build_board(root=r3)["board"]["inflation_row"]["nearest_cpi"]
        assert nc3["first_print_basis"] == "first_print"

    def test_countdown_binds_display_cutoff_without_restamping_evidence(self, tmp_path):
        """A05: countdown binds the display cutoff to the calendar release date
        while the source snapshot fields stay untouched (never restamped)."""
        _t0_write_json(
            tmp_path / "release_forecast" / "latest.json",
            _t0_release_forecast_artifact(),
        )
        # 1. No explicit cutoff — must be a dict (first call, no cutoff kwarg).
        r0 = build_board(root=tmp_path)
        nc0 = r0["board"]["inflation_row"]["nearest_cpi"]
        cd0 = nc0.get("countdown")
        assert isinstance(cd0, dict), cd0
        # 2. No explicit cutoff ⇒ historical at the source snapshot, never
        #    current; the evidence fields stay verbatim.
        assert cd0.get("source_cutoff") == "2026-10-09T15:17:19Z"
        assert cd0.get("source_days_to") == 5
        assert cd0.get("display_cutoff") is None
        assert cd0.get("days_to") is None
        assert cd0.get("state") == "historical"
        assert cd0.get("method") == "source_snapshot"
        assert nc0["days_to"] == 5
        # 3. Re-render stability: no wall-clock dependence.
        cd0_again = build_board(
            root=tmp_path
        )["board"]["inflation_row"]["nearest_cpi"].get("countdown")
        assert cd0_again == cd0
        # 4. Explicit display cutoff recomputes from the artefact's calendar
        #    release date; source snapshot fields are NOT restamped.
        nc_cut = build_board(
            root=tmp_path, cutoff="2026-10-12",
        )["board"]["inflation_row"]["nearest_cpi"]
        cd = nc_cut.get("countdown")
        assert cd.get("display_cutoff") == "2026-10-12"
        assert cd.get("days_to") == 2
        assert cd.get("state") == "current"
        assert cd.get("method") == "release_forecast_release_date"
        assert cd.get("source_cutoff") == "2026-10-09T15:17:19Z"
        assert cd.get("source_days_to") == 5
        assert nc_cut["days_to"] == 5
        # 5. Same day as the source snapshot.
        cd5 = build_board(
            root=tmp_path, cutoff="2026-10-09",
        )["board"]["inflation_row"]["nearest_cpi"].get("countdown")
        assert cd5.get("state") == "current"
        assert cd5.get("days_to") == 5
        # 6. Release day.
        cd6 = build_board(
            root=tmp_path, cutoff="2026-10-14",
        )["board"]["inflation_row"]["nearest_cpi"].get("countdown")
        assert cd6.get("state") == "current"
        assert cd6.get("days_to") == 0
        # 7. After release.
        cd7 = build_board(
            root=tmp_path, cutoff="2026-10-15",
        )["board"]["inflation_row"]["nearest_cpi"].get("countdown")
        assert cd7.get("state") == "released"
        assert cd7.get("days_to") is None
        # 8. Display cutoff BEFORE the evidence existed (late evidence).
        cd8 = build_board(
            root=tmp_path, cutoff="2026-10-08",
        )["board"]["inflation_row"]["nearest_cpi"].get("countdown")
        assert cd8.get("state") == "source_after_display_cutoff"
        assert cd8.get("days_to") is None
        # 9. Malformed calendar date: no exception, state unknown.
        r2 = tmp_path / "bad_date"
        artefact = _t0_release_forecast_artifact()
        artefact["upcoming"][0]["release_date"] = "not-a-date"
        _t0_write_json(r2 / "release_forecast" / "latest.json", artefact)
        cd_bad = build_board(
            root=r2, cutoff="2026-10-12",
        )["board"]["inflation_row"]["nearest_cpi"].get("countdown")
        assert isinstance(cd_bad, dict), cd_bad
        assert cd_bad.get("state") == "unknown"
        assert cd_bad.get("days_to") is None
        assert cd_bad.get("source_days_to") == 5
        # 10. Malformed display cutoff: no exception, state unknown.
        cd_garbage = build_board(
            root=tmp_path, cutoff="garbage",
        )["board"]["inflation_row"]["nearest_cpi"].get("countdown")
        assert isinstance(cd_garbage, dict), cd_garbage
        assert cd_garbage.get("state") == "unknown"
        assert cd_garbage.get("days_to") is None


class TestT0FixAContract:
    """T0-FIX-A extra contract: malformed inputs fail open, unchanged-input
    controls, immutable old artefacts, per-state rendering (EN+ZH), lean
    mapping, and template/builder source pins. All fixtures synthetic."""

    @staticmethod
    def _render_block_d(row: dict) -> str:
        """Render template block d (Inflation Read) against an inflation row."""
        import jinja2

        src = (
            Path(__file__).resolve().parents[1] / "templates" / "dashboard.html.j2"
        ).read_text(encoding="utf-8")
        i = src.index("      {# ── d. Inflation Read")
        j = src.index("      {# ── e. Risk Indicators")
        return jinja2.Environment(autoescape=True).from_string(src[i:j]).render(
            _dlgrc_inf=row
        )

    @staticmethod
    def _qualified_row(display_cutoff):
        """Build a qualified nearest-CPI row end-to-end from the RED fixture."""
        from engine.rates_inflation_command import _build_inflation_row

        artefact = _t0_release_forecast_artifact()
        return _build_inflation_row(
            {"state": {"inflation": {"core_pce_yoy": 2.9}}},
            artefact["upcoming"],
            release_meta=artefact,
            display_cutoff=display_cutoff,
        )

    # ------------------------------------------------------------------ #
    # 1. MALFORMED fed_path fields
    # ------------------------------------------------------------------ #
    def test_malformed_fed_path_fields_fail_open(self, tmp_path):
        r = tmp_path / "malformed"
        _t0_write_json(r / "bonds" / "bond_health.json", {"fed_path": {
            "asof": "2026-10-08",
            "implied": [1, 2, 3],
            "dots": {"a": 1},
            "gap": "oops",
        }})
        rp = build_board(root=r)["board"]["rate_path_row"]
        for m in ("m1", "m3", "m6", "m12"):
            assert rp["implied_path"][m] is None, m
        assert rp["dots"] == []
        assert rp["gap"] == {}
        assert rp["source_en"] is None
        assert rp["source_zh"] is None

    def test_nondict_fed_path_unit_call(self):
        from engine.rates_inflation_command import _build_rate_path_row

        for bad in ([], None, "x", 7):
            rp = _build_rate_path_row(bad)
            assert rp["source_en"] is None
            assert rp["source_zh"] is None
            assert rp["implied_path"] == {"m1": None, "m3": None, "m6": None, "m12": None}

    # ------------------------------------------------------------------ #
    # 2. MALFORMED release artefact
    # ------------------------------------------------------------------ #
    def test_release_latest_json_list_fails_open(self, tmp_path):
        _t0_write_json(tmp_path / "release_forecast" / "latest.json", ["not", "a", "dict"])
        board = build_board(root=tmp_path)
        assert board["board"]["inflation_row"]["nearest_cpi"] is None

    def test_release_upcoming_dict_fails_open(self, tmp_path):
        artefact = _t0_release_forecast_artifact()
        artefact["upcoming"] = {"release_type": "cpi_headline"}
        _t0_write_json(tmp_path / "release_forecast" / "latest.json", artefact)
        assert build_board(root=tmp_path)["board"]["inflation_row"]["nearest_cpi"] is None

    def test_release_dirty_list_finds_valid_item(self, tmp_path):
        artefact = _t0_release_forecast_artifact()
        valid = artefact["upcoming"][0]
        artefact["upcoming"] = ["x", None, valid]
        _t0_write_json(tmp_path / "release_forecast" / "latest.json", artefact)
        nc = build_board(root=tmp_path)["board"]["inflation_row"]["nearest_cpi"]
        assert nc is not None and nc["point"] == 0.37 and nc["days_to"] == 5

    def test_malformed_qualification_fields_are_none(self, tmp_path):
        artefact = _t0_release_forecast_artifact()
        artefact["methodology_status"] = "not-a-dict"
        artefact["upcoming"][0]["coverage_flags"] = ["not", "a", "dict"]
        artefact["upcoming"][0]["benchmark_set"] = "not-a-dict"
        _t0_write_json(tmp_path / "release_forecast" / "latest.json", artefact)
        nc = build_board(root=tmp_path)["board"]["inflation_row"]["nearest_cpi"]
        assert nc["model_maturity"] is None
        assert nc["benchmark_ids"] is None
        assert nc["forecast_epoch"] is None
        assert nc["accuracy_claim"] is None

    def test_empty_benchmark_set_yields_none(self, tmp_path):
        artefact = _t0_release_forecast_artifact()
        artefact["upcoming"][0]["benchmark_set"] = {}
        _t0_write_json(tmp_path / "release_forecast" / "latest.json", artefact)
        nc = build_board(root=tmp_path)["board"]["inflation_row"]["nearest_cpi"]
        assert nc["benchmark_ids"] is None

    # ------------------------------------------------------------------ #
    # 3. CORRECTED artefact (no stale reuse)
    # ------------------------------------------------------------------ #
    def test_corrected_artefact_no_stale_reuse(self, tmp_path):
        import copy

        path = tmp_path / "release_forecast" / "latest.json"
        artefact = _t0_release_forecast_artifact()
        _t0_write_json(path, artefact)
        nc1 = build_board(root=tmp_path)["board"]["inflation_row"]["nearest_cpi"]
        assert nc1["point"] == 0.37 and nc1["release_date"] == "2026-10-14"
        corrected = copy.deepcopy(artefact)
        corrected["upcoming"][0]["projection"]["point"] = 0.21
        corrected["upcoming"][0]["release_date"] = "2026-10-15"
        _t0_write_json(path, corrected)
        nc2 = build_board(root=tmp_path)["board"]["inflation_row"]["nearest_cpi"]
        assert nc2["point"] == 0.21 and nc2["release_date"] == "2026-10-15"

    # ------------------------------------------------------------------ #
    # 4. UNCHANGED-INPUT CONTROLS
    # ------------------------------------------------------------------ #
    @staticmethod
    def _strip_volatile(board: dict, *, strip_countdown: bool) -> dict:
        import copy

        snap = copy.deepcopy(board)
        snap.pop("built", None)
        if strip_countdown:
            nc = snap.get("board", {}).get("inflation_row", {}).get("nearest_cpi")
            if isinstance(nc, dict):
                nc.pop("countdown", None)
        return snap

    def test_cutoff_touches_only_the_countdown(self, tmp_path):
        _t0_write_json(
            tmp_path / "release_forecast" / "latest.json",
            _t0_release_forecast_artifact(),
        )
        a = build_board(root=tmp_path)
        b = build_board(root=tmp_path, cutoff="2026-10-12")
        # T0-B amendment: each row's basis carries its cutoff BY DESIGN, so
        # the basis records are stripped too before the unchanged-input
        # comparison (the basis cutoff law is pinned by TestT0FixBBasisContract).
        strips = [self._strip_volatile(art, strip_countdown=True) for art in (a, b)]
        for snap in strips:
            snap["board"]["rate_path_row"].pop("basis", None)
            nc = snap["board"]["inflation_row"].get("nearest_cpi")
            if isinstance(nc, dict):
                nc.pop("basis", None)
        assert strips[0] == strips[1]
        # and the countdown really did move
        assert (
            a["board"]["inflation_row"]["nearest_cpi"]["countdown"]["state"] == "historical"
        )
        assert (
            b["board"]["inflation_row"]["nearest_cpi"]["countdown"]["state"] == "current"
        )

    def test_same_cutoff_is_deterministic(self, tmp_path):
        _t0_write_json(
            tmp_path / "release_forecast" / "latest.json",
            _t0_release_forecast_artifact(),
        )
        a = build_board(root=tmp_path, cutoff="2026-10-12")
        b = build_board(root=tmp_path, cutoff="2026-10-12")
        assert self._strip_volatile(a, strip_countdown=False) == self._strip_volatile(
            b, strip_countdown=False
        )

    def test_compact_state_equal_across_cutoffs(self, tmp_path):
        _t0_write_json(
            tmp_path / "release_forecast" / "latest.json",
            _t0_release_forecast_artifact(),
        )
        a = build_board(root=tmp_path)
        b = build_board(root=tmp_path, cutoff="2026-10-12")
        assert compact_state(a) == compact_state(b)

    def test_regime_outlook_never_composed_by_board(self, tmp_path):
        assert "regime_outlook" not in build_board(root=tmp_path)

    # ------------------------------------------------------------------ #
    # 5. IMMUTABLE OLD ARTEFACT (pre-T0 row: seven keys, no countdown)
    # ------------------------------------------------------------------ #
    def test_old_artefact_renders_without_stale_nd(self, tmp_path):
        import copy

        from engine.rates_inflation_command import _build_inflation_row

        row = _build_inflation_row(
            {"state": {"inflation": {"core_pce_yoy": 2.9}}}, []
        )
        row["nearest_cpi"] = {
            "release_type": "cpi_headline",
            "period": "2026-09",
            "release_date": "2026-10-14",
            "days_to": 5,
            "point": 0.37,
            "surprise_skew_tag": "inline",
            "surprise_skew_sigma": None,
        }
        frozen = copy.deepcopy(row)
        out = self._render_block_d(row)
        assert "Next CPI · 2026-10-14" in out
        assert "5d" not in out
        assert "5天" not in out
        assert "Day count not shown" in out
        assert row == frozen  # render never mutates the evidence

        # compact_state / build_changes accept a board carrying the old row
        board = build_board(root=tmp_path)
        board["board"]["inflation_row"] = row
        compact_state(board)
        build_changes(board, copy.deepcopy(board), "2026-10-13")

    # ------------------------------------------------------------------ #
    # 6. RENDER PER COUNTDOWN STATE (EN + ZH)
    # ------------------------------------------------------------------ #
    def test_render_state_current(self):
        out = self._render_block_d(self._qualified_row("2026-10-12"))
        assert "Next CPI · 2d" in out
        assert "下次CPI · 2天" in out
        assert "counted as of 2026-10-12" in out
        assert "5d" not in out

    def test_render_state_released(self):
        out = self._render_block_d(self._qualified_row("2026-10-15"))
        assert "CPI released 2026-10-14" in out
        assert "CPI 已于 2026-10-14 发布" in out

    def test_render_state_source_after_display_cutoff(self):
        out = self._render_block_d(self._qualified_row("2026-10-08"))
        assert "newer than the display date" in out
        assert "晚于显示日期" in out

    def test_render_state_unknown(self):
        out = self._render_block_d(self._qualified_row("garbage"))
        assert "Day count unavailable" in out
        assert "无法计算天数" in out

    def test_render_state_historical(self):
        out = self._render_block_d(self._qualified_row(None))
        assert "Day count not shown" in out
        assert "未显示天数" in out
        assert "5d" not in out

    def test_render_experimental_accuracy_withheld(self):
        out = self._render_block_d(self._qualified_row("2026-10-12"))
        assert "accuracy not yet claimed" in out
        assert "尚未声明准确度" in out

    # ------------------------------------------------------------------ #
    # 7. LEAN mapping
    # ------------------------------------------------------------------ #
    def test_lean_absent_when_tag_none(self):
        import copy

        from engine.rates_inflation_command import _build_inflation_row

        row = _build_inflation_row(
            {"state": {"inflation": {"core_pce_yoy": 2.9}}}, []
        )
        row["nearest_cpi"] = {
            "release_type": "cpi_headline",
            "period": "2026-09",
            "release_date": "2026-10-14",
            "days_to": 5,
            "point": 0.37,
            "surprise_skew_tag": None,
            "surprise_skew_sigma": None,
        }
        out = self._render_block_d(row)
        assert "Recent-data lean not available" in out
        assert "leans in line" not in out

    def test_lean_inline_and_hotter(self):
        import copy

        from engine.rates_inflation_command import _build_inflation_row

        for tag, expect in (("inline", "leans in line"), ("hotter", "hotter than forecast")):
            row = _build_inflation_row(
                {"state": {"inflation": {"core_pce_yoy": 2.9}}}, []
            )
            row["nearest_cpi"] = {
                "release_type": "cpi_headline",
                "period": "2026-09",
                "release_date": "2026-10-14",
                "days_to": 5,
                "point": 0.37,
                "surprise_skew_tag": tag,
                "surprise_skew_sigma": -0.14,
            }
            out = self._render_block_d(row)
            assert expect in out, tag

    # ------------------------------------------------------------------ #
    # 8. TEMPLATE source pins (A03 display honesty)
    # ------------------------------------------------------------------ #
    def test_template_source_pins(self):
        text = (
            Path(__file__).resolve().parents[1] / "templates" / "dashboard.html.j2"
        ).read_text(encoding="utf-8")
        assert "(ZQ fed-funds futures)" not in text
        assert "'Market-implied fed-funds path.'" not in text
        assert "(source not recorded)" in text
        assert "Path source: not recorded for this read." in text

    # ------------------------------------------------------------------ #
    # 9. BUILDER pin (build-time cutoff wired at the call site)
    # ------------------------------------------------------------------ #
    def test_builder_pins_display_cutoff(self):
        text = (
            Path(__file__).resolve().parents[1] / "scripts" / "build_rates_command.py"
        ).read_text(encoding="utf-8")
        assert (
            "build_board(cutoff=datetime.now(timezone.utc).date().isoformat())" in text
        )


# ---------------------------------------------------------------------------
# T0-FIX-B: board rows carry rates_command_basis.v1 QualifiedObservations
# ---------------------------------------------------------------------------

class TestT0FixBBasisContract:
    """T0-B contract: both quantitative board rows carry their basis as a
    frozen rates_command_basis.v1 QualifiedObservation (`.to_dict()`), so the
    C0 comparison layer can refuse cross-basis gaps (ZQ≠SR3, CPI≠PCE,
    forecast≠first print) from the row itself. All fixtures synthetic."""

    @staticmethod
    def _schema():
        import jsonschema

        schema = json.loads(
            (
                Path(__file__).resolve().parents[1]
                / "contracts"
                / "rates_command_basis.v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        return jsonschema.Draft202012Validator(
            {"$ref": "#/$defs/QualifiedObservation", "$defs": schema["$defs"]}
        )

    @staticmethod
    def _fed_path(label="ZQ fed-funds futures", m12=3.2, asof="2026-10-08"):
        fp = {
            "asof": asof,
            "policy_rate": 3.88,
            "implied": {"m1": 3.85, "m3": 3.7, "m6": 3.5, "m12": m12},
            "implied_bp_12m": -68,
            "implied_cuts_12m": -3,
        }
        if label is not None:
            fp["implied_source_en"] = label
            fp["implied_source_zh"] = "ZQ 联邦基金期货"
        return fp

    @staticmethod
    def _write(root, *, fed_path=None, artefact=None):
        if fed_path is not None:
            _t0_write_json(root / "bonds" / "bond_health.json", {"fed_path": fed_path})
        if artefact is not None:
            _t0_write_json(root / "release_forecast" / "latest.json", artefact)
        return root

    # 1. ZQ round trip ----------------------------------------------------
    def test_zq_basis_round_trips(self, tmp_path):
        from engine.rates_command_basis import QualifiedObservation

        root = self._write(tmp_path / "zq", fed_path=self._fed_path())
        b = build_board(root=root)["board"]["rate_path_row"]["basis"]
        assert b is not None
        self._schema().validate(b)
        assert b["rate_index"] == "EFFR"
        assert b["averaging_law"] == "arithmetic_calendar_day"
        assert b["evidence_class"] == "market_implied_expectation"
        assert b["value"] == 3.2 and b["value_state"] == "present"
        assert QualifiedObservation.from_dict(b).to_dict() == b

    # 2. SR3 vs ZQ refused from the row itself ----------------------------
    def test_sr3_vs_zq_refused_from_board_rows(self, tmp_path):
        from engine import rates_command_basis as rcb

        zq_root = self._write(
            tmp_path / "zq", fed_path=self._fed_path("ZQ fed-funds futures")
        )
        sr3_root = self._write(
            tmp_path / "sr3", fed_path=self._fed_path("SR3 SOFR futures")
        )
        zq = build_board(root=zq_root)["board"]["rate_path_row"]["basis"]
        sr3 = build_board(root=sr3_root)["board"]["rate_path_row"]["basis"]
        assert zq["rate_index"] == "EFFR" and sr3["rate_index"] == "SOFR"
        result = rcb.compare_qualified(
            rcb.QualifiedObservation.from_dict(sr3),
            rcb.QualifiedObservation.from_dict(zq),
            rcb.RULES["sr3_vs_zq.v1"],
        )
        assert result.status.value == "not_comparable"
        assert result.difference is None

    # 3. Unknown source stays UNKNOWN --------------------------------------
    def test_unknown_source_basis_is_unknown(self, tmp_path):
        root = self._write(tmp_path / "nosrc", fed_path=self._fed_path(label=None))
        b = build_board(root=root)["board"]["rate_path_row"]["basis"]
        assert b is not None
        self._schema().validate(b)
        assert b["rate_index"] is None
        assert b["averaging_law"] is None
        assert b["source"] is None
        assert "source_unknown" in b["limitations"]

    # 4. Missing m12 is missing, never zero --------------------------------
    def test_missing_m12_is_missing_not_zero(self, tmp_path):
        for name, m12 in (("absent", None), ("nonnum", "abc")):
            root = self._write(
                tmp_path / name, fed_path=self._fed_path(m12=m12)
            )
            b = build_board(root=root)["board"]["rate_path_row"]["basis"]
            assert b["value"] is None, (name, b)
            assert b["value_state"] == "missing", (name, b)

    # 5. first_print suffix only when declared ------------------------------
    def test_cpi_first_print_only_when_declared(self, tmp_path):
        import copy

        undeclared = _t0_release_forecast_artifact()
        root1 = self._write(tmp_path / "undecl", artefact=undeclared)
        b1 = build_board(root=root1)["board"]["inflation_row"]["nearest_cpi"]["basis"]
        assert b1 is not None
        assert not b1["target"].endswith("_first_print")
        assert "first_print_basis_undeclared" in b1["limitations"]

        declared = copy.deepcopy(undeclared)
        declared["upcoming"][0]["first_print_basis"] = "first_print"
        root2 = self._write(tmp_path / "decl", artefact=declared)
        b2 = build_board(root=root2)["board"]["inflation_row"]["nearest_cpi"]["basis"]
        assert b2["target"].endswith("_first_print")
        assert b2["obs_id"] != b1["obs_id"]

    # 6. Model status carries into quality flags ---------------------------
    def test_cpi_quality_flags(self, tmp_path):
        root = self._write(tmp_path / "q", artefact=_t0_release_forecast_artifact())
        b = build_board(root=root)["board"]["inflation_row"]["nearest_cpi"]["basis"]
        assert b is not None
        assert {"experimental", "accuracy_withheld"} <= set(b["quality"])

    # 7. Unknown target ⇒ no basis at all ----------------------------------
    def test_cpi_unknown_target_has_no_basis(self, tmp_path):
        artefact = _t0_release_forecast_artifact()
        del artefact["upcoming"][0]["target"]
        root = self._write(tmp_path / "notarget", artefact=artefact)
        nc = build_board(root=root)["board"]["inflation_row"]["nearest_cpi"]
        assert nc is not None
        assert nc["basis"] is None

    # 8. Late evidence refused at the cutoff, row untouched -----------------
    def test_late_input_refused_at_cutoff(self, tmp_path):
        root = self._write(tmp_path / "late", fed_path=self._fed_path(asof="2026-10-08"))
        board = build_board(root=root, cutoff="2026-10-07")["board"]
        b = board["rate_path_row"]["basis"]
        assert b["value"] is None and b["value_state"] == "refused"
        assert "after_cutoff" in b["limitations"]
        # The basis never edits the row's display fields.
        assert board["rate_path_row"]["implied_bp_12m"] == -68
        assert board["rate_path_row"]["implied_path"]["m12"] == 3.2
        assert board["rate_path_row"]["implied_cuts_12m"] == -3

    # 9. Determinism and cutoff binding ------------------------------------
    def test_basis_deterministic_and_cutoff_bound(self, tmp_path):
        root = self._write(tmp_path / "det", fed_path=self._fed_path())
        a = build_board(root=root, cutoff="2026-10-12")["board"]["rate_path_row"]["basis"]
        b = build_board(root=root, cutoff="2026-10-12")["board"]["rate_path_row"]["basis"]
        assert a == b
        c = build_board(root=root, cutoff="2026-10-13")["board"]["rate_path_row"]["basis"]
        assert c["obs_id"] != a["obs_id"]

    # 10. Top-level contract version + old-artefact compat ------------------
    def test_top_level_contract_version(self, tmp_path):
        import copy

        root = self._write(
            tmp_path / "top",
            fed_path=self._fed_path(),
            artefact=_t0_release_forecast_artifact(),
        )
        board = build_board(root=root)
        assert board["basis_contract_version"] == "rates_command_basis.v1"
        assert board["qualified_comparisons"] == []
        old = copy.deepcopy(board)
        old["board"]["rate_path_row"].pop("basis", None)
        old["board"]["inflation_row"]["nearest_cpi"].pop("basis", None)
        old.pop("basis_contract_version", None)
        old.pop("qualified_comparisons", None)
        assert compact_state(old) == compact_state(board)

    # 11. Empty / malformed inputs never raise -------------------------------
    def test_empty_and_malformed_inputs(self, tmp_path):
        board = build_board(root=tmp_path / "empty")
        assert board["board"]["rate_path_row"]["basis"] is None
        assert board["board"]["inflation_row"]["nearest_cpi"] is None
        root = self._write(
            tmp_path / "mal", fed_path=self._fed_path(asof="not-a-date")
        )
        b = build_board(root=root)["board"]["rate_path_row"]["basis"]
        assert b is not None
        assert b["observation_precision"] == "unknown"
        self._schema().validate(b)

    # 12. ZH caption: missing cuts are unknown, never zero -------------------
    def test_zh_caption_missing_cuts_is_unknown_not_zero(self):
        import jinja2

        src = (
            Path(__file__).resolve().parents[1] / "templates" / "dashboard.html.j2"
        ).read_text(encoding="utf-8")
        i = src.index("{# ZH mirrors the EN preference order")
        j = src.index("{# Gap chip (Fed vs market divergence) #}")
        block = src[i:j]
        env = jinja2.Environment()
        out_empty = env.from_string(block).render(_dfp={})
        assert "来源未记录" in out_empty
        assert "次" not in out_empty
        out_two = env.from_string(block).render(
            _dfp={"implied_cuts_12m": 2.0, "implied_source_zh": "ZQ联邦基金期货"}
        )
        assert "约2次降息" in out_two
        assert "（ZQ联邦基金期货）" in out_two
        out_none = env.from_string(block).render(_dfp={"implied_cuts_12m": None})
        assert "0次" not in out_none

    # 13. Unknown string label stays UNKNOWN, never silently ZQ --------------
    def test_unknown_string_source_is_unknown_not_zq(self, tmp_path):
        labels = ("mystery feed", "zq fed-funds futures", "ZQ fed-funds futures ", "")
        for i, label in enumerate(labels):
            root = self._write(tmp_path / f"u{i}", fed_path=self._fed_path(label=label))
            b = build_board(root=root)["board"]["rate_path_row"]["basis"]
            assert b is not None, (label, b)
            self._schema().validate(b)
            assert b["rate_index"] is None, (label, b)
            assert b["averaging_law"] is None, (label, b)
            assert b["source"] is None, (label, b)
            assert "source_unknown" in b["limitations"], (label, b)
            assert "degraded_front_month_only" not in b["limitations"], (label, b)

    # 14. Front-month-only label: declared ZQ, degraded, m12 missing ----------
    def test_front_month_only_label_is_degraded_zq_and_m12_missing(self, tmp_path):
        root = self._write(
            tmp_path / "front",
            fed_path=self._fed_path(label="ZQ front (30d) only", m12=None),
        )
        b = build_board(root=root)["board"]["rate_path_row"]["basis"]
        assert b is not None
        self._schema().validate(b)
        assert b["rate_index"] == "EFFR"
        assert b["averaging_law"] == "arithmetic_calendar_day"
        assert b["source"] == "rate_futures:ZQ"
        assert "degraded_front_month_only" in b["limitations"]
        assert "source_unknown" not in b["limitations"]
        assert b["value"] is None
        assert b["value_state"] == "missing"

    # 15. CPI target gate is byte-exact to the producer string ----------------
    def test_cpi_target_gate_is_byte_exact(self, tmp_path):
        import copy

        variants = ("Mom_sa_pct", "MOM_SA_PCT", "mom_sa_pct ")
        for i, target in enumerate(variants):
            artefact = copy.deepcopy(_t0_release_forecast_artifact())
            artefact["upcoming"][0]["target"] = target
            root = self._write(tmp_path / f"g{i}", artefact=artefact)
            nc = build_board(root=root)["board"]["inflation_row"]["nearest_cpi"]
            assert nc is not None, (target, nc)
            assert nc["basis"] is None, (target, nc)
        control_root = self._write(
            tmp_path / "gc", artefact=_t0_release_forecast_artifact()
        )
        nc = build_board(root=control_root)["board"]["inflation_row"]["nearest_cpi"]
        assert nc is not None and nc["basis"] is not None

    # 16. CPI row late evidence refused at the cutoff, display untouched ------
    def test_cpi_late_input_refused_at_cutoff(self, tmp_path):
        root = self._write(tmp_path / "cpilate", artefact=_t0_release_forecast_artifact())
        board = build_board(root=root, cutoff="2026-10-08")["board"]
        nc = board["inflation_row"]["nearest_cpi"]
        b = nc["basis"]
        assert b is not None
        assert b["value"] is None and b["value_state"] == "refused"
        assert "after_cutoff" in b["limitations"]
        # The basis never edits the row's display field.
        assert nc["point"] == 0.37
        fresh = build_board(root=root, cutoff="2026-10-10")["board"]
        b2 = fresh["inflation_row"]["nearest_cpi"]["basis"]
        assert b2 is not None
        assert b2["value"] == 0.37 and b2["value_state"] == "present"
