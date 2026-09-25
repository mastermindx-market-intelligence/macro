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


# RD2: actual collector -> incumbent store -> RIC measurement path.
def _rd2_frames(*, shift=0.0, missing_old=None, dates=('2026-09-30', '2026-10-01'),
                root='ZQ', cadence='monthly', capture='2026-10-02T09:00:00Z'):
    from collectors import rate_futures as rf
    from engine.rate_futures_repricing import attach_constituents
    idx = pd.DatetimeIndex(dates)
    months = [(2026 + (9 + i) // 12, (9 + i) % 12 + 1) for i in range(15)]
    if root == 'SR3':
        months = [(2026, 9), (2026, 12), (2027, 3), (2027, 6), (2027, 9), (2027, 12)]
    contracts, symbols = {}, {}
    for i, (year, month) in enumerate(months):
        rate = 4.0 + i * 0.1
        contracts[(year, month)] = pd.Series([100 - rate, 100 - rate - shift], index=idx)
        symbols[(year, month)] = f'{root}{rf._MONTH_CODE[month]}{year % 100:02d}.CBT'
    if missing_old is not None:
        contracts[months[missing_old]].iloc[0] = float('nan')
    path, components = rf.implied_path_with_components(contracts, [1, 3, 6, 12], 18, cadence)
    return attach_constituents(path, components, contracts, symbols,
        root=root, cadence=cadence, max_months=18, captured_at=capture)


def _rd2_store(tmp_path, pair, key='zq'):
    folder = tmp_path / 'rate_futures'
    folder.mkdir(exist_ok=True)
    pair[0].to_parquet(folder / f'{key}_path.parquet')
    pair[1].to_parquet(folder / f'{key}_constituents.parquet')


def _rd2_read(tmp_path):
    from engine.rate_futures_repricing import build_policy_repricing
    return build_policy_repricing(tmp_path, asof='2026-10-01',
                                  evaluated_at='2026-10-02T10:00:00Z')


def test_rd2_unchanged_contracts_can_move_rolling_path(tmp_path):
    _rd2_store(tmp_path, _rd2_frames())
    out = _rd2_read(tmp_path)['families']['zq']['horizons']['m12']
    assert out['status'] == 'available'
    assert out['raw_change_bp'] == pytest.approx(10)
    assert out['matched_contract_change_bp'] == pytest.approx(0)
    assert out['roll_change_bp'] == pytest.approx(10)
    assert abs(out['rounding_residual_bp']) < 1e-8


def test_rd2_fixed_weights_isolate_contract_change(tmp_path):
    _rd2_store(tmp_path, _rd2_frames(shift=.15, dates=('2026-09-29', '2026-09-30')))
    out = _rd2_read(tmp_path)['families']['zq']['horizons']['m12']
    assert out['matched_contract_change_bp'] == pytest.approx(15)
    assert out['roll_change_bp'] == pytest.approx(0)


def test_rd2_simultaneous_repricing_and_roll_reconcile(tmp_path):
    _rd2_store(tmp_path, _rd2_frames(shift=.15))
    out = _rd2_read(tmp_path)['families']['zq']['horizons']['m12']
    assert out['raw_change_bp'] == pytest.approx(25)
    assert out['matched_contract_change_bp'] == pytest.approx(15)
    assert out['roll_change_bp'] == pytest.approx(10)


def test_rd2_missing_entering_quote_withholds_not_zero_fills(tmp_path):
    _rd2_store(tmp_path, _rd2_frames(missing_old=12))
    out = _rd2_read(tmp_path)['families']['zq']['horizons']['m12']
    assert out['status'] == 'unavailable'
    assert out['matched_contract_change_bp'] is None
    assert out['reason'] == 'incomplete_matched_components'


def test_rd2_reference_periods_and_in_progress_meaning(tmp_path):
    from engine.rate_futures_repricing import reference_period
    assert reference_period('ZQ', 2026, 10) == ('2026-10-01', '2026-11-01')
    assert reference_period('SR3', 2026, 9) == ('2026-09-16', '2026-12-16')
    _rd2_store(tmp_path, _rd2_frames(root='SR3', cadence='quarterly'), key='sofr')
    out = _rd2_read(tmp_path)['families']['sofr']
    assert out['rate_family'] == 'SOFR'
    assert out['horizons']['m3']['status'] == 'available'
    assert out['horizons']['m3']['forward_reference_only'] is False
    assert out['historical_availability_qualified'] is False


def test_rd2_generation_mismatch_cannot_mix_two_writes(tmp_path):
    path, evidence = _rd2_frames()
    path.loc[path.index[-1], '_constituents_token'] += 1
    _rd2_store(tmp_path, (path, evidence))
    out = _rd2_read(tmp_path)['families']['zq']
    assert out['status'] == 'unavailable'
    assert out['reason'] == 'generation_mismatch'


def test_rd2_same_day_capture_never_becomes_certified_overnight(tmp_path):
    _rd2_store(tmp_path, _rd2_frames(capture='2026-10-01T15:00:00Z'))
    out = _rd2_read(tmp_path)['families']['zq']
    assert out['status'] == 'unavailable'
    assert out['reason'] == 'capture_may_include_incomplete_bar'


def test_rd2_future_capture_is_unavailable(tmp_path):
    _rd2_store(tmp_path, _rd2_frames(capture='2026-10-03T09:00:00Z'))
    assert _rd2_read(tmp_path)['families']['zq']['reason'] == 'capture_after_decision'


def test_rd2_stale_latest_is_not_flat_forecast(tmp_path):
    from engine.rate_futures_repricing import build_policy_repricing
    _rd2_store(tmp_path, _rd2_frames())
    out = build_policy_repricing(tmp_path, asof='2026-10-12',
                                evaluated_at='2026-10-12T12:00:00Z')
    assert out['families']['zq']['reason'] == 'stale_source'
    assert out['authority'] is False and out['can_trade'] is False


def test_rd2_invalid_latest_does_not_fall_back_silently(tmp_path):
    path, evidence = _rd2_frames()
    evidence.loc[evidence.index[-1], 'snapshot_json'] = '{bad json'
    _rd2_store(tmp_path, (path, evidence))
    assert _rd2_read(tmp_path)['families']['zq']['status'] == 'unavailable'


def test_rd2_missing_source_explicit_and_authority_false(tmp_path):
    out = _rd2_read(tmp_path)
    assert out['families']['zq']['reason'] == 'missing_source'
    assert out['families']['sofr']['reason'] == 'missing_source'
    assert out['can_rank'] is False and out['can_gate'] is False
    json.dumps(out, allow_nan=False)


def _rd2_native_fetch(monkeypatch):
    from datetime import datetime, timezone
    from types import SimpleNamespace
    from collectors import rate_futures as rf
    moment = datetime(2026, 10, 2, 9, tzinfo=timezone.utc)
    monkeypatch.setattr(rf, 'datetime', SimpleNamespace(now=lambda tz: moment))
    monkeypatch.setitem(sys.modules, 'yfinance', SimpleNamespace())
    adapter = rf.RateFuturesAdapter()
    adapter.cfg = {'horizons_m': [1, 3, 6, 12], 'max_months': 18,
                   'roots': {'zq': {'symbol_root': 'ZQ', 'exchanges': ['CBT'],
                                    'cadence': 'monthly', 'months': 14}}}
    idx = pd.DatetimeIndex(['2026-09-30', '2026-10-01'])
    entries, series = {}, {}
    for i, contract in enumerate(rf.gen_contracts('ZQ', ['CBT'], 'monthly', 14, moment.date())):
        quote = pd.Series([96 - .1 * i, 95.85 - .1 * i], index=idx)
        series[(contract['year'], contract['month'])] = quote
        entries[contract['symbols'][0]] = quote.to_frame('Close')
    raw = pd.concat(entries, axis=1)
    monkeypatch.setattr(adapter, '_download', lambda symbols, period, yf: raw)
    return adapter, adapter.fetch(), rf.implied_path(series, [1, 3, 6, 12], 18, 'monthly')


def test_rd2_native_collector_and_store_roundtrip(monkeypatch, tmp_path):
    from lib import config, store
    from engine import fed_path as fp
    adapter, frames, legacy = _rd2_native_fetch(monkeypatch)
    assert set(frames) == {'zq_path', 'zq_constituents'}
    pd.testing.assert_frame_equal(frames['zq_path'][list(legacy.columns)], legacy)
    monkeypatch.setattr(config, 'data_dir', lambda: tmp_path)
    for key, frame in frames.items():
        cleaned = adapter.validate(key, frame)
        store.upsert('rate_futures', key, cleaned)
    out = _rd2_read(tmp_path)['families']['zq']['horizons']['m12']
    assert out['matched_contract_change_bp'] == pytest.approx(15)
    assert out['roll_change_bp'] == pytest.approx(10)
    old_row, old_date = fp._read_path_row('zq_path')
    assert old_row['m12'] == pytest.approx(legacy.iloc[-1]['m12'])
    assert old_date == '2026-10-01'


def test_rd2_ric_real_consumer_preserves_stance(monkeypatch, tmp_path):
    from datetime import datetime, timezone
    from types import SimpleNamespace
    from engine import rates_inflation_command as ric
    monkeypatch.setattr(ric, 'datetime', SimpleNamespace(
        now=lambda tz: datetime(2026, 10, 2, 10, tzinfo=timezone.utc)))
    baseline = ric.build_board(root=tmp_path)
    _rd2_store(tmp_path, _rd2_frames(shift=.15))
    out = ric.build_board(root=tmp_path)
    assert out['policy_path_repricing']['families']['zq']['horizons']['m12']['roll_change_bp'] == pytest.approx(10)
    assert out['policy_path_repricing']['can_trade'] is False
    assert out['stance'] == baseline['stance']


def _rd2_reseal(pair, mutate):
    from hashlib import sha256
    path, evidence = pair
    stamp = evidence.index[-1]
    payload = json.loads(evidence.loc[stamp, 'snapshot_json'])['payload']
    mutate(payload)
    raw = json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False)
    digest = sha256(raw.encode()).hexdigest()
    token = int(digest[:13], 16)
    path.loc[stamp, '_constituents_token'] = token
    evidence.loc[stamp, '_constituents_token'] = token
    evidence.loc[stamp, 'snapshot_json'] = json.dumps({'payload': payload, 'sha256': digest})
    return path, evidence


@pytest.mark.parametrize('field,value', [
    ('rate_family', 'SOFR'), ('schema', 'unknown'),
    ('historical_availability_qualified', True), ('weight_basis', 'exact_day_forward_rate')])
def test_rd2_resealed_unsupported_semantics_still_fail(tmp_path, field, value):
    _rd2_store(tmp_path, _rd2_reseal(_rd2_frames(), lambda p: p.update({field: value})))
    assert _rd2_read(tmp_path)['families']['zq']['reason'] == 'unsupported_source_semantics'


def test_rd2_resealed_weights_must_reconstruct_from_actual_contracts(tmp_path):
    def alter(payload):
        payload['components']['m12']['weights'] = {'2027-09': 1.0}
    _rd2_store(tmp_path, _rd2_reseal(_rd2_frames(), alter))
    assert _rd2_read(tmp_path)['families']['zq']['reason'] == 'constituent_weights_do_not_reproduce_path'


def test_rd2_torn_numeric_correction_does_not_pass_token_only_check(tmp_path):
    path, evidence = _rd2_frames()
    path.loc[path.index[-1], 'm12'] += .1
    _rd2_store(tmp_path, (path, evidence))
    assert _rd2_read(tmp_path)['families']['zq']['reason'] == 'published_path_mismatch'


def test_rd2_daily_cut_cannot_make_old_data_fresh_at_current_evaluation(tmp_path):
    from engine.rate_futures_repricing import build_policy_repricing
    _rd2_store(tmp_path, _rd2_frames())
    out = build_policy_repricing(tmp_path, asof='2026-10-01', evaluated_at='2026-10-12T12:00:00Z')
    assert out['families']['zq']['reason'] == 'stale_source'


def test_rd2_batch_quotes_without_contract_identity_are_rejected(monkeypatch):
    adapter, _, _ = _rd2_native_fetch(monkeypatch)
    ambiguous = pd.DataFrame({'Close': [96.0, 95.9]},
                              index=pd.DatetimeIndex(['2026-09-30', '2026-10-01']))
    monkeypatch.setattr(adapter, '_download', lambda symbols, period, yf: ambiguous)
    with pytest.raises(ValueError, match='batch_quotes_lack_contract_identity'):
        adapter.fetch()


def test_rd2_duplicate_source_dates_are_not_silently_deduplicated(tmp_path):
    path, evidence = _rd2_frames()
    path = pd.concat([path, path.iloc[-1:]])
    _rd2_store(tmp_path, (path, evidence))
    assert _rd2_read(tmp_path)['families']['zq']['reason'] == 'invalid_daily_source_grid'


def test_rd2_incomplete_family_does_not_erase_other_family(tmp_path):
    _rd2_store(tmp_path, _rd2_frames())
    _rd2_store(tmp_path, _rd2_frames(root='SR3', cadence='quarterly'), key='sofr')
    file = tmp_path / 'rate_futures' / 'sofr_constituents.parquet'
    evidence = pd.read_parquet(file)
    evidence.loc[evidence.index[-1], 'snapshot_json'] = 'invalid'
    evidence.to_parquet(file)
    out = _rd2_read(tmp_path)
    assert out['families']['zq']['horizons']['m12']['status'] == 'available'
    assert out['families']['sofr']['status'] == 'unavailable'


def test_rd2_incomplete_latest_preserves_separately_dated_completed_context(tmp_path, monkeypatch):
    from engine.rate_futures_repricing import build_policy_repricing
    path, evidence = _rd2_frames()
    extra_path, extra_evidence = path.iloc[-1:].copy(), evidence.iloc[-1:].copy()
    extra_path.index = extra_evidence.index = pd.DatetimeIndex(['2026-10-02'])
    pair = pd.concat([path, extra_path]), pd.concat([evidence, extra_evidence])
    pair = _rd2_reseal(pair, lambda p: p.update(
        observation_date='2026-10-02', prior_calendar_day_at_capture=False))
    _rd2_store(tmp_path, pair)
    calls, original = [], pd.read_parquet
    def read_once(file, *args, **kwargs):
        calls.append(str(file))
        return original(file, *args, **kwargs)
    monkeypatch.setattr(pd, 'read_parquet', read_once)
    out = build_policy_repricing(tmp_path, asof='2026-10-02',
                                evaluated_at='2026-10-02T10:00:00Z')['families']['zq']
    assert out['status'] == 'unavailable'
    assert out['reason'] == 'capture_may_include_incomplete_bar'
    context = out['last_completed_observation_context']
    assert context['context_only'] is True
    assert context['observation_dates'] == ['2026-09-30', '2026-10-01']
    assert context['horizons']['m12']['roll_change_bp'] == pytest.approx(10)
    assert context['historical_availability_qualified'] is False
    assert len(calls) == len(set(calls)) == 2


def test_rd2_corrupt_latest_never_launders_prior_context(tmp_path):
    path, evidence = _rd2_frames()
    evidence.loc[evidence.index[-1], 'snapshot_json'] = '{}'
    _rd2_store(tmp_path, (path, evidence))
    out = _rd2_read(tmp_path)['families']['zq']
    assert out['status'] == 'unavailable'
    assert out.get('last_completed_observation_context') is None


def test_rd2_shared_collector_runner_accepts_companion_tables(monkeypatch, tmp_path):
    from copy import deepcopy
    from collectors import base, rate_futures
    from lib import config
    adapter, frames, _ = _rd2_native_fetch(monkeypatch)
    cfg = deepcopy(config.load())
    cfg['storage']['run_status_file'] = 'run_status.json'
    cfg['storage']['data_dir'] = 'data'
    monkeypatch.setattr(config, 'ROOT', tmp_path)
    monkeypatch.setattr(config, 'load', lambda: cfg)
    monkeypatch.setattr(config, 'data_dir', lambda: tmp_path / 'data')
    monkeypatch.setattr(base, 'datetime', rate_futures.datetime)
    result = base.run_adapter(adapter)
    assert result.status == 'ok', result.error
    assert result.rows == sum(len(frame) for frame in frames.values())
    out = _rd2_read(tmp_path / 'data')
    assert out['families']['zq']['horizons']['m12']['matched_contract_change_bp'] == pytest.approx(15)


@pytest.mark.parametrize('prices', [(1e307, 2e307), (-1e307, -2e307)])
def test_rd2_finite_quotes_cannot_publish_nonfinite_attribution(monkeypatch, tmp_path, prices):
    from collectors import rate_futures as rf
    from engine.rate_futures_repricing import build_policy_repricing
    from lib import config, store
    adapter, _, _ = _rd2_native_fetch(monkeypatch)
    idx = pd.DatetimeIndex(['2026-09-30', '2026-10-01'])
    contracts = rf.gen_contracts('ZQ', ['CBT'], 'monthly', 14, rf.datetime.now(None).date())
    raw = pd.concat({c['symbols'][0]: pd.DataFrame({'Close': list(prices)}, index=idx)
                     for c in contracts}, axis=1)
    monkeypatch.setattr(adapter, '_download', lambda symbols, period, yf: raw)
    monkeypatch.setattr(config, 'data_dir', lambda: tmp_path)
    for key, frame in adapter.fetch().items():
        store.upsert(adapter.group, key, adapter.validate(key, frame))
    out = build_policy_repricing(tmp_path, asof='2026-10-01',
                                evaluated_at='2026-10-02T10:00:00Z')
    horizon = out['families']['zq']['horizons']['m12']
    assert horizon['status'] == 'unavailable'
    assert horizon['reason'] == 'nonfinite_derived_attribution'
    for key in ('raw_change_bp', 'matched_contract_change_bp',
                'roll_change_bp', 'rounding_residual_bp'):
        assert horizon[key] is None
    assert out['authority'] is False
    json.dumps(out, allow_nan=False)


@pytest.mark.parametrize('empty', [pd.DataFrame(), None])
def test_rd2_empty_second_family_keeps_valid_first_through_ric(monkeypatch, tmp_path, empty):
    from copy import deepcopy
    from datetime import datetime, timezone
    from types import SimpleNamespace
    from collectors import base, rate_futures as rf
    from engine import rates_inflation_command as ric
    from lib import config
    adapter, _, _ = _rd2_native_fetch(monkeypatch)
    download = adapter._download
    adapter.cfg['roots']['sofr'] = {'symbol_root': 'SR3', 'exchanges': ['CME'],
                                    'cadence': 'quarterly', 'months': 6}
    requests = []
    def vendor_download(symbols, **kwargs):
        requests.append(symbols[0])
        return download(symbols, kwargs['period'], None) if symbols[0].startswith('ZQ') else empty
    monkeypatch.setitem(sys.modules, 'yfinance', SimpleNamespace(download=vendor_download))
    # Exercise the actual download/retry boundary: an empty vendor response is
    # raised inside _download, not returned by it. Do not mock that behavior away.
    monkeypatch.setattr(adapter, '_download', rf.RateFuturesAdapter._download.__get__(adapter))
    adapter.retries, adapter.backoff = 2, 0
    cfg = deepcopy(config.load())
    cfg['storage']['run_status_file'] = 'run_status.json'
    cfg['storage']['data_dir'] = 'data'
    monkeypatch.setattr(config, 'ROOT', tmp_path)
    monkeypatch.setattr(config, 'load', lambda: cfg)
    monkeypatch.setattr(config, 'data_dir', lambda: tmp_path / 'data')
    monkeypatch.setattr(base, 'datetime', rf.datetime)
    monkeypatch.setattr(ric, 'datetime', SimpleNamespace(
        now=lambda tz: datetime(2026, 10, 2, 10, tzinfo=timezone.utc)))
    result = base.run_adapter(adapter)
    assert result.status == 'ok', result.error
    out = ric.build_board(root=tmp_path / 'data')['policy_path_repricing']
    assert out['families']['zq']['horizons']['m12']['matched_contract_change_bp'] == pytest.approx(15)
    assert out['families']['sofr']['reason'] == 'missing_source'
    assert out['authority'] is False
    assert sum(symbol.startswith('ZQ') for symbol in requests) == 1
    assert sum(symbol.startswith('SR3') for symbol in requests) == adapter.retries


def test_rd2_all_empty_families_still_fail_without_manufacturing_data(monkeypatch):
    adapter, _, _ = _rd2_native_fetch(monkeypatch)
    monkeypatch.setattr(adapter, '_download', lambda symbols, period, yf: pd.DataFrame())
    with pytest.raises(RuntimeError, match='no implied path'):
        adapter.fetch()


def test_rd2_empty_family_repair_does_not_swallow_other_download_errors(monkeypatch):
    adapter, _, _ = _rd2_native_fetch(monkeypatch)
    def fail(symbols, period, yf):
        raise ConnectionError('synthetic transport failure')
    monkeypatch.setattr(adapter, '_download', fail)
    with pytest.raises(ConnectionError, match='synthetic transport failure'):
        adapter.fetch()


def test_rd2_contract_strip_uses_new_york_calendar_date(monkeypatch):
    """UTC midnight must not roll a US rate-futures strip before New York midnight."""
    from datetime import date, datetime, timezone
    from types import SimpleNamespace
    from collectors import rate_futures as rf

    # 2026-10-01 01:00 UTC is still 2026-09-30 21:00 in New York.
    moment = datetime(2026, 10, 1, 1, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(rf, 'datetime', SimpleNamespace(now=lambda tz: moment))
    monkeypatch.setitem(sys.modules, 'yfinance', SimpleNamespace())

    adapter = rf.RateFuturesAdapter()
    adapter.cfg = {
        'horizons_m': [1, 3, 6, 12],
        'max_months': 18,
        'roots': {
            'zq': {
                'symbol_root': 'ZQ',
                'exchanges': ['CBT'],
                'cadence': 'monthly',
                'months': 14,
            }
        },
    }

    observed_asof = []
    real_gen = rf.gen_contracts

    def capture_gen(symbol_root, exchanges, cadence, n, asof):
        observed_asof.append(asof)
        return real_gen(symbol_root, exchanges, cadence, n, asof)

    monkeypatch.setattr(rf, 'gen_contracts', capture_gen)
    monkeypatch.setattr(adapter, '_download',
                        lambda symbols, period, yf: pd.DataFrame())

    with pytest.raises(RuntimeError, match='no implied path'):
        adapter.fetch()

    assert observed_asof == [date(2026, 9, 30)]


@pytest.mark.parametrize(
    'asof,expected',
    [
        ('2026-03-17', (2025, 12)),
        ('2026-03-18', (2026, 3)),
        ('2026-04-01', (2026, 3)),
        ('2026-05-15', (2026, 3)),
        ('2026-06-16', (2026, 3)),
        ('2026-06-17', (2026, 6)),
        ('2026-07-01', (2026, 6)),
        ('2026-08-15', (2026, 6)),
        ('2026-09-15', (2026, 6)),
        ('2026-09-16', (2026, 9)),
    ],
)
def test_rd2_sr3_strip_starts_with_active_reference_quarter(asof, expected):
    from datetime import date
    from collectors import rate_futures as rf
    from engine.rate_futures_repricing import reference_period

    d = date.fromisoformat(asof)
    contracts = rf.gen_contracts('SR3', ['CME'], 'quarterly', 4, d)
    first = (contracts[0]['year'], contracts[0]['month'])
    assert first == expected

    start, end = reference_period('SR3', *first)
    assert date.fromisoformat(start) <= d < date.fromisoformat(end)
    assert [(c['year'], c['month']) for c in contracts[1:]] == [
        ((expected[0] + (expected[1] + step - 1) // 12),
         ((expected[1] + step - 1) % 12) + 1)
        for step in (3, 6, 9)
    ]


def test_rd2_sr3_active_quarter_survives_collector_store_and_ric(monkeypatch, tmp_path):
    from copy import deepcopy
    from datetime import datetime, timezone
    from types import SimpleNamespace
    from collectors import base, rate_futures as rf
    from engine import rates_inflation_command as ric
    from lib import config

    # April is inside the March SR3 reference quarter. The collector must retain
    # the March-named contract instead of starting the strip at June.
    moment = datetime(2026, 4, 2, 13, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(rf, 'datetime', SimpleNamespace(now=lambda tz: moment))
    requested = []
    idx = pd.DatetimeIndex(['2026-03-31', '2026-04-01'])

    def vendor_download(symbols, **kwargs):
        requested[:] = list(symbols)
        entries = {}
        for i, symbol in enumerate(symbols):
            entries[symbol] = pd.DataFrame(
                {'Close': [96.0 - .05 * i, 95.9 - .05 * i]},
                index=idx,
            )
        return pd.concat(entries, axis=1)

    monkeypatch.setitem(sys.modules, 'yfinance', SimpleNamespace(download=vendor_download))
    adapter = rf.RateFuturesAdapter()
    adapter.retries, adapter.backoff = 1, 0
    adapter.cfg = {
        'horizons_m': [1, 3, 6, 12],
        'max_months': 18,
        'roots': {
            'sofr': {
                'symbol_root': 'SR3',
                'exchanges': ['CME'],
                'cadence': 'quarterly',
                'months': 6,
            }
        },
    }

    cfg = deepcopy(config.load())
    cfg['storage']['run_status_file'] = 'run_status.json'
    cfg['storage']['data_dir'] = 'data'
    monkeypatch.setattr(config, 'ROOT', tmp_path)
    monkeypatch.setattr(config, 'load', lambda: cfg)
    monkeypatch.setattr(config, 'data_dir', lambda: tmp_path / 'data')
    monkeypatch.setattr(base, 'datetime', rf.datetime)
    monkeypatch.setattr(
        ric,
        'datetime',
        SimpleNamespace(now=lambda tz: datetime(2026, 4, 2, 14, 0, tzinfo=timezone.utc)),
    )

    result = base.run_adapter(adapter)
    assert result.status == 'ok', result.error
    assert requested[0].startswith('SR3H26.')

    out = ric.build_board(root=tmp_path / 'data')['policy_path_repricing']
    sofr = out['families']['sofr']
    assert sofr['status'] == 'partial'
    assert sofr['horizons']['m1']['status'] == 'unavailable'
    assert sofr['horizons']['m1']['reason'] == 'unbracketed_horizon'
    for horizon in ('m3', 'm6', 'm12'):
        assert sofr['horizons'][horizon]['status'] == 'available'
    assert sofr['historical_availability_qualified'] is False
    assert out['authority'] is False and out['can_trade'] is False
    json.dumps(out, allow_nan=False)

    evidence = pd.read_parquet(tmp_path / 'data' / 'rate_futures' / 'sofr_constituents.parquet')
    last = json.loads(evidence.iloc[-1]['snapshot_json'])['payload']
    assert '2026-03' in last['quotes']
    assert last['quotes']['2026-03']['reference_period'] == [
        '2026-03-18', '2026-06-17'
    ]
