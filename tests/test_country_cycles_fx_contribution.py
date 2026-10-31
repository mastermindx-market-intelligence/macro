"""CC-3 — currency contribution strip on country_cycles.html (SPEC CC-3).

The 3-month + 1-year local-currency move against the USD, server-rendered from the
builder's model (`fx.leg_return_63d` / `leg_return_252d`, always ccy-per-USD — see
engine/country_fx.fx_ccy_per_usd). Synthetic fixtures only; the template is rendered
through an Environment mirroring scripts/build_country_cycles.py:133-141.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jinja2 import Environment, FileSystemLoader  # noqa: E402

from scripts.build_country_cycles import _fx_contribution  # noqa: E402


def _env():
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=False)
    try:
        from engine import i18n
        env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    except Exception:  # noqa: BLE001 — mirror the builder's degrade path
        env.globals.update(td=lambda en: en, tr=lambda en: en, t=lambda en, zh="": en)
    return env


def _render(fc):
    return _env().get_template("country_cycles.html.j2").render(fx_contribution=fc)


def _section(html):
    i = html.index('id="cc-fx"')
    return html[i:html.index("</section>", i)]


def _norm(seg):
    return " ".join(seg.split())


_SPAN = re.compile(r'<span class="l-(en|zh)">(.*?)</span>', re.S)


def _assert_twins_differ(section):
    pairs = _SPAN.findall(section)
    en = [_norm(t) for k, t in pairs if k == "en"]
    zh = [_norm(t) for k, t in pairs if k == "zh"]
    assert en and len(en) == len(zh)
    for a, b in zip(en, zh):
        assert a != b, (a, b)


def _fx_rec(rid="ewu", pair="GBPUSD", r63=1.1, r252=-1.4, quote="ccy_per_usd"):
    return {"id": rid, "name": "United Kingdom", "name_zh": "英国",
            "fx": {"pair": pair, "quote": quote,
                   "leg_return_63d": r63, "leg_return_252d": r252}}


def _model(*recs):
    return {"sectors": list(recs), "baskets": []}


def test_strip_shows_63d_and_252d_for_the_committed_ewu_leg():
    # committed ewu: pair GBPUSD, quote ccy_per_usd, 63d 1.1, 252d -1.4
    data = _model(_fx_rec())
    fc = _fx_contribution(data)
    assert fc["n_rows"] == 1
    row = fc["rows"][0]
    assert row["id"] == "ewu" and row["ccy"] == "GBP"
    assert row["r63"] == 1.1 and row["r252"] == -1.4
    assert "pair" not in row and "GBPUSD" not in repr(fc)
    sec = _section(_render(fc))
    assert "+1.1%" in sec and "-1.4%" in sec and "GBP" in sec
    assert "per USD" in _norm(sec)
    assert "GBPUSD" not in sec
    assert data["sectors"][0]["fx"]["pair"] == "GBPUSD"   # model untouched


def test_negative_63d_keeps_its_sign():
    # committed ewj: USDJPY, 63d -3.5, 252d 2.5 — the code is JPY, not USD
    fc = _fx_contribution(_model(_fx_rec("ewj", "USDJPY", -3.5, 2.5)))
    assert fc["rows"][0]["ccy"] == "JPY"
    sec = _norm(_section(_render(fc)))
    assert "-3.5%" in sec and "+2.5%" in sec and "JPY" in sec


def test_bloc_note_only_fx_renders_nothing():
    # committed efa: fx is note-only, no pair — nothing renders
    bloc = {"id": "efa", "name": "Emerging Asia", "name_zh": "新兴亚洲",
            "fx": {"note": "multi-currency bloc — FX decomposition not defined",
                   "note_zh": "多货币区域 — 未定义汇率拆分"}}
    assert _fx_contribution(_model(bloc)) == {}
    assert 'id="cc-fx"' not in _render(_fx_contribution(_model(bloc)))
    mixed = _fx_contribution(_model(_fx_rec(), bloc))
    assert mixed["n_rows"] == 1 and mixed["rows"][0]["id"] == "ewu"
    ghost = {"id": "ewx", "name": "Ghost", "name_zh": "幽灵",
             "fx": {"quote": "ccy_per_usd", "leg_return_63d": 1.0,
                    "leg_return_252d": 1.0}}                     # valid quote, no pair
    assert _fx_contribution(_model(ghost)) == {}


def test_null_63d_renders_a_dash_not_zero():
    fc = _fx_contribution(_model(_fx_rec("ewd", "USDSEK", None, 4.5)))
    assert fc["rows"][0]["r63"] is None and fc["rows"][0]["r252"] == 4.5
    sec = _norm(_section(_render(fc)))
    assert "—" in sec and "+4.5%" in sec and "+0.0%" not in sec


def test_other_quote_orientation_is_not_rendered():
    fc = _fx_contribution(_model(_fx_rec(quote="usd_per_ccy")))
    assert fc == {}
    assert 'id="cc-fx"' not in _render(fc)


def test_zero_and_negative_zero_print_plus_zero():
    # committed ewh 63d is 0.0; a -0.0 leg must normalize, never print "-0.0%"
    fc = _fx_contribution(_model(_fx_rec("ewh", "USDHKD", 0.0, 0.8),
                                 _fx_rec("ewk", "USDCHF", -0.0, 1.5)))
    assert fc["n_rows"] == 2
    assert all(r["r63"] == 0.0 and str(r["r63"]) != "-0.0" for r in fc["rows"])
    sec = _norm(_section(_render(fc)))
    assert "+0.0%" in sec and "-0.0%" not in sec


def test_orientation_note_and_zh_twins():
    fc = _fx_contribution(_model(_fx_rec()))
    sec = _section(_render(fc))
    norm = _norm(sec)
    assert ("A rise means more local currency per dollar: the currency weakened"
            " against USD." in norm)
    assert "数值上升表示每美元可兑换更多本币，即本币兑美元走弱。" in norm
    _assert_twins_differ(sec)
