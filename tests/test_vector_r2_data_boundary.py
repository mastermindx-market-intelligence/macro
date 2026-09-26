from __future__ import annotations

import pandas as pd

from scripts import build_vector


def _sig() -> pd.DataFrame:
    idx = pd.to_datetime(["2026-09-23", "2026-09-24", "2026-09-25", "2026-09-26"])
    return pd.DataFrame(
        {
            "close": [80000.0, 81000.0, 82000.0, 83000.0],
            "risk_index": [20.0, None, 25.0, 15.0],
            "alloc_optimal": [1.0, 0.0, None, 0.5],
        },
        index=idx,
    )


def test_r2_payload_preserves_zero_and_unavailable_allocation() -> None:
    payload = build_vector._risk_strategy_payload(_sig())

    assert payload["schema"] == "mastermind.vector_risk_strategy.v2"
    assert payload["valid"] is False
    assert payload["alloc"]["optimal"] == [1.0, 0.0, None, 0.5]
    assert payload["risk"] == [20, None, 25, 15]
    assert payload["missing"]["allocation_dates"]["optimal"] == ["2026-09-25"]
    assert payload["issues"][0]["code"] == "ALLOCATION_UNAVAILABLE"


def test_r2_payload_does_not_create_trade_markers_across_missing_allocation() -> None:
    payload = build_vector._risk_strategy_payload(_sig())

    assert payload["markers"]["optimal"] == [
        {"t": "2026-09-24", "dir": "sell", "to": 0.0},
    ]


def test_r2_payload_exposes_noninvented_source_metadata() -> None:
    payload = build_vector._risk_strategy_payload(_sig())
    meta = payload["meta"]

    assert meta["observed_at"] == "2026-09-26"
    assert meta["fields"]["price"]["source_id"] == "signals.close"
    assert meta["fields"]["risk"]["source_id"] == "signals.risk_index"
    assert meta["fields"]["allocation"]["source_id"] == "signals.alloc_optimal"
    assert meta["fields"]["price"]["available_at"] is None
    assert meta["fields"]["risk"]["available_at"] is None
    assert meta["fields"]["allocation"]["available_at"] is None


def test_r2_valid_zero_allocation_remains_actionable() -> None:
    sig = _sig().copy()
    sig["alloc_optimal"] = [1.0, 0.0, 0.0, 0.5]

    payload = build_vector._risk_strategy_payload(sig)

    assert payload["valid"] is True
    assert payload["alloc"]["optimal"][1:3] == [0.0, 0.0]
    assert payload["missing"]["allocation_dates"]["optimal"] == []


def test_r2_template_gates_replay_and_exposes_source_contract() -> None:
    from pathlib import Path

    source = (Path(__file__).resolve().parent.parent / "templates" / "vector.html.j2").read_text()

    assert 'data-vector-replay-state="{{ \'valid\' if chart_contract.valid else \'unavailable\' }}"' in source
    assert "{% if chart_contract.valid %}" in source
    assert "Missing observations are never rendered as 0% cash." in source
    assert "{{ t('Data & source','数据与来源') }}" in source
    assert "chart_contract.meta.fields.allocation.source_id" in source
    assert "Availability clock: not asserted." in source
