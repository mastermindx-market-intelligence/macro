"""S2 INFO-LEAK predicate (E10, SL §7 class 3) on synthetic price frames.

Pins: an adjustment-factor step (q_t = close_t/close_price_t) above tolerance
inside the scan window retires TUNE (ledger row + manifest record); an HK
series with no adjustment-factor pair is VINTAGE_UNVERIFIABLE and never
retired; TRAIN is never retired; an empty split is not applicable.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "event_response"))

from engine.trial_ledger import TrialLedger  # noqa: E402
from run_s2 import maybe_log_retirement  # noqa: E402
from s2_outcomes import OutcomeEngine  # noqa: E402
from s2_seal import INFO_LEAK_CLASS, ledger_family  # noqa: E402


def _frame(rows: list[tuple[str, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["Date", "close", "close_price"])


class _SyntheticLoader:
    """Serves the two price stores from synthetic frames (never data/)."""

    def __init__(self, baba: pd.DataFrame, spy: pd.DataFrame) -> None:
        self._frames = {"data/yahoo/BABA.parquet": baba,
                        "data/yahoo/SPY.parquet": spy}

    def read_parquet(self, path, columns=None):
        df = self._frames[path]
        return df if columns is None else df[[c for c in columns
                                              if c in df.columns]]

    def read_yaml(self, path):  # pragma: no cover - unused here
        raise AssertionError("no yaml reads in the price phase")

    def read_json(self, path):  # pragma: no cover
        raise AssertionError("no json reads in the price phase")


def _engine(baba_q_jump: bool) -> OutcomeEngine:
    dates = pd.date_range("2026-06-01", periods=30, freq="D")
    base_close = [100.0 + 0.1 * i for i in range(30)]
    base_raw = list(base_close)
    if baba_q_jump:
        # a dividend ex-date on the 10th bar: the adjustment factor steps from
        # 1.0 to 1.01, so q_t/q_{t-1} - 1 = 0.01 > 1e-6 on that date
        base_raw[9] = base_close[9] / 1.01
    baba = _frame([(d.date().isoformat(), c, r)
                   for d, c, r in zip(dates, base_close, base_raw)])
    spy_dates = pd.date_range("2026-06-01", periods=30, freq="D")
    spy = _frame([(d.date().isoformat(), 500.0 + 0.05 * i, 500.0 + 0.05 * i)
                  for i, d in enumerate(spy_dates)])
    return OutcomeEngine(_SyntheticLoader(baba, spy))


def test_q_step_inside_window_fires_and_logs_retirement(tmp_path: Path) -> None:
    engine = _engine(baba_q_jump=True)
    scan = engine.info_leak_scan(dt.date(2026, 6, 5))
    assert scan["leak"] is True
    assert scan["series"]["BABA"]["steps_above_tolerance"] >= 1
    ledger = TrialLedger(path=tmp_path / "trial_ledger.jsonl")
    state = {"membership": {"P04": {"sha_table": {str(h): {"TUNE": f"sha{h}"}
                                                   for h in (5, 21, 63)}}}}
    rec = maybe_log_retirement(ledger, "P04", engine, state,
                               dt.date(2026, 6, 5), "2026-10-11T21:59:47+00:00")
    assert rec["contamination_class"] == INFO_LEAK_CLASS
    assert rec["successor"] == "P04 v2 — not drafted; owner = seat/S0"
    rows = [json.loads(l) for l in
            (tmp_path / "trial_ledger.jsonl").read_text().splitlines() if l.strip()]
    assert len(rows) == 1
    row = rows[0]
    assert row["family"] == ledger_family("P04")
    assert row["config"]["event"] == "holdout_retired"
    assert row["config"]["split"] == "TUNE"
    assert row["config"]["contamination_class"] == INFO_LEAK_CLASS
    assert row["source"] == "sni_s0_holdout_retirement"


def test_no_step_inside_window_does_not_retire(tmp_path: Path) -> None:
    engine = _engine(baba_q_jump=False)
    scan = engine.info_leak_scan(dt.date(2026, 6, 5))
    assert scan["leak"] is False
    ledger = TrialLedger(path=tmp_path / "trial_ledger.jsonl")
    state = {"membership": {"P04": {"sha_table": {str(h): {"TUNE": f"sha{h}"}
                                                   for h in (5, 21, 63)}}}}
    rec = maybe_log_retirement(ledger, "P04", engine, state,
                               dt.date(2026, 6, 5), "2026-10-11T21:59:47+00:00")
    assert "contamination_class" not in rec
    assert "not retired" in rec["state"]
    assert not (tmp_path / "trial_ledger.jsonl").exists()


def test_empty_tune_split_is_not_applicable(tmp_path: Path) -> None:
    engine = _engine(baba_q_jump=True)
    ledger = TrialLedger(path=tmp_path / "trial_ledger.jsonl")
    rec = maybe_log_retirement(ledger, "P05", engine, {}, None,
                               "2026-10-11T21:59:47+00:00")
    assert rec["state"] == "EMPTY — retirement not applicable"
    assert not (tmp_path / "trial_ledger.jsonl").exists()


def test_hk_series_vintage_is_disclosed_never_retired() -> None:
    from s2_seal import HK_VINTAGE_LINE
    assert "VINTAGE_UNVERIFIABLE" in HK_VINTAGE_LINE
    assert "not retired" in HK_VINTAGE_LINE


def test_train_is_never_retired() -> None:
    from s2_seal import TRAIN_NEVER_RETIRED
    assert "never retired" in TRAIN_NEVER_RETIRED
