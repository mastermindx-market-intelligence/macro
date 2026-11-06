"""MS-W32A-1 — the NY Fed recession odds must print in the unit the producer writes.

`conditions.recession.ny_fed_prob` is FRED RECPROUSM156N in PERCENT
(`engine/conditions.py:698`); the composite leg divides it by 100 to obtain a
0..1 probability at `engine/conditions.py:296`. `templates/macro_signals.html.j2`
multiplied the already-percent value by 100 again, so the committed 0.62 print
rendered as "62%" inside a tile whose own headline reads 7/100 "low".

Fixtures are synthetic dicts carrying exactly the committed values quoted in the
W32A design packet (F1). No `data/`, no network, no builder run.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Undefined

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT / "templates"


def _make_env() -> Environment:
    """Jinja2 env with FileSystemLoader on templates/ and minimal globals."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
        undefined=Undefined,  # silent undefined — mirrors build_site behaviour
    )

    def _td(val, *_args, **_kw):
        return val if val is not None else ""

    def _tr(*args, **kwargs):
        return args[0] if args else ""

    env.globals.update(td=_td, tr=_tr, zip=zip)
    return env


def _render(vm: dict) -> str:
    return _make_env().get_template("macro_signals.html.j2").render(**vm)


def _base_vm() -> dict:
    """Absolute-minimum vm — every optional key None, cycle panel reachable."""
    return {
        "latest": {
            "date": "2026-10-19",
            "growth_score": None,
            "inflation_score": None,
            "business_cycle": {"available": True, "phase": {"label": "Expansion"}},
            "conditions": {},
        },
        "market_state": None,
        "msig_stances": None,
        "fear_greed": None,
        "fear_euphoria": None,
        "vix": None,
        "chart_liquidity": None,
        "chart_credit_breadth": None,
        "chart_vix": None,
        "commodities": [],
        "positioning": [],
        "cross_asset": None,
        "fx_context": None,
    }


# Committed record quoted in the design packet F1 (data/regime/latest.json).
_RECESSION = {
    "score": 7.187487062303684,
    "label": "low",
    "sahm": 0.0,
    "ebp": -0.3919245963723856,
    "ny_fed_prob": 0.62,
    "components": {
        "prob": 0.62,
        "ebp_prob": 9.12016941156304,
        "ebp_level": 14.603174603174605,
    },
}


def _vm(recession: dict) -> dict:
    vm = _base_vm()
    vm["latest"]["conditions"]["recession"] = recession
    return vm


def test_ny_fed_prob_is_printed_in_producer_units():
    """0.62 (percent) prints as `0.62%`, never as the 100x-inflated `62%`."""
    html = _render(_vm(dict(_RECESSION)))
    assert "NY Fed prob: 0.62%" in html
    assert "NY Fed prob: 62%" not in html
    # No bare 62% anywhere in the recession tile: the tile score is 7/100.
    tile_i = html.index(">Recession risk</span>")
    assert re.search(r"(?<![\d.])62%", html[tile_i:tile_i + 1400]) is None


def test_ny_fed_prob_units_match_the_composite_leg():
    """The printed percent equals the artifact value verbatim (kills *100)."""
    html = _render(_vm(dict(_RECESSION)))
    printed = re.search(r"NY Fed prob: ([\d.]+)%", html)
    assert printed is not None, "NY Fed prob disappeared from the tooltip"
    assert float(printed.group(1)) == _RECESSION["ny_fed_prob"]


def test_ny_fed_prob_absent_renders_em_dash():
    """A None print keeps the em-dash fallback and carries no percent sign."""
    rec = dict(_RECESSION)
    rec["ny_fed_prob"] = None
    html = _render(_vm(rec))
    assert "NY Fed prob: —" in html
    assert re.search(r"NY Fed prob:\s*[\d.]", html) is None
    assert "NY Fed prob: None" not in html


def test_zh_arm_uses_the_same_unit():
    """The zh arm of the same help() carries the identical corrected figure."""
    html = _render(_vm(dict(_RECESSION)))
    assert "纽约联储曲线概率: 0.62%" in html
    assert "纽约联储曲线概率: 62%" not in html
