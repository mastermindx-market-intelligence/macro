"""Primary Macro route mount: one compact EOD panel, no stocks-mode regression."""
from __future__ import annotations

from pathlib import Path

import pytest
from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader

from engine.tech_volatility_shock import _missing
from scripts.tech_shock_macro import render_macro_with_shock

ROOT = Path(__file__).resolve().parents[1]


def _env(dashboard: str) -> Environment:
    return Environment(loader=ChoiceLoader([
        DictLoader({"dashboard.html.j2": dashboard}),
        FileSystemLoader(ROOT / "templates"),
    ]))


def test_mounted_once_after_dashboard_and_before_body_close():
    html = render_macro_with_shock(
        _env('<html><body><main><section id="regime-radar">REGIME</section></main></body></html>'),
        {"tech_shock": _missing("Raw data not restored.")},
    )
    assert html.count('id="tech-volatility-shock"') == 1
    assert html.count('id="regime-radar"') == 1
    assert html.index("REGIME") < html.index('id="tech-volatility-shock"')
    assert html.index('id="tech-volatility-shock"') < html.index("</body>")
    assert "Raw data not restored." in html
    assert "QQQ vs SPY -1.70" not in html
    assert "tech volatility shock" in html.lower()
    assert "Massive/Polygon" in html


def test_old_vm_has_honest_unavailable_panel():
    html = render_macro_with_shock(_env("<html><body>base</body></html>"), {})
    assert "Data unavailable" in html
    assert "Raw EOD source has not been assembled" in html


def test_ambiguous_body_anchor_fails_not_silently_drops_feature():
    with pytest.raises(ValueError, match="body anchor"):
        render_macro_with_shock(_env("<html><main>no body end</main></html>"), {})
    with pytest.raises(ValueError, match="body anchor"):
        render_macro_with_shock(_env("<body></body></body>"), {})
