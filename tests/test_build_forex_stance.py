"""Hero stance follows the forex ripple-table contract, both dollar directions.

templates/forex.html.j2:473/:494/:495 — column "If USD rises":
  headwind_for → "Leaning on it" / 压制中
  tailwind_for → "Giving it a lift" / 提振中
Correlation is linear and symmetric, so a falling dollar inverts the verbs:
  USD firm/up  : lean on headwind_for, lift tailwind_for
  USD soft/down: lift headwind_for, lean on tailwind_for
Quiet only when direction is mixed/flat or both lists are empty.
"""
from __future__ import annotations

import re
from pathlib import Path


_ARGS = ([], False, False, "risk-on")  # active, dollar_day, triple_red, risk_word

_TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "forex.html.j2"


def _stance(dollar_dir, *, headwind_for, tailwind_for):
    from scripts.build_forex import _stance as impl
    return impl(dollar_dir, *_ARGS, headwind_for=headwind_for, tailwind_for=tailwind_for)


def test_stance_cross_mapping_all_four_cells():
    """direction × list: verb follows the ripple-table inversion, both locales."""
    cases = [
        # dir, hw, tw → lift?, asset_en, asset_zh
        ("up", ["Gold"], [], False, "gold", "黄金"),
        ("up", [], ["US equities"], True, "US stocks", "美股"),
        ("down", ["Gold"], [], True, "gold", "黄金"),
        ("down", [], ["US equities"], False, "US stocks", "美股"),
    ]
    for dollar_dir, hw, tw, want_lift, asset_en, asset_zh in cases:
        got = _stance(dollar_dir, headwind_for=hw, tailwind_for=tw)
        en, zh = got["sentence_en"], got["sentence_zh"]
        label = f"dir={dollar_dir!r} hw={hw} tw={tw} → {en!r} / {zh!r}"
        if want_lift:
            assert "giving" in en and "lift" in en, label
            assert "leaning on" not in en, label
            assert "提振" in zh and "压制" not in zh, label
        else:
            assert "leaning on" in en, label
            assert "giving" not in en and "lift" not in en, label
            assert "压制" in zh and "提振" not in zh, label
        assert asset_en in en, label
        assert asset_zh in zh, label
        assert "quiet" not in en.lower(), label
        assert "平静" not in zh, label

    # Aliases the caller actually passes ("strengthening"/"weakening").
    assert (
        _stance("strengthening", headwind_for=["Gold"], tailwind_for=[])["sentence_en"]
        == _stance("up", headwind_for=["Gold"], tailwind_for=[])["sentence_en"]
    )
    assert (
        _stance("weakening", headwind_for=["Gold"], tailwind_for=[])["sentence_en"]
        == _stance("down", headwind_for=["Gold"], tailwind_for=[])["sentence_en"]
    )
    assert (
        _stance("strengthening", headwind_for=[], tailwind_for=["US equities"])["sentence_zh"]
        == _stance("up", headwind_for=[], tailwind_for=["US equities"])["sentence_zh"]
    )
    assert (
        _stance("weakening", headwind_for=[], tailwind_for=["US equities"])["sentence_zh"]
        == _stance("down", headwind_for=[], tailwind_for=["US equities"])["sentence_zh"]
    )


def test_soft_dollar_with_headwinds_only_is_lift_not_quiet():
    """Typical tape: inverse assets only. Soft dollar lifts them; never 'quiet'."""
    soft = _stance("down", headwind_for=["Gold", "Oil (WTI)"], tailwind_for=[])
    en, zh = soft["sentence_en"], soft["sentence_zh"]
    assert "giving" in en and "lift" in en, en
    assert "gold" in en.lower() and "oil" in en.lower(), en
    assert "leaning on" not in en, en
    assert "quiet" not in en.lower(), en
    assert "提振" in zh, zh
    assert "黄金" in zh, zh
    assert "压制" not in zh and "平静" not in zh, zh
    assert soft["headline_en"] == "Dollar soft"


def test_quiet_only_when_mixed_or_both_lists_empty():
    mixed = _stance("mixed", headwind_for=["Gold"], tailwind_for=["US equities"])
    assert "quiet" in mixed["sentence_en"].lower(), mixed["sentence_en"]
    assert "平静" in mixed["sentence_zh"], mixed["sentence_zh"]
    empty_firm = _stance("up", headwind_for=[], tailwind_for=[])
    empty_soft = _stance("down", headwind_for=[], tailwind_for=[])
    assert "quiet" in empty_firm["sentence_en"].lower(), empty_firm["sentence_en"]
    assert "quiet" in empty_soft["sentence_en"].lower(), empty_soft["sentence_en"]


def test_dollar_trend_scorecard_labels_12_month_horizon():
    """Hero 63d dollar_dir vs 12m overlay must not look like a contradiction."""
    src = _TEMPLATE.read_text(encoding="utf-8")
    longs = re.findall(r"Currently long[^<{]*", src)
    flats = re.findall(r"Currently flat[^<{]*", src)
    assert longs and all("12-month" in s for s in longs), longs
    assert flats and all("12-month" in s for s in flats), flats
    zh_longs = re.findall(r"当前做多[^<{]*", src)
    zh_flats = re.findall(r"当前空仓[^<{]*", src)
    assert zh_longs and all("12个月" in s for s in zh_longs), zh_longs
    assert zh_flats and all("12个月" in s for s in zh_flats), zh_flats
