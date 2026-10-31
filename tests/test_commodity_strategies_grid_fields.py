"""Display contract for the commodity active-strategy grid (templates/commodity_strategies.html.j2).

The levered cards come from scripts/build_commodity_strategies.py::_build_active, whose card
dicts are patched by scripts/_commodity_card_fields.py. Committed shapes (seed evaluation):
gold avg_leverage 0.91 printed as "Income 0.91%", halves first=True/second=False; silver
True/True; copper False/True. These tests render the real template with autoescape=True over
synthetic cards (never the builder — its import closure is 328 modules) and pin the
avg-leverage tile, the non-active income tile byte-identical to the seed, the split-half foot
chip, the helper's four-way mapping and its degradation to absent fields.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jinja2 import Environment, FileSystemLoader  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_C = {"blue": "#285fff", "indigo": "#5b6bff", "r2": "#9aa4b2", "r3": "#cfd4dc",
      "ink": "#101828", "text": "#344054", "muted": "#667085", "faint": "#98a2b3",
      "red": "#e5484d", "amber": "#e0a106", "grid": "#e6e9ef", "card": "#ffffff",
      "bg": "#f7f8fa"}
_GOLD_EN = "Split-half: CAGR ahead of holding in the first half only"
_GOLD_ZH = "分段检验：仅前半段年化高于持有"
_GO_SPAN = ('<span class="go"><span class="l-en">Open →</span>'
            '<span class="l-zh">打开 →</span></span>')


def _env() -> Environment:
    env = Environment(loader=FileSystemLoader(str(_ROOT / "templates")), autoescape=True)
    env.globals.update(td=lambda en: en, tr=lambda en: en)
    return env


def _card(**over):
    """A card shaped like the builder's active card (AR.card output patched by card_fields)."""
    c = {"key": "cm_gold_active", "icon": "🥇", "href": "strategy_cm_gold_active.html",
         "name_en": "Gold Active", "name_zh": "黄金主动", "thesis_en": "t", "thesis_zh": "测",
         "experimental": True, "cagr": 12.0, "hodl_cagr": 11.0, "sharpe": 0.75,
         "hodl_sharpe": 0.67, "maxdd": -32.7, "hodl_maxdd": -44.4, "income": 0.91,
         "years": 8.4, "stance_en": "0.9x Gold · vol-targeted",
         "stance_zh": "0.9x 黄金 · 波动率目标"}
    c.update(over)
    return c


def _plain(**over):
    """A non-active card shaped like build_strategies._card (real income, no avg_lev)."""
    c = _card(key="cm_gold_swap", href="strategy_cm_gold_swap.html", income=3.2, years=20)
    c.update(over)
    return c


def _render(cards):
    groups = [{"key": "gold", "icon": "🥇", "label_en": "Gold", "label_zh": "黄金",
               "cards": cards}]
    return _env().get_template("commodity_strategies.html.j2").render(
        groups=groups, built="TEST", C=_C)


def _between(text: str, start: str, end: str) -> str:
    i = text.index(start)
    return text[i + len(start):text.index(end, i)]


def _text(fragment: str) -> str:
    return re.sub(r"<[^>]+>", " ", fragment)


def _seg(html: str, href: str) -> str:
    """One card's segment: from its unique anchor open tag to its closing </a>."""
    return _between(html, f'<a class="scard" href="{href}">', "</a>")


def _foot(seg: str) -> str:
    return _between(seg, '<div class="scard-foot">', "</div>")


def _income_tile(income, years) -> str:
    """The seed's :122 fourth tile rendered for one card (autoescape=True, one run, no gaps)."""
    return ('<div><span class="m-k"><span class="l-en">Income</span>'
            f'<span class="l-zh">票息</span></span><span class="m-v">{income}%'
            f'</span><span class="m-sub">{years}y</span></div>')


def _stance_span(en: str, zh: str) -> str:
    return (f'<span class="stance"><span class="l-en">{en}</span>'
            f'<span class="l-zh">{zh}</span></span>')


def test_active_card_prints_avg_leverage_not_income():
    html = _render([_card(income=None, avg_lev=0.91, years=8.4)])
    seg = _seg(html, "strategy_cm_gold_active.html")
    assert "Avg leverage" in seg and "平均杠杆" in seg
    assert "0.91x" in seg and "8.4y" in seg
    assert 'x</span><span class="m-sub">' in seg   # one run of markup, no whitespace gaps
    txt = _text(seg)
    for banned in ("Income", "票息", "None"):
        assert banned not in txt


def test_non_active_card_keeps_the_income_tile_byte_identical():
    plain = _plain()
    assert "avg_lev" not in plain and "oos_en" not in plain
    seg = _seg(_render([plain]), "strategy_cm_gold_swap.html")
    assert _income_tile(3.2, 20) in seg
    assert "Avg leverage" not in seg
    # present-but-not-a-number avg_lev (the helper's degraded shape) must still take the seed tile
    seg2 = _seg(_render([_plain(avg_lev=None, oos_en=None, oos_zh=None)]),
                "strategy_cm_gold_swap.html")
    assert _income_tile(3.2, 20) in seg2
    assert "Avg leverage" not in seg2


def test_card_fields_maps_each_split_half_combination():
    from scripts import _commodity_card_fields as CF
    expected = {
        (True, True): ("Split-half: CAGR ahead of holding in both halves",
                       "分段检验：前后两段年化均高于持有"),
        (True, False): (_GOLD_EN, _GOLD_ZH),
        (False, True): ("Split-half: CAGR ahead of holding in the second half only",
                        "分段检验：仅后半段年化高于持有"),
        (False, False): ("Split-half: CAGR not ahead of holding in either half",
                         "分段检验：两段年化均未高于持有"),
    }
    sc = {"avg_leverage": 0.91}
    for (first, second), (en, zh) in expected.items():
        oos = {"first": {"beats_cagr": first}, "second": {"beats_cagr": second}}
        out = CF.card_fields(sc, oos)
        assert (out["oos_en"], out["oos_zh"]) == (en, zh)
        assert out["avg_lev"] == 0.91 and out["income"] is None


def test_card_fields_degrades_without_oos_or_numeric_leverage():
    from scripts import _commodity_card_fields as CF
    for oos in (None, {}, {"first": 1, "second": {}}):
        out = CF.card_fields({"avg_leverage": 0.91}, oos)
        assert out["oos_en"] is None and out["oos_zh"] is None
    assert CF.card_fields({"avg_leverage": True}, None)["avg_lev"] is None
    assert CF.card_fields({"avg_leverage": "0.9"}, None)["avg_lev"] is None
    assert CF.card_fields({}, None)["avg_lev"] is None
    assert CF.card_fields({"avg_leverage": 0.91}, None)["avg_lev"] == 0.91
    for sc in ({}, {"income": 3.2}, {"avg_leverage": True}, {"avg_leverage": 0.91}):
        assert CF.card_fields(sc, None)["income"] is None


def test_split_half_chip_renders_in_the_foot_only_when_present():
    gold = _card(income=None, avg_lev=0.91, oos_en=_GOLD_EN, oos_zh=_GOLD_ZH)
    foot = _foot(_seg(_render([gold]), "strategy_cm_gold_active.html"))
    assert "data-split-half" in foot and _GOLD_EN in foot and _GOLD_ZH in foot
    chip = (f'<span class="stance" data-split-half><span class="l-en">{_GOLD_EN}'
            f'</span><span class="l-zh">{_GOLD_ZH}</span></span>')
    assert chip in foot
    plain = _plain()
    foot2 = _foot(_seg(_render([plain]), "strategy_cm_gold_swap.html"))
    assert "data-split-half" not in foot2
    assert foot2.strip() == (_stance_span(plain["stance_en"], plain["stance_zh"])
                             + "\n        " + _GO_SPAN)


def test_committed_shapes_render_their_split_half_text():
    from scripts import _commodity_card_fields as CF
    cases = ((True, False, "first half only", "仅前半段"),
             (True, True, "both halves", "前后两段"),
             (False, True, "second half only", "仅后半段"))
    sc = {"avg_leverage": 0.91}
    for first, second, en_part, zh_part in cases:
        oos = {"first": {"beats_cagr": first}, "second": {"beats_cagr": second}}
        card = _card()
        card.update(CF.card_fields(sc, oos))
        seg = _seg(_render([card]), "strategy_cm_gold_active.html")
        assert en_part in seg and zh_part in seg


def test_en_and_zh_views_each_carry_one_language():
    gold = _card(income=None, avg_lev=0.91, oos_en=_GOLD_EN, oos_zh=_GOLD_ZH)
    seg = _seg(_render([gold]), "strategy_cm_gold_active.html")
    en_view = re.sub(r'<span class="l-zh">.*?</span>', "", seg)
    zh_view = re.sub(r'<span class="l-en">.*?</span>', "", seg)
    assert "Avg leverage" in en_view and "平均杠杆" not in en_view
    assert "平均杠杆" in zh_view and "Avg leverage" not in zh_view
    assert "0.91x" in en_view and "0.91x" in zh_view


def test_no_new_css_or_colour_literal():
    tpl = (_ROOT / "templates" / "commodity_strategies.html.j2").read_text(encoding="utf-8")
    tile = _between(tpl, "{%- if c.avg_lev is number %}", "{%- else %}")
    chip = _between(tpl, '<span class="stance" data-split-half', "\n")
    for frag in (tile, chip):
        assert "<style" not in frag and "style=" not in frag
        assert re.search(r"#[0-9a-fA-F]{3,6}", frag) is None
        assert "rgb(" not in frag and "hsl(" not in frag


def test_cards_have_no_whitespace_only_line():
    gold = _card(income=None, avg_lev=0.91, oos_en=_GOLD_EN, oos_zh=_GOLD_ZH)
    plain = _plain()
    html = _render([gold, plain])
    gold_seg = _seg(html, "strategy_cm_gold_active.html")
    plain_seg = _seg(html, "strategy_cm_gold_swap.html")
    for seg in (gold_seg, plain_seg):
        assert re.search(r"\n[ \t]*\n", seg) is None
    plain_foot = _between(plain_seg, '<div class="scard-foot">', "</div>")
    assert plain_foot.strip() == (_stance_span(plain["stance_en"], plain["stance_zh"])
                                  + "\n        " + _GO_SPAN)


# --------------------------------------------------------------------------- #
# the as-of line: each card prints its own data date (parity with the US grid)

# ci-trigger-closure: data — the builder is read as text only, never imported
_BUILDER = _ROOT / "scripts/build_commodity_strategies.py"

_ASOF_SPAN = ('      </div>\n      <span class="m-sub"><span class="l-en">As of</span>'
              '<span class="l-zh">截至</span> Oct 16, 2026</span>\n      <div class="scard-foot">')


def test_active_and_plain_cards_print_their_as_of():
    html = _render([_card(income=None, avg_lev=0.91, as_of="Oct 16, 2026"),
                    _plain(as_of="Oct 16, 2026")])
    for href in ("strategy_cm_gold_active.html", "strategy_cm_gold_swap.html"):
        assert _seg(html, href).count(_ASOF_SPAN) == 1


def test_card_without_as_of_renders_the_seed_markup():
    renders = []
    for over in ({}, {"as_of": None}, {"as_of": ""}):
        html = _render([_plain(**over), _card(**over)])
        for href in ("strategy_cm_gold_swap.html", "strategy_cm_gold_active.html"):
            assert '      </div>\n      <div class="scard-foot">' in _seg(html, href)
        assert "As of" not in html and "截至" not in html
        renders.append(html)
    assert renders[0] == renders[1] == renders[2]


def test_as_of_en_and_zh_views():
    html = _render([_card(income=None, avg_lev=0.91, as_of="Oct 16, 2026")])
    seg = _seg(html, "strategy_cm_gold_active.html")
    en_view = re.sub(r'<span class="l-zh">.*?</span>', "", seg)
    zh_view = re.sub(r'<span class="l-en">.*?</span>', "", seg)
    assert "As of" in en_view and "Oct 16, 2026" in en_view and "截至" not in en_view
    assert "截至" in zh_view and "Oct 16, 2026" in zh_view and "As of" not in zh_view


def test_as_of_cards_have_no_whitespace_only_line():
    html = _render([_card(income=None, avg_lev=0.91, as_of="Oct 16, 2026"),
                    _plain(as_of="Oct 16, 2026")])
    for href in ("strategy_cm_gold_active.html", "strategy_cm_gold_swap.html"):
        assert re.search(r"\n[ \t]*\n", _seg(html, href)) is None


def test_as_of_line_adds_no_style_or_colour_literal():
    src = (_ROOT / "templates" / "commodity_strategies.html.j2").read_text(encoding="utf-8")
    assert src.count("{%- if c.as_of %}") == 1
    i = src.index("{%- if c.as_of %}")
    block = src[i:src.index("{%- endif %}", i) + len("{%- endif %}")]
    lines = block.splitlines()
    assert len(lines) == 3
    assert "t('As of','截至')" in block and 'class="m-sub"' in block
    for bad in ("style=", "<style", "rgb(", "hsl("):
        assert bad not in block
    assert re.search(r"#[0-9a-fA-F]{3,6}", block) is None
    for line in lines:
        assert len(line) <= 100


def test_builder_sets_active_card_as_of_from_the_evaluation():
    lines = _BUILDER.read_text(encoding="utf-8").splitlines()
    want = '        card["as_of"] = ev.get("asof")'
    assert lines.count(want) == 1
    i = lines.index(want)
    assert lines[i - 1] == '        card.update(CF.card_fields(sc, ev.get("oos")))'
    assert lines[i + 1] == '        cards_by_group.setdefault(m["group"], []).append(card)'
