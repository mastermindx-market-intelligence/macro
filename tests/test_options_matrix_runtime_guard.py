"""Runtime contract tests for the scheduled options-matrix launchd lane."""
from pathlib import Path


def test_runner_gates_on_canonical_coherent_session() -> None:
    root = Path(__file__).resolve().parents[1]
    runner = (root / "ops/launchd/run_options_matrix.sh").read_text()

    assert "latest_options_matrix_session" in runner
    assert 'coherent = latest_options_matrix_session("SPY", store=store)' in runner
    assert "if coherent is not None and coherent >= required.isoformat():" in runner

    # Freshness must not drift back to an OI-only date projection.
    assert 'columns=["date"]' not in runner
    assert 'Path(store) / "oi" / "SPY"' not in runner
