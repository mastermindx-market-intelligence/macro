"""Contract tests for the merge-on-green *arming* predicate, not merge eligibility.

The controller must still require genuine clean checks before any actual merge.
These tests isolate enrollment semantics with a fake classifier; they do not
stand in for real check-run, hold, trust or throughput integration coverage.
"""
import ast
from pathlib import Path
from typing import Any

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "merge_on_green.py"


def load_predicate(verdict):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    node = next(
        n for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "can_arm_merge_on_green"
    )
    calls = []

    def decide(runs):
        calls.append(runs)
        return verdict, []

    namespace = {"Any": Any, "decide_verdict": decide}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace["can_arm_merge_on_green"], calls


@pytest.mark.parametrize("verdict", ["clean", "pending"])
def test_enrollment_does_not_wait_for_pending_checks(verdict):
    predicate, calls = load_predicate(verdict)
    runs = [{"name": "sentinel"}]
    assert predicate(runs, base_ref="main") is True
    assert calls == [runs]


@pytest.mark.parametrize("verdict", ["blocked", "red", "failed", "missing", "unknown", "", None])
def test_other_verdicts_never_arm(verdict):
    predicate, calls = load_predicate(verdict)
    assert predicate([], base_ref="main") is False
    assert calls == [[]]


@pytest.mark.parametrize("base", ["master", "develop", "feature/x"])
@pytest.mark.parametrize("verdict", ["clean", "pending"])
def test_non_main_bases_are_out_of_scope(base, verdict):
    predicate, calls = load_predicate(verdict)
    assert predicate([], base_ref=base) is False
    assert calls == []


def test_default_main_uses_shared_classifier():
    predicate, calls = load_predicate("clean")
    assert predicate([]) is True
    assert len(calls) == 1
