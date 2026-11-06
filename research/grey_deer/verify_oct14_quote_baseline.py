"""Reproduce two quote-clock test failures with the original market-state owner.

Read-only with respect to tracked files. Only this test process's module namespace
is loaded from the frozen Git base; the candidate workspace is never reverted.
This is a baseline diagnostic, not a way to suppress or reclassify failing CI.
"""
from pathlib import Path
import subprocess
import sys

BASE = "9e8f22ec1fc03c046bc1f38b3f397d5f6c9965ef"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main() -> int:
    import engine.market_state as market_state
    import pytest

    original = subprocess.check_output(
        ["git", "-C", str(ROOT), "show", f"{BASE}:engine/market_state.py"],
        text=True,
    )
    print(f"BASELINE owner: engine/market_state.py at {BASE}", flush=True)
    exec(compile(original, f"{BASE}:engine/market_state.py", "exec"), market_state.__dict__)
    tests = ROOT / "tests" / "test_risk_state_live_session_floor.py"
    return pytest.main([
        str(tests) + "::TestSplicedFramesQuoteClocks::test_a_synthetic_flagged_quote_is_excluded_from_the_clock_receipt",
        str(tests) + "::TestSplicedFramesQuoteClocks::test_all_synthetic_quotes_yield_none_source_event_time",
        "-q", "--tb=short", "--basetemp=/tmp/macro-risk-response-20261014-c1-baseline",
    ])


if __name__ == "__main__":
    raise SystemExit(main())
