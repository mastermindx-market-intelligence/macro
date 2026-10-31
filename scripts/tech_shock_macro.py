"""One Macro-only mount for the EOD tech shock drill-down.

The established dashboard.html.j2 is a 16k-line shared macro/stocks template.
Keep this additive panel in its own reviewed partial and make the insertion
identical in the nightly and dev-fast renderers. No duplicate regime hero.
"""
from __future__ import annotations

from jinja2 import Environment


def render_macro_with_shock(env: Environment, vm: dict) -> str:
    """Render the existing Macro route and append a progressive-enhancement card.

    The component relocates itself immediately after #regime-radar in the DOM;
    without JavaScript it remains accessible at the bottom of the document.
    A missing <body> end is a contract failure, never a silently omitted feature.
    """
    page = env.get_template("dashboard.html.j2").render(**vm, mode="macro")
    if page.count("</body>") != 1:
        raise ValueError("Macro body anchor missing or ambiguous")
    snap = vm.get("tech_shock")
    if not isinstance(snap, dict):
        # Older cached dev VMs must not produce fake values or a broken build.
        from engine.tech_volatility_shock import _missing
        snap = _missing("Raw EOD source has not been assembled for this render.")
    panel = env.get_template("_tech_volatility_shock.html.j2").render(tech_shock=snap)
    return page.replace("</body>", panel + "\n</body>")
