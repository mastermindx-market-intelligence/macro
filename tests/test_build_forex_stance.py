"""Hero stance must follow dollar_dir the way the transmission engine does.

engine/forex_transmission.py classifies headwind_for / tailwind_for as the
effect of a STRENGTHENING dollar (ripple table column: "If USD rises").
The engine's own prose (lines 169-173) therefore selects:

    hp = headwind if usd_dir == "strengthening" else tailwind
    word = "headwind" if strengthening else "tailwind"

scripts/build_forex._stance() must mirror that selection so a soft dollar is
never described as "leaning on" assets the table marks headwind-only-if-USD-rises.
"""
from __future__ import annotations

from pathlib import Path


_HW = ["Gold", "EM equities"]
_TW = ["US equities"]
_ARGS = ([], False, False, "risk-on")  # active, dollar_day, triple_red, risk_word

_TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "forex.html.j2"


def _stance(dollar_dir, *, headwind_for=_HW, tailwind_for=_TW):
    from scripts.build_forex import _stance as impl
    return impl(dollar_dir, *_ARGS, headwind_for=headwind_for, tailwind_for=tailwind_for)


def test_stance_sentence_flips_when_dollar_dir_flips():
    """Same ripple lists, flipped dollar_dir → verb and selected list flip, both locales."""
    firm = _stance("up")
    soft = _stance("down")

    assert "leaning on" in firm["sentence_en"], firm["sentence_en"]
    assert "gold" in firm["sentence_en"].lower(), firm["sentence_en"]
    assert "压制" in firm["sentence_zh"], firm["sentence_zh"]
    assert "黄金" in firm["sentence_zh"], firm["sentence_zh"]

    assert "giving" in soft["sentence_en"] and "lift" in soft["sentence_en"], soft["sentence_en"]
    assert "US stocks" in soft["sentence_en"], soft["sentence_en"]
    assert "leaning on" not in soft["sentence_en"], soft["sentence_en"]
    assert "gold" not in soft["sentence_en"].lower(), soft["sentence_en"]
    assert "提振" in soft["sentence_zh"], soft["sentence_zh"]
    assert "美股" in soft["sentence_zh"], soft["sentence_zh"]
    assert "压制" not in soft["sentence_zh"], soft["sentence_zh"]

    assert firm["sentence_en"] != soft["sentence_en"]
    assert firm["sentence_zh"] != soft["sentence_zh"]

    # Aliases the caller actually passes ("strengthening"/"weakening") and the
    # engine's usd_dir tokens must agree with up/down.
    assert _stance("strengthening")["sentence_en"] == firm["sentence_en"]
    assert _stance("weakening")["sentence_en"] == soft["sentence_en"]
    assert _stance("strengthening")["sentence_zh"] == firm["sentence_zh"]
    assert _stance("weakening")["sentence_zh"] == soft["sentence_zh"]


def test_soft_dollar_does_not_lean_on_if_usd_rises_headwinds():
    """Typical tape: inverse assets only. Soft dollar must not 'lean on' them."""
    soft = _stance("down", headwind_for=["Gold", "Oil (WTI)"], tailwind_for=[])
    assert "leaning on" not in soft["sentence_en"], soft["sentence_en"]
    assert "压制" not in soft["sentence_zh"], soft["sentence_zh"]


def test_dollar_trend_scorecard_labels_12_month_horizon():
    """Hero 63d dollar_dir vs 12m overlay must not look like a contradiction."""
    src = _TEMPLATE.read_text(encoding="utf-8")
    assert "Currently long — 12-month trend up" in src
    assert "当前做多 — 12个月趋势向上" in src
    assert "Currently flat — 12-month trend down" in src
    assert "当前空仓 — 12个月趋势向下" in src
    assert "Currently long (trend up)" not in src
    assert "当前做多（趋势向上）" not in src
    assert "Currently flat (trend down)" not in src
    assert "当前空仓（趋势向下）" not in src
