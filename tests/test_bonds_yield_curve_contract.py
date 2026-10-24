"""R19: Bonds reuses the canonical yield-curve owner in bond_health.json."""

from __future__ import annotations

import pandas as pd

from scripts import build_bonds


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {"us2y": [4.2, 4.3], "us10y": [4.5, 4.6]},
        index=pd.to_datetime(["2026-09-24", "2026-09-25"]),
    )


def test_attach_yield_curve_contract_reuses_owner_output_verbatim(monkeypatch) -> None:
    f = _frame()
    owner = {
        "asof": "2026-09-25",
        "shape": {"level": 4.44},
        "slopes": {"2s10s": 0.3},
        "momentum": {"real10y_speed_bp": 65},
        "regime": {"key": "bear_flattener"},
        "recession": {"risk": "low", "n_flags": 0},
        "forwards": {"5y5y": 4.7},
        "signals": {"market_tendency": {"drawdown_risk": "elevated"}},
        "scored_status": {"en": "Display-only."},
        "caveats": [{"en": "Never scored."}],
    }
    seen = []

    def fake_snapshot(arg):
        seen.append(arg)
        return owner

    monkeypatch.setattr("engine.yield_curve.snapshot", fake_snapshot)
    snap = {"health_score": 84, "pillars": {"curve": {"move_taxonomy": "bear_flattener"}}}

    result = build_bonds._attach_yield_curve_contract(snap, f)

    assert seen == [f]
    assert result is owner
    assert snap["yield_curve"] is owner
    assert snap["health_score"] == 84
    assert snap["pillars"]["curve"]["move_taxonomy"] == "bear_flattener"


def test_attach_yield_curve_contract_keeps_absence_absent(monkeypatch) -> None:
    f = _frame()
    monkeypatch.setattr("engine.yield_curve.snapshot", lambda arg: None)
    snap = {"health_score": 84}

    result = build_bonds._attach_yield_curve_contract(snap, f)

    assert result is None
    assert snap == {"health_score": 84}


def test_attach_yield_curve_contract_is_fail_open_and_does_not_write_placeholder(monkeypatch) -> None:
    f = _frame()

    def boom(_arg):
        raise RuntimeError("synthetic owner failure")

    monkeypatch.setattr("engine.yield_curve.snapshot", boom)
    snap = {"health_score": 84, "yield_curve_status": "preexisting"}

    result = build_bonds._attach_yield_curve_contract(snap, f)

    assert result is None
    assert snap == {"health_score": 84, "yield_curve_status": "preexisting"}


def test_contract_adapter_has_no_independent_curve_math() -> None:
    """Guard against the adapter growing into a second yield-curve engine."""
    import inspect
    import ast

    source = inspect.getsource(build_bonds._attach_yield_curve_contract)
    # Inspect executable statements; the pd.DataFrame annotation is not curve math.
    node = ast.parse(source).body[0]
    body_source = "\n".join(ast.get_source_segment(source, statement) or "" for statement in node.body)
    assert "from engine import yield_curve" in source
    assert "_yield_curve.snapshot(" in source
    for forbidden in (
        ".rolling(",
        ".pct_change(",
        ".diff(",
        "np.",
        "pd.",
        "float(",
        "round(",
    ):
        assert forbidden not in body_source



def test_curve_chart_keeps_shared_tenor_geometry_with_missing_values() -> None:
    import re
    columns = ["us3m", "us6m", "us1y", "us2y", "us3y", "us5y", "us7y", "us10y", "us30y"]
    frame = pd.DataFrame({column: [float(i)] * 252 for i, column in enumerate(columns)})
    frame.loc[251, "us6m"] = float("nan")
    frame.loc[188, "us30y"] = float("nan")
    frame.loc[0, "us3m"] = float("nan")
    out = build_bonds.chart_curve_now(frame)
    paths = re.findall(r'<path class="ilx-path ilx-m" d="([^"]+)"', out)
    xs = [[float(x) for x in re.findall(r"(?:M|L)([-0-9.]+) ", path)] for path in paths]
    assert xs == [
        [0, 140, 210, 280, 350, 420, 490, 560],
        [0, 70, 140, 210, 280, 350, 420, 490],
        [70, 140, 210, 280, 350, 420, 490, 560],
    ]
    assert '<span class="ilx-d ilx-d0">3m</span>' in out
    assert '<span class="ilx-d ilx-d1">30y</span>' in out


def test_curve_chart_keeps_its_separate_two_snapshot_admission() -> None:
    columns = ["us3m", "us6m", "us1y", "us2y", "us3y", "us5y", "us7y", "us10y", "us30y"]
    one_snapshot = pd.DataFrame({column: [float(i)] for i, column in enumerate(columns)})
    assert build_bonds.chart_curve_now(one_snapshot) == ""
