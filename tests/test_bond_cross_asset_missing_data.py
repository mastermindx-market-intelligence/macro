"""Synthetic regression tests for the display-only Bonds cross-asset map."""
from pathlib import Path
import ast

import numpy as np
import pandas as pd
import pytest
from jinja2 import Environment

from engine import bond_cross_asset as BX


def _series(n=150, seed=234):
    rng = np.random.default_rng(seed)
    index = pd.date_range("2020-01-03", periods=n, freq="W-FRI")
    driver = pd.Series(2 + np.cumsum(rng.normal(0, .02, n)), index=index)
    price = pd.Series(100 * np.cumprod(1 + rng.normal(.002, .01, n)), index=index)
    return price, driver


def _reference(price, driver):
    """Independent adjacent-endpoint formula, with no implicit filling."""
    a = price.resample("W-FRI").last()
    d = driver.resample("W-FRI").last()
    pairs = pd.concat([a / a.shift(1) - 1, d - d.shift(1)], axis=1, keys=["r", "d"])
    pairs = pairs[np.isfinite(pairs).all(axis=1)]
    if len(pairs) < 104 or pairs.d.var() == 0:
        return None
    beta = pairs.r.cov(pairs.d) / pairs.d.var()
    corr = pairs.r.corr(pairs.d)
    if not np.isfinite(beta) or not np.isfinite(corr):
        return None
    return {"beta": beta, "corr": corr, "n": len(pairs)}


def _assert_reference(price, driver):
    actual, expected = BX._beta(price, driver), _reference(price, driver)
    if expected is None:
        assert actual is None
    else:
        assert actual is not None
        assert actual["n"] == expected["n"]
        assert actual["beta"] == pytest.approx(expected["beta"], rel=1e-12, abs=1e-12)
        assert actual["corr"] == pytest.approx(expected["corr"], rel=1e-12, abs=1e-12)


@pytest.mark.parametrize("n,gaps", [(106, [50]), (105, [50]), (150, [50]), (150, [50, 51]), (150, [20, 50, 80])])
@pytest.mark.parametrize("side", ["asset", "driver"])
def test_missing_weeks_do_not_create_comparison_pairs(n, gaps, side):
    price, driver = _series(n)
    (price if side == "asset" else driver).iloc[gaps] = np.nan
    _assert_reference(price, driver)


@pytest.mark.parametrize("n", [1, 103, 104, 105, 150])
def test_complete_history_retains_existing_minimum(n):
    _assert_reference(*_series(n))


@pytest.mark.parametrize("value", [0., np.inf, -np.inf])
def test_nonfinite_returns_are_excluded(value):
    price, driver = _series()
    price.iloc[50] = value
    _assert_reference(price, driver)


@pytest.mark.parametrize("side", ["asset", "driver"])
def test_constant_series_does_not_emit_undefined_statistics(side):
    price, driver = _series()
    (price if side == "asset" else driver)[:] = 100.
    assert BX._beta(price, driver) is None


@pytest.fixture
def render_panel(monkeypatch):
    """Real builder view-model and template fragment; not a full-page build."""
    monkeypatch.setattr(BX.store, "read", lambda *a, **kw: None)
    root = Path(__file__).resolve().parents[1]
    module = ast.parse((root / "scripts/build_bonds.py").read_text())
    node = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "_xasset_vm")
    colors = {k: k for k in ("blue", "amber", "green", "red", "muted")}
    scope = {"C": colors, "_XA_VERDICT": {
        "tailwind": ("green", "Tailwind", "顺风"),
        "headwind": ("red", "Headwind", "逆风"),
        "neutral": ("muted", "Neutral", "中性"),
    }}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "scripts/build_bonds.py", "exec"), scope)
    source = (root / "templates/bonds.html.j2").read_text()
    fragment = source.split("<!-- ===================== BONDS → EVERYTHING (measured transmission) ===================== -->")[1]
    fragment = fragment.split("<!-- ===================== TREASURY SUPPLY ABSORPTION")[0]
    template = Environment().from_string(fragment)

    def render(snapshot, lang):
        return template.render(xasset_vm=scope["_xasset_vm"](snapshot), C=colors, charts={},
                               t=lambda en, zh: en if lang == "en" else zh,
                               kpi=lambda *args: "")
    return render


@pytest.mark.parametrize("lang", ["en", "zh"])
@pytest.mark.parametrize("healthy_sibling", [False, True])
def test_constant_asset_cannot_break_panel(render_panel, lang, healthy_sibling):
    price, driver = _series()
    frame = pd.DataFrame({"SPY": price * 0 + 100, "hy_oas": driver})
    if healthy_sibling:
        frame["XLU"] = price
        frame["us10y"] = driver
    snapshot = BX.snapshot(frame)
    html = render_panel(snapshot, lang)
    assert [row["key"] for row in snapshot["assets"]] == (["utes"] if healthy_sibling else [])
    if healthy_sibling:
        assert ("Utilities" if lang == "en" else "公用事业") in html
    else:
        assert html.strip() == ""


@pytest.mark.parametrize("lang", ["en", "zh"])
@pytest.mark.parametrize("n", [1, 2, 63, 64])
def test_short_real_yield_history_retains_healthy_panel(render_panel, lang, n):
    price, driver = _series()
    frame = pd.DataFrame({"SPY": price, "hy_oas": driver})
    frame["us10y_real"] = np.nan
    frame.loc[frame.index[-n:], "us10y_real"] = np.linspace(1., 2., n)
    snapshot = BX.snapshot(frame)
    html = render_panel(snapshot, lang)
    assert [row["key"] for row in snapshot["assets"]] == ["spx"]
    assert "None" not in html
    assert ("S&P 500" if lang == "en" else "标普500") in html
    if n < 64:
        assert ("3m change unavailable" if lang == "en" else "3个月变化暂无数据") in html
    else:
        assert ("+100bp/3m" if lang == "en" else "+100基点/3月") in html
    assert snapshot["interpretation_scope"] == "contemporaneous_association_not_lead_or_causal_effect"


def test_complete_summary_retains_exact_bilingual_copy():
    snapshot = {"assets": [{"verdict": "tailwind"}, {"verdict": "headwind"}],
                "drivers_now": {"real_10y": 2., "real_chg_bp": 10., "slope": .5, "hy_oas": 3.}}
    assert BX._verdict(snapshot) == (
        "Real-10y 2.0% (+10bp/3m), curve 0.5pp, HY OAS 3.0%. 1 markets with a bond-associated tailwind, 1 with a bond-associated headwind right now.",
        "10年实际利率 2.0%（+10基点/3月），曲线 0.5pp，高收益利差 3.0%。当前 1 个市场呈与债券指标相关的顺风，1 个呈相关逆风。",
    )


def test_missing_asset_or_driver_is_unavailable():
    price, driver = _series()
    assert BX._beta(None, driver) is None
    assert BX._beta(price, None) is None
    assert BX.snapshot(pd.DataFrame()) is None
