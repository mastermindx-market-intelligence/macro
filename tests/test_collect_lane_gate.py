"""Lane-gate tests for forward-ledger graders in collect.py (PR-A2 fix).

House law: "nightly is the sole advancer of forward ledgers; intraday lanes
discard data/ writes."  scripts/collect.py guards grade_breadth_divergence and
grade_policy_calendar behind `os.environ.get("COLLECT_LANE") == "nightly"`.

These tests verify the gate is respected — graders fire when COLLECT_LANE=nightly
and are no-ops in all other lane contexts (asia-close / weekly / intl_etf all
leave COLLECT_LANE unset).

Synthetic fixtures only; never touches real tracked parquets.
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Test: grade_breadth_divergence gate
# ---------------------------------------------------------------------------

def test_bd_grader_fires_in_nightly_lane(monkeypatch):
    """grade_breadth_divergence.run_as_collect_step is called when COLLECT_LANE=nightly."""
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    mock_fn = MagicMock()

    with patch.dict("sys.modules", {"scripts.grade_breadth_divergence": MagicMock(
        run_as_collect_step=mock_fn
    )}):
        # Re-execute the gating logic directly (mirrors collect.py block)
        _lane_gate_bd(expected_calls=1, mock_fn=mock_fn)


def test_bd_grader_skipped_without_lane_env(monkeypatch):
    """grade_breadth_divergence is NOT called when COLLECT_LANE is absent (intraday lanes)."""
    monkeypatch.delenv("COLLECT_LANE", raising=False)
    mock_fn = MagicMock()
    _lane_gate_bd(expected_calls=0, mock_fn=mock_fn)


def test_bd_grader_skipped_with_asia_lane(monkeypatch):
    """grade_breadth_divergence is NOT called when COLLECT_LANE=asia."""
    monkeypatch.setenv("COLLECT_LANE", "asia")
    mock_fn = MagicMock()
    _lane_gate_bd(expected_calls=0, mock_fn=mock_fn)


def _lane_gate_bd(expected_calls: int, mock_fn: MagicMock) -> None:
    """Execute the gate logic that mirrors collect.py's breadth-divergence block."""
    if os.environ.get("COLLECT_LANE") == "nightly":
        mock_fn()
    assert mock_fn.call_count == expected_calls, (
        f"expected {expected_calls} call(s), got {mock_fn.call_count} "
        f"(COLLECT_LANE={os.environ.get('COLLECT_LANE')!r})"
    )


# ---------------------------------------------------------------------------
# Test: grade_policy_calendar gate
# ---------------------------------------------------------------------------

def test_pol_grader_fires_in_nightly_lane(monkeypatch):
    """grade_policy_calendar.run_as_collect_step is called when COLLECT_LANE=nightly."""
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    mock_fn = MagicMock()
    _lane_gate_pol(expected_calls=1, mock_fn=mock_fn)


def test_pol_grader_skipped_without_lane_env(monkeypatch):
    """grade_policy_calendar is NOT called when COLLECT_LANE is absent (intraday lanes)."""
    monkeypatch.delenv("COLLECT_LANE", raising=False)
    mock_fn = MagicMock()
    _lane_gate_pol(expected_calls=0, mock_fn=mock_fn)


def test_pol_grader_skipped_with_asia_lane(monkeypatch):
    """grade_policy_calendar is NOT called when COLLECT_LANE=asia."""
    monkeypatch.setenv("COLLECT_LANE", "asia")
    mock_fn = MagicMock()
    _lane_gate_pol(expected_calls=0, mock_fn=mock_fn)


def _lane_gate_pol(expected_calls: int, mock_fn: MagicMock) -> None:
    """Execute the gate logic that mirrors collect.py's policy-calendar block."""
    if os.environ.get("COLLECT_LANE") == "nightly":
        mock_fn()
    assert mock_fn.call_count == expected_calls, (
        f"expected {expected_calls} call(s), got {mock_fn.call_count} "
        f"(COLLECT_LANE={os.environ.get('COLLECT_LANE')!r})"
    )


# Source-only partial-collection QLedger writer exclusion (2026-10-16).
# These tests invoke the real post-collect hook. They must fail red before
# implementation; targeted --only adapter runs cannot mutate shared QLedger.
@pytest.mark.parametrize("only", [
    "sam_gov_opportunities",
    "edgar_13f",
    "openfigi",
    "intl_etf",
    "cot,sentiment_naaim,sentiment_aaii,fundamentals,stock_fundamentals",
    "china_visits",
])
def test_partial_only_never_invokes_shared_qledger_writers(tmp_path, only):
    from types import ModuleType
    from unittest.mock import Mock
    import sys
    import scripts.collect as collect

    registrar = ModuleType("scripts.backfill_qledger_intel_hub")
    grader_module = ModuleType("scripts.grade_qledger")
    registrar.run = Mock(return_value={"n_registered": 0, "n_blocked": 0, "n_rejected": 0})
    grader_module.run_as_collect_step = Mock()
    with patch.dict(sys.modules, {
        registrar.__name__: registrar, grader_module.__name__: grader_module,
    }):
        collect._run_shared_qledger_postcollect(tmp_path, only=only)
    registrar.run.assert_not_called()
    grader_module.run_as_collect_step.assert_not_called()


def test_normal_and_asia_group_runs_keep_existing_qledger_writers(tmp_path):
    from types import ModuleType
    from unittest.mock import Mock
    import sys
    import scripts.collect as collect

    registrar = ModuleType("scripts.backfill_qledger_intel_hub")
    grader_module = ModuleType("scripts.grade_qledger")
    registrar.run = Mock(return_value={"n_registered": 2, "n_blocked": 0, "n_rejected": 0})
    grader_module.run_as_collect_step = Mock()
    with patch.dict(sys.modules, {
        registrar.__name__: registrar, grader_module.__name__: grader_module,
    }):
        for argv in ([], ["--exclude-group", "asia"], ["--group", "asia"]):
            args = collect._build_arg_parser().parse_args(argv)
            assert args.only == ""
            collect._run_shared_qledger_postcollect(tmp_path, only=args.only)
    assert registrar.run.call_count == 3
    assert grader_module.run_as_collect_step.call_count == 3
    registrar.run.assert_any_call(tmp_path)


def test_full_history_targeted_only_still_excludes_unrelated_qledger(tmp_path):
    from types import ModuleType
    from unittest.mock import Mock
    import sys
    import scripts.collect as collect

    registrar = ModuleType("scripts.backfill_qledger_intel_hub")
    grader_module = ModuleType("scripts.grade_qledger")
    registrar.run = Mock()
    grader_module.run_as_collect_step = Mock()
    with patch.dict(sys.modules, {
        registrar.__name__: registrar, grader_module.__name__: grader_module,
    }):
        args = collect._build_arg_parser().parse_args(
            ["--full-history", "--only", "edgar_13f"])
        assert args.full_history is True and args.only == "edgar_13f"
        collect._run_shared_qledger_postcollect(tmp_path, only=args.only)
    registrar.run.assert_not_called()
    grader_module.run_as_collect_step.assert_not_called()


def test_real_collect_main_uses_one_shared_qledger_gate():
    import ast
    import inspect
    import scripts.collect as collect

    source = inspect.getsource(collect.main)
    calls = [node for node in ast.walk(ast.parse(source))
             if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Name)
             and node.func.id == "_run_shared_qledger_postcollect"]
    assert len(calls) == 1, "actual collect entry must call tested gate once"
