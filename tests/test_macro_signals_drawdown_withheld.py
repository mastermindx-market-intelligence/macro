"""MS-W32A-2 — the drawdown tile must say the odds were WITHHELD, in the producer's words.

When `conditions.drawdown_risk` runs on fewer inputs than it was measured on,
`engine/conditions.py:874` sets `dd10_prob_pct` to None and `:890-899` writes a
bilingual `degraded_note_en` / `degraded_note_zh` explaining why. The page printed
only `P(dd≥10%/63d): —` — a silence that reads as "no risk to report", the exact
defect `templates/dashboard.html.j2:16112-16123` already fixed for the same field.

The note strings below are the producer's own, quoted verbatim from the committed
`data/regime/latest.json` record in the W32A design packet (F2). No `data/`, no
network, no builder run.
"""
from __future__ import annotations

import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Undefined

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT / "templates"

# Producer strings, verbatim from data/regime/latest.json (design packet F2).
_NOTE_EN = (
    "Running on 3 of 4 inputs — no current print for NFCI. The measured per-band "
    "pullback odds were calibrated on the full set, so they are withheld rather "
    "than restated for a narrower gauge."
)
_NOTE_ZH = (
    "当前仅有 4 项输入中的 3 项——NFCI 暂无最新数据。每档回撤概率是在完整输入下测得的，"
    "因此暂不显示，而非改用较窄的口径重述。"
)


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


# Committed record quoted in the design packet F2 (data/regime/latest.json).
_PARTIAL_DD = {
    "score": 21,
    "dd10_prob_pct": None,
    "base_rate_pct": 19,
    "partial": True,
    "basis_missing": ["NFCI"],
    "basis_resolved": ["recession risk", "EBP", "HY OAS"],
    "n_legs": 3,
    "n_legs_expected": 4,
    "dd10_prob_informative": False,
    "degraded_note_en": _NOTE_EN,
    "degraded_note_zh": _NOTE_ZH,
    "stat_passport": {
        "basis": "partial",
        "span": "1993-01-29–2026-06-30",
        "definition": "max peak-to-trough SPY decline over the next 63 trading days",
    },
}


def _vm(drawdown_risk: dict) -> dict:
    vm = _base_vm()
    vm["latest"]["conditions"]["drawdown_risk"] = drawdown_risk
    return vm


def _tile(html: str, label_en: str) -> str:
    """The sig-tile block whose l-en sig-label carries `label_en`."""
    i = html.index(">%s</span>" % label_en)
    start = html.rindex('<div class="sig-tile', 0, i)
    end = html.find('<div class="sig-tile', i)
    if end == -1:
        end = html.find('<div class="panel', i)
    return html[start:end if end != -1 else len(html)]


def test_partial_basis_prints_the_producer_note():
    """Both producer strings render, plus the 3 / 4 leg count, in that tile."""
    html = _render(_vm(dict(_PARTIAL_DD)))
    assert _NOTE_EN in html
    assert _NOTE_ZH in html
    assert 'data-dr-withheld' in html
    tile = _tile(html, "Drawdown risk")
    assert "3 / 4" in tile, "the leg count must sit inside the drawdown tile"
    assert _NOTE_EN in tile and _NOTE_ZH in tile


def test_informative_odds_print_the_probability_not_the_note():
    """A full-basis payload prints the probability and no withheld note."""
    dd = dict(_PARTIAL_DD)
    dd.update({"dd10_prob_pct": 10, "dd10_prob_informative": True, "partial": False})
    dd["stat_passport"] = {"basis": "ok"}
    html = _render(_vm(dd))
    assert "P(dd≥10%/63d): 10%" in html
    assert "data-dr-withheld" not in html
    assert _NOTE_EN not in html


def test_legacy_payload_without_the_flags_stays_dark():
    """A pre-flag payload renders and prints no note (unguarded access would raise)."""
    html = _render(_vm({"score": 21, "dd10_prob_pct": None, "base_rate_pct": 19}))
    assert "Base rate: 19%" in html
    assert "data-dr-withheld" not in html
    assert _NOTE_EN not in html and _NOTE_ZH not in html


def test_stat_passport_partial_alone_triggers_the_note():
    """`stat_passport.basis == 'partial'` alone is enough — the OR arm matters."""
    dd = dict(_PARTIAL_DD)
    del dd["partial"]
    html = _render(_vm(dd))
    assert "data-dr-withheld" in html
    assert _NOTE_EN in html and _NOTE_ZH in html
