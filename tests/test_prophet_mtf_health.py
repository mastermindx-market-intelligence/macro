"""Producer health for the Prophet checklist: never convert computation failure to empty."""
from unittest.mock import patch

import pandas as pd
import pytest

from engine import mtf_upturn


def _result(state="UPTURN_WATCH"):
    return {
        "state": state, "raw_state": state, "k": 2 if state != "NONE" else 0,
        "legs": {"d_macd": True, "d3_confluence": True, "w_macd": "none", "w2_macd": False},
        "trend": {key: {"pos": False, "bars_since_cross": None} for key in ("d", "d3", "w", "w2")},
        "monthly_phase": "below_water/rising", "htf_coverage": True,
    }


def _compute(tmp_path, symbols, failures=(), skipped=(), state="UPTURN_WATCH"):
    close = pd.Series([100.0, 101.0], index=pd.to_datetime(["2026-10-29", "2026-10-30"]))

    def symbol_result(sym, *_):
        if sym in failures:
            raise ValueError("private diagnostic must not become public UI copy")
        return _result(state)

    with (
        patch.object(mtf_upturn, "_build_universe", return_value={s: ["test"] for s in symbols}),
        patch.object(mtf_upturn, "_load_prior_states", return_value={}),
        patch.object(mtf_upturn, "_load_ledger", return_value=[]),
        patch.object(mtf_upturn, "_load_close", side_effect=lambda sym, _: None if sym in skipped else close),
        patch.object(mtf_upturn, "_compute_symbol", side_effect=symbol_result),
        patch.object(mtf_upturn, "_stamp_ledger", return_value=0) as ledger,
    ):
        output = mtf_upturn.compute(data_root=tmp_path)
    return output, ledger


def test_all_symbol_calculations_failing_are_not_a_successful_empty_snapshot(tmp_path):
    data, ledger = _compute(tmp_path, ["FAIL1", "FAIL2"], failures=("FAIL1", "FAIL2"))
    assert data["schema"] == "mtf_upturn.v1"
    assert data["universe_n"] == 2 and data["evaluated_n"] == 0 and data["failed_n"] == 2
    assert data["error"] == "no_symbols_evaluated"
    assert data["as_of"] == "2026-10-30"
    assert data["cohort"] == {"confirmed": [], "watch": []}
    assert "private diagnostic" not in str(data)
    assert ledger.call_args.args[0] == []


def test_partial_failure_preserves_good_rows_and_exposes_coverage(tmp_path):
    data, ledger = _compute(tmp_path, ["ACME", "FAIL", "SKIP"], failures=("FAIL",), skipped=("SKIP",))
    assert data["universe_n"] == 2 and data["evaluated_n"] == 1 and data["failed_n"] == 1
    assert data["skipped_n"] == 1 and "error" not in data
    assert data["cohort"] == {"confirmed": [], "watch": ["ACME"]}
    assert list(data["tickers"]) == ["ACME"]
    assert data["tickers"]["ACME"]["state"] == "UPTURN_WATCH"
    assert data["tickers"]["ACME"]["k"] == 2
    assert [row["symbol"] for row in ledger.call_args.args[0]] == ["ACME"]


def test_successful_no_signal_snapshot_remains_genuinely_empty(tmp_path):
    data, _ = _compute(tmp_path, ["NO_SETUP"], state="NONE")
    assert data["universe_n"] == data["evaluated_n"] == 1 and data["failed_n"] == 0
    assert "error" not in data
    assert data["cohort"] == {"confirmed": [], "watch": []}
    assert data["tier"] == "display"
    assert all(data["authority"][key] is False for key in ("may_rank", "may_gate", "may_size", "may_escalate"))


@pytest.mark.parametrize("symbols,skipped", [([], ()), (["SKIP"], ("SKIP",))])
def test_no_evaluable_universe_has_explicit_unavailable_health(tmp_path, symbols, skipped):
    data, _ = _compute(tmp_path, symbols, skipped=skipped)
    assert data["universe_n"] == data["evaluated_n"] == data["failed_n"] == 0
    assert data["error"] == "no_symbols_evaluated"
    assert data["skipped_n"] == len(skipped)
