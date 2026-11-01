"""Seasonality page: every style's call for the graded month, and the years behind it.

engine/factor_seasonality.py grades each style for the current month (verdict,
window_used, streak) and keeps its ten most recent same-month returns (recent),
but the page printed only the one headline the copy step picked. The records
below are copied from the committed site/factordata/factor_seasonality.json
(as_of 2026-08, month 10). The mosaic stats are synthetic and only guard that
the existing grid still renders.
"""
from __future__ import annotations

import copy
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from engine.i18n import td, tr

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"


def _rec(key, en, zh, verdict, y10, y30, streak, recent):
    stat = lambda m, md, h, n: {"mean": m, "median": md, "hit": h, "n": n}  # noqa: E731
    return {"key": key, "plain_en": en, "plain_zh": zh, "verdict": verdict,
            "window_used": "trailing_10y", "y10": stat(*y10), "y30": stat(*y30),
            "streak": {"sign": streak[0], "len": streak[1]},
            "recent": [{"year": 2025 - i, "ret": r} for i, r in enumerate(recent)]}


NOW_FACTORS = [
    _rec("value", "Cheap stocks (Value)", "低估值（价值）", "tailwind",
         (1.54, 0.57, 70, 10), (0.18, -0.1, 50, 30), (-1, 1),
         [-3.18, 0.91, 0.22, 7.97, -0.53, 4.25, -1.92, 3.43, 0.13, 4.1]),
    _rec("profitability", "Strong earners (Profitability)", "高盈利（盈利质量）", "tailwind",
         (0.31, 0.93, 70, 10), (0.42, 0.59, 53, 30), (-1, 2),
         [-5.25, -1.49, 2.42, 3.28, 1.71, -0.77, 0.43, 0.94, 0.92, 0.96]),
    _rec("investment", "Careful spenders (Investment)", "稳健投资（投资）", "neutral",
         (0.02, -0.65, 40, 10), (0.29, 0.24, 60, 30), (-1, 1),
         [-4.07, 1.02, -0.72, 6.42, -1.54, -0.57, -1.03, 3.56, -3.14, 0.28]),
    _rec("momentum", "Recent winners (Momentum)", "近期赢家（动量）", "tailwind",
         (1.2, 1.16, 80, 10), (0.33, 0.1, 57, 30), (1, 5),
         [0.16, 2.98, 1.69, 3.94, 3.31, -3.1, 0.13, -2.0, 4.24, 0.62]),
    _rec("size", "Small companies (Size)", "小盘股（规模）", "headwind",
         (-1.4, -1.44, 30, 10), (-0.95, -1.2, 37, 30), (-1, 3),
         [-0.57, -0.95, -3.87, 0.01, -2.26, 4.34, 0.27, -4.67, -1.93, -4.41]),
]


def _seas(now=True):
    cell = {"mean": 0.5, "median": 0.4, "hit": 60, "n": 10}
    months = {m: dict(cell) for m in range(1, 13)}
    factors = [{"key": k, "label_en": k.title(), "label_zh": k, "start": "1926-07",
                "context_only": False, "full": dict(months), "trailing_30y": dict(months),
                "trailing_10y": dict(months)}
               for k in ("value", "profitability", "investment", "momentum", "size", "market")]
    seas = {"as_of": "2026-08", "factors": factors, "disclosure_en": "d", "disclosure_zh": "d"}
    if now:
        seas["now"] = {"month": 10, "month_label_en": "October", "month_label_zh": "10月",
                       "headline_en": "h", "headline_zh": "h", "stance_en": "s",
                       "stance_zh": "s", "chip_en": "", "chip_zh": "",
                       "factors": copy.deepcopy(NOW_FACTORS)}
    return seas


def _render(seas):
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=True)
    env.globals.update(td=td, tr=tr, zip=zip)
    return env.get_template("seasonality.html.j2").render(seas=seas, built="2026-10-19")


def _cards(html):
    return html.split('class="fcard"')[1:]


def _card(html, plain_en):
    hits = [c for c in _cards(html) if plain_en in c.split("</h3>")[0]]
    assert len(hits) == 1, plain_en
    return hits[0].split("</details>")[0]


def _en(fragment):
    text = re.sub(r'<span class="l-zh">.*?</span>', "", fragment, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text))


def test_w21g_one_card_per_graded_style():
    html = _render(_seas())
    assert html.count('class="fcard"') == 5
    assert len(re.findall(r'<td class="mos[" ]', html)) == 216
    assert 'class="mos muted' not in html


def test_w21g_size_headwind_card_prints_its_record():
    card = _en(_card(_render(_seas()), "Small companies (Size)"))
    assert "Seasonal headwind" in card
    assert "Graded on the last 10 Octobers: average -1.40%, up in 30% of them" in card
    assert "Down 3 Octobers in a row" in card
    zh = _card(_render(_seas()), "Small companies (Size)")
    assert "季节性偏弱" in zh and "连续 3 年10月下跌" in zh


def test_w21g_verdict_badges_follow_the_producer():
    html = _render(_seas())
    badges = {k: _en(_card(html, f["plain_en"]).split("</h3>")[0])
              for k, f in ((f["key"], f) for f in NOW_FACTORS)}
    assert "Seasonal tailwind" in badges["momentum"]
    assert "Seasonal tailwind" in badges["value"]
    assert "No clear seasonal lean" in badges["investment"]
    assert "Seasonal headwind" not in badges["momentum"]


def test_w21g_single_year_streak_reads_last_month():
    card = _en(_card(_render(_seas()), "Cheap stocks (Value)"))
    assert "Last October: down" in card
    assert "in a row" not in card
    mom = _en(_card(_render(_seas()), "Recent winners (Momentum)"))
    assert "Up 5 Octobers in a row" in mom
    assert "average +1.20%, up in 80% of them" in mom


def test_w21g_thirty_year_fallback_uses_y30():
    seas = _seas()
    size = next(f for f in seas["now"]["factors"] if f["key"] == "size")
    size["y10"]["n"] = 5
    size["window_used"] = "trailing_30y"
    card = _en(_card(_render(seas), "Small companies (Size)"))
    assert "Graded on the last 30 Octobers: average -0.95%, up in 37% of them" in card
    assert "-1.40%, up in 30%" not in card


def test_w21g_momentum_years_are_all_listed_signed():
    card = _card(_render(_seas()), "Recent winners (Momentum)")
    assert "The last 10 Octobers, year by year" in _en(card)
    assert card.count("<li>") == 10
    for item in ("2025 +0.16%", "2020 -3.10%", "2018 -2.00%", "2016 +0.62%"):
        assert f"<li>{item}</li>" in card


def test_w21g_empty_recent_has_no_year_list():
    seas = _seas()
    for f in seas["now"]["factors"]:
        f["recent"] = []
    html = _render(seas)
    assert html.count('class="fcard"') == 5
    assert "<details>" not in html


def test_w21g_absent_now_renders_no_cards():
    for seas in (_seas(now=False), dict(_seas(), now=None)):
        html = _render(seas)
        assert 'class="fcard"' not in html
        assert 'class="now-strip"' not in html
        assert "style by style" not in html
        assert html.count('class="mos"') == 216
