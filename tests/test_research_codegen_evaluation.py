"""Trusted synthetic source fixtures only; never call the numerical incumbent."""
from dataclasses import replace
from datetime import date, timedelta
import importlib.util
from pathlib import Path
import sys

import pytest

# Load the exact trusted source artifact, without importing any market pipeline.
_PATH = Path(__file__).resolve().parents[1] / "engine/research_codegen/evaluation.py"
_SPEC = importlib.util.spec_from_file_location("_trusted_evaluation_fixture", _PATH)
ev = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = ev
_SPEC.loader.exec_module(ev)


@pytest.fixture
def case(monkeypatch):
    # Invented calendar, not a claim that these dates are exchange cash sessions.
    start = date(2010, 1, 4) - timedelta(days=260)
    days = tuple((start + timedelta(days=i)).isoformat() for i in range(340))
    paths = tuple(ev.SourcePath(node, days, (0.0,) * len(days)) for node in ev.COHORT)
    formation = ev.Formation(0, days[260], ("XLB", "XLE", "XLF"))
    scores = tuple(ev.FeatureScore(0, node, value)
                   for node, value in (("XLB", 1.0), ("XLE", 1.0), ("XLF", 2.0)))
    calls = []

    def stub(source_paths, entries):
        calls.append((source_paths, entries))
        return [dict(node=node, trigger_date=trigger, exec_date=days[days.index(trigger) + 1],
                     MFE=0.1, MAE={"XLB": -0.03, "XLE": -0.02, "XLF": -0.01}.get(node, -0.01),
                     ret_exit=0.04, regime="risk_on", hold_sessions=21)
                for node, triggers in entries.items() for trigger in triggers]

    monkeypatch.setattr(ev, "_measure_incumbent_rows", stub)
    return dict(paths=paths, formations=(formation,), scores=scores,
                expected_session_dates=days), calls, stub


def test_top_half_ties_shared_rows_and_single_measurement(case):
    arguments, calls, _ = case
    result = ev.evaluate_feature_ordering(**arguments)
    assert result.status == "DIAGNOSTIC_ONLY"
    assert result.scientific_acceptance == "UNQUALIFIED"
    assert result.authority == "display_only" and result.refusal_count == 0
    pair = result.pairs[0]
    assert pair.selected_nodes == ("XLF", "XLB")
    assert pair.foregone_nodes == ("XLE",)
    assert pair.baseline_loss == pytest.approx(0.02)
    assert pair.candidate_loss == pytest.approx(0.02)
    assert len(calls) == 1
    assert all(any(selected is baseline for baseline in pair.baseline_entries)
               for selected in pair.candidate_entries)


def test_single_and_empty_opportunities_keep_original_positions(case):
    arguments, calls, _ = case
    days = arguments["expected_session_dates"]
    arguments["formations"] = (ev.Formation(0, days[260], ("XLB",)),
                               ev.Formation(2, days[312], ()))
    arguments["scores"] = (ev.FeatureScore(0, "XLB", 0.0),)
    result = ev.evaluate_feature_ordering(**arguments)
    assert [(row.calendar_index, row.opportunities) for row in result.coverage] == [(0, 1), (2, 0)]
    assert len(result.pairs) == 1 and result.pairs[0].difference == 0.0
    assert len(calls) == 1
    arguments["formations"] = (ev.Formation(0, days[260], ()),)
    arguments["scores"] = ()
    assert ev.evaluate_feature_ordering(**arguments).pairs == ()
    assert len(calls) == 1


@pytest.mark.parametrize("problem", ["missing", "extra", "duplicate", "nan", "infinity", "bool"])
def test_score_failures_refuse_whole_call_before_measurement(case, problem):
    arguments, calls, _ = case
    scores = arguments["scores"]
    if problem == "missing":
        scores = scores[:-1]
    elif problem == "extra":
        scores += (ev.FeatureScore(0, "XLY", 1.0),)
    elif problem == "duplicate":
        scores += (scores[0],)
    else:
        value = {"nan": float("nan"), "infinity": float("inf"), "bool": True}[problem]
        scores = (replace(scores[0], value=value),) + scores[1:]
    arguments["scores"] = scores
    result = ev.evaluate_feature_ordering(**arguments)
    assert result.status == "REFUSED" and result.refusal_count >= 1
    assert result.pairs == () and calls == []


@pytest.mark.parametrize("problem", ["nan", "minus_one", "length", "calendar", "cohort", "warmup", "horizon", "schedule"])
def test_source_and_schedule_refusals_precede_legacy_fillna(case, problem):
    arguments, calls, _ = case
    paths = arguments["paths"]
    days = arguments["expected_session_dates"]
    if problem in ("nan", "minus_one"):
        value = float("nan") if problem == "nan" else -1.0
        paths = (replace(paths[0], returns=(value,) + paths[0].returns[1:]),) + paths[1:]
    elif problem == "length":
        paths = (replace(paths[0], returns=paths[0].returns[:-1]),) + paths[1:]
    elif problem == "calendar":
        paths = (replace(paths[0], session_dates=days[:-1]),) + paths[1:]
    elif problem == "cohort":
        paths = (replace(paths[0], node="XLC"),) + paths[1:]
    elif problem == "warmup":
        arguments["expected_session_dates"] = days[2:]
        paths = tuple(replace(path, session_dates=days[2:], returns=path.returns[2:]) for path in paths)
    elif problem == "horizon":
        arguments["formations"] = (ev.Formation(3, days[338], ("XLB",)),)
    else:
        arguments["formations"] += (ev.Formation(1, days[287], ()),)
    arguments["paths"] = paths
    result = ev.evaluate_feature_ordering(**arguments)
    assert result.status == "REFUSED" and result.pairs == () and calls == []


@pytest.mark.parametrize("problem", ["missing", "duplicate", "extra", "exec", "mae", "hold", "overflow"])
def test_native_silent_skips_and_invalid_rows_refuse_entire_result(case, monkeypatch, problem):
    arguments, calls, stub = case

    def invalid(paths, entries):
        rows = stub(paths, entries)
        if problem == "missing":
            return rows[:-1]
        if problem == "duplicate":
            return rows + [rows[0]]
        if problem == "extra":
            return rows + [dict(rows[0], node="XLY")]
        if problem == "overflow":
            return [dict(row, MAE=-1e308) for row in rows]
        change = {"exec": {"exec_date": "1999-01-01"}, "mae": {"MAE": float("nan")},
                  "hold": {"hold_sessions": 25}}[problem]
        return [dict(rows[0], **change)] + rows[1:]

    monkeypatch.setattr(ev, "_measure_incumbent_rows", invalid)
    result = ev.evaluate_feature_ordering(**arguments)
    assert result.status == "REFUSED" and result.pairs == () and len(calls) == 1


def test_immutable_values_and_reject_hooks(case):
    arguments, calls, _ = case

    class Hook:
        def __eq__(self, other):
            raise AssertionError("untrusted equality hook executed")

    arguments["paths"] = (replace(arguments["paths"][0], session_dates=(Hook(),)),) + arguments["paths"][1:]
    assert ev.evaluate_feature_ordering(**arguments).status == "REFUSED"
    assert calls == []
    arguments["paths"] = list(arguments["paths"])
    assert ev.evaluate_feature_ordering(**arguments).refusal_reasons == ("IMMUTABLE_INPUT_REQUIRED",)


@pytest.mark.parametrize("problem", ["wrong_single_date", "wrong_single_index", "uniform_date_shift", "uniform_index_shift", "absent_anchor"])
def test_fixed_anchor_binding_does_not_depend_on_previous_formation(case, problem):
    arguments, calls, _ = case
    days = arguments["expected_session_dates"]
    if problem == "wrong_single_date":
        arguments["formations"] = (ev.Formation(0, days[261], ("XLB",)),)
    elif problem == "wrong_single_index":
        arguments["formations"] = (ev.Formation(1, days[260], ("XLB",)),)
    elif problem == "uniform_date_shift":
        arguments["formations"] = (ev.Formation(0, days[261], ("XLB",)),
                                   ev.Formation(1, days[287], ("XLB",)))
    elif problem == "uniform_index_shift":
        arguments["formations"] = (ev.Formation(1, days[260], ("XLB",)),
                                   ev.Formation(2, days[286], ("XLB",)))
    else:
        no_anchor = tuple(day for day in days if day != "2010-01-04")
        arguments["expected_session_dates"] = no_anchor
        arguments["paths"] = tuple(replace(path, session_dates=no_anchor, returns=(0.0,) * len(no_anchor))
                                   for path in arguments["paths"])
    result = ev.evaluate_feature_ordering(**arguments)
    reason = "FORMATION_ANCHOR_ABSENT" if problem == "absent_anchor" else "FORMATION_ANCHOR_MISMATCH"
    assert result.refusal_reasons == (reason,)
    assert result.pairs == () and calls == []


def test_single_later_formation_preserves_predeclared_gap(case):
    arguments, calls, _ = case
    days = arguments["expected_session_dates"]
    arguments["formations"] = (ev.Formation(2, days[312], ("XLB",)),)
    arguments["scores"] = (ev.FeatureScore(2, "XLB", 1.0),)
    result = ev.evaluate_feature_ordering(**arguments)
    assert result.status == "DIAGNOSTIC_ONLY"
    assert result.pairs[0].calendar_index == 2
    assert len(calls) == 1


@pytest.mark.parametrize("change", [{"MAE": -1.0}, {"MAE": 0.2, "MFE": 0.1},
                                    {"ret_exit": -1.0}, {"ret_exit": -0.5}, {"ret_exit": 0.5}])
def test_impossible_native_metric_rows_refuse_diagnostics(case, monkeypatch, change):
    arguments, calls, stub = case

    def impossible(paths, entries):
        rows = stub(paths, entries)
        return [dict(rows[0], **change)] + rows[1:]

    monkeypatch.setattr(ev, "_measure_incumbent_rows", impossible)
    result = ev.evaluate_feature_ordering(**arguments)
    assert result.refusal_reasons == ("INCONSISTENT_NATIVE_MEASUREMENT",)
    assert result.pairs == () and len(calls) == 1


def test_real_fixed_wrapper_invented_returns_include_post_exit_excursion():
    """One real incumbent call: invented values only, no candidate or data loader."""
    start = date(2010, 1, 4) - timedelta(days=260)
    days = tuple((start + timedelta(days=i)).isoformat() for i in range(340))
    trigger_position = days.index("2010-01-04")
    entry_position = trigger_position + 1
    paths = []
    for node in ev.COHORT:
        returns = [0.0] * len(days)
        if node == "XLB":
            returns[entry_position + 21] = 0.10
            returns[entry_position + 25] = -0.20
        elif node == "XLE":
            returns[entry_position + 1] = -0.10
        paths.append(ev.SourcePath(node, days, tuple(returns)))
    result = ev.evaluate_feature_ordering(
        paths=tuple(paths),
        formations=(ev.Formation(0, days[trigger_position], ("XLB", "XLE", "XLF")),),
        scores=(ev.FeatureScore(0, "XLB", 1.0), ev.FeatureScore(0, "XLE", 0.0),
                ev.FeatureScore(0, "XLF", 2.0)),
        expected_session_dates=days,
    )
    assert result.status == "DIAGNOSTIC_ONLY" and result.refusal_reasons == ()
    assert result.scientific_acceptance == "UNQUALIFIED" and result.authority == "display_only"
    assert len(result.pairs) == 1
    pair = result.pairs[0]
    assert pair.selected_nodes == ("XLF", "XLB")
    assert pair.baseline_loss == pytest.approx((0.12 + 0.10) / 3)
    assert pair.candidate_loss == pytest.approx(0.12 / 2)
    assert pair.difference == pytest.approx(0.013333333333333333)
    entries = {row.node: row for row in pair.baseline_entries}
    assert entries["XLB"].mae == pytest.approx(-0.12)
    assert entries["XLB"].mfe == pytest.approx(0.10)
    assert entries["XLB"].ret_exit == pytest.approx(0.10)
    assert entries["XLB"].hold_sessions == 21
    assert entries["XLE"].mae == pytest.approx(-0.10)
    assert entries["XLF"].mae == 0.0
    assert all(row is entries[row.node] for row in pair.candidate_entries)
