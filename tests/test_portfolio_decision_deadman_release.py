from __future__ import annotations

from scripts import portfolio_decision_deadman as deadman


def test_exact_fix_commit_is_accepted_without_repository_ancestry_lookup(monkeypatch) -> None:
    def unexpected(*args, **kwargs):
        raise AssertionError("exact deployed commit must not require merge-base history")

    monkeypatch.setattr(deadman.subprocess, "run", unexpected)
    assert deadman._release_contains_fix(deadman.FIX_COMMIT) is True
