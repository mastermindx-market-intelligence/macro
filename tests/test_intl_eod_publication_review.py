"""Discriminating fail-closed countercases for lib.intl_eod_publication.

Retained Grok R1 cases with an explicit parent correction: the optional EOD
adapter withholds malformed input, but the existing strict overview API raises.
They do not write parquet success fixtures (this runtime has no pyarrow).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engine import intl_inputs
from engine.intl_workspace_overview import build_workspace_overviews
from lib.intl_eod_publication import build_eod_inputs

EVALUATED = "2026-10-09T20:30:00+00:00"
GRANT = {
    "status": "confirmed",
    "scope": "intl-index-fx-eod-user-facing-v1",
    "decision_ref": "chairman:2026-10-09:user-facing-redistribution-confirmed",
}
GENERATION = "im-workspace-generation:df4a2d6b-aed5-4d0c-a211-68f3a4627eb4"
_BASIS = "yfinance:auto_adjust=true:observed-close"


def _frame():
    dates = pd.bdate_range(end="2026-10-07", periods=280)
    cols = {}
    slot = 0
    for market in intl_inputs.countries().values():
        for symbol in (market["index"], market["fx"]):
            if symbol in cols:
                continue
            cols[symbol] = pd.Series(
                [float(100 + slot * 4 + 0.125 * i) for i in range(len(dates))],
                index=dates,
            )
            slot += 1
    return pd.DataFrame(cols).sort_index()


def _status(root: Path) -> None:
    status = {"sources": {"intl_prices": {
        "source": "intl_prices", "status": "ok",
        "checked_at": "2026-10-09T15:00:00+00:00",
        "last_date": "2026-10-07",
    }}}
    (root / "run_status.json").write_text(json.dumps(status), encoding="utf-8")


def _call(root: Path, frame, *, rights=GRANT, evaluated_at=EVALUATED):
    return build_eod_inputs(
        frame, data_root=root, evaluated_at=evaluated_at, rights=rights)


def _bases():
    ids = []
    for market in intl_inputs.countries().values():
        for series_id in (market["index"], market["fx"]):
            if series_id not in ids:
                ids.append(series_id)
    return {series_id: _BASIS for series_id in ids}


def _empty_inputs():
    return {
        "adjustment_bases": _bases(),
        "source_evidence": [],
        "disclosure_decisions": [],
        "policy_id": "intl-observed-endpoints-completed-session-v1",
    }


def _inf_tip(frame):
    out = frame.copy()
    out.iloc[-1, 0] = float("inf")
    return out


def _neg_inf_tip(frame):
    out = frame.copy()
    out.iloc[-1, 0] = float("-inf")
    return out


def _bool_column(frame):
    out = frame.copy()
    out[out.columns[0]] = True
    return out


def _object_true(frame):
    out = frame.copy()
    out[out.columns[0]] = np.array([True] * len(out), dtype=object)
    return out


def _string_cell(frame):
    out = frame.copy()
    out[out.columns[0]] = out.iloc[:, 0].astype(object)
    out.iloc[0, 0] = "100.0"
    return out


def _duplicate_columns(frame):
    return pd.concat([frame, frame.iloc[:, :1]], axis=1)


def test_missing_parquet_and_nan_tip_withhold_without_throwing(tmp_path):
    """Negative cases that already fail closed; keep them green."""
    _status(tmp_path)
    frame = _frame()
    assert _call(tmp_path, frame) is None
    nan_tip = frame.copy()
    nan_tip.iloc[-1, 0] = float("nan")
    assert _call(tmp_path, nan_tip) is None
    assert _call(tmp_path, frame.iloc[::-1]) is None
    assert _call(tmp_path, frame, rights={
        "status": "confirmed",
        "scope": GRANT["scope"],
        "decision_ref": "  ",
    }) is None


@pytest.mark.parametrize("label,mutate", [
    ("inf_tip", _inf_tip),
    ("neg_inf_tip", _neg_inf_tip),
    ("bool_column", _bool_column),
    ("object_true", _object_true),
    ("string_cell", _string_cell),
    ("duplicate_columns", _duplicate_columns),
])
def test_malformed_closes_are_withheld_without_throwing(tmp_path, label, mutate):
    _status(tmp_path)
    assert _call(tmp_path, mutate(_frame())) is None, label


def test_unreadable_parquet_is_withheld_without_throwing(tmp_path):
    """One unreadable saved file must not abort the remaining series."""
    _status(tmp_path)
    path = tmp_path / "intl" / "_N225.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"not-a-parquet-file")
    assert _call(tmp_path, _frame()) is None


@pytest.mark.parametrize("mutate", [_inf_tip, _bool_column, _duplicate_columns])
def test_overview_supplied_malformed_closes_withhold_without_throwing(mutate):
    # Parent adjudication: the pre-existing strict source API intentionally
    # raises on malformed snapshots. Only the optional EOD adapter normalizes
    # those errors to a withheld result. Do not weaken the shared validator.
    with pytest.raises(ValueError):
        build_workspace_overviews(
            mutate(_frame()), production_inputs=_empty_inputs(),
            workspace_generation=GENERATION,
        )
