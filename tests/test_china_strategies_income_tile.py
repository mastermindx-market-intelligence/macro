"""Display contract for the China strategies grid Income tile.

The Income-Vector card printed its own CAGR under "Income / 票息" because
scripts/build_china_strategies.py :48 read the blend's return as income. The tile now
takes its fields from scripts/_china_income_card.py sample_tile(): the backtest's
drawdown count (|dd| >= 10%) and the window start. The except-branch fallback
(income 2.6) and every build_strategies._card-shaped card must keep printing the seed
Income tile byte-identically.

Only the stdlib, jinja2 and the new helper are imported (the seat's CI job installs
nothing else, so scripts/build_*.py, engine.*, lib.*, pandas and numpy are forbidden
here — the builders' closure is ~328 modules). The real template is rendered with
autoescape=True as the builders do; every assertion is scoped inside the card's own
slice, as tests/test_china_mechanics_display.py _between() does.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jinja2 import Environment, FileSystemLoader  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATE = "china_strategies.html.j2"
# The template's own :root{...} block reads exactly these keys from C
# (scripts/build_vector.C at build time; a plain dict here — the tile never consumes them).
_C = {"blue": "#3B82F6", "indigo": "#4F46E5", "ink": "#0F172A", "text": "#22293A",
      "muted": "#5B6577", "faint": "#8A93A6", "red": "#D23C3C", "amber": "#C77B12",
      "grid": "#E3E8F0", "card": "#FFFFFF", "bg": "#F5F7FB"}


def _render(cards: list[dict]) -> str:
    env = Environment(loader=FileSystemLoader(str(_ROOT / "templates")), autoescape=True)
    return env.get_template(_TEMPLATE).render(C=_C, cards=cards, built="TEST")


def _between(html: str, start: str, end: str) -> str:
    i = html.index(start)
    return html[i + len(start):html.index(end, i)]


def _card_seg(html: str) -> str:
    """One rendered card: from <a class="scard" through its closing </a>, markers included."""
    i = html.index('<a class="scard"')
    return html[i:html.index("</a>", i) + len("</a>")]


def _metrics_seg(html: str) -> str:
    """The rendered <div class="metrics"> ... </div> of a single-card page."""
    return _between(html, '<div class="metrics">', '<div class="scard-foot">')


def _view(seg: str, lang: str) -> str:
    """One language of a card segment: the other language's l-* spans are stripped,
    mirroring the page's data-lang CSS toggle (html:18-22)."""
    other = "l-zh" if lang == "en" else "l-en"
    return re.sub(rf'<span class="{other}">.*?</span>', "", seg)


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fragment)).strip()


def _income_tile(income, years) -> str:
    """The seed line 188 rendered: <div> tile, t('Income','票息') macro output, % and y."""
    return ('        <div><span class="m-k"><span class="l-en">Income</span>'
            '<span class="l-zh">票息</span></span><span class="m-v">{}%</span>'
            '<span class="m-sub">{}y</span></div>'.format(income, years))


def _income_line(seg: str) -> str:
    """The whole rendered line carrying the Income m-k, with its 8-space indent."""
    i = seg.index('<span class="l-en">Income</span>')
    return seg[seg.rfind("\n", 0, i) + 1:seg.index("\n", i)]


def _vector_card(**over) -> dict:
    """A card shaped exactly like _income_vector_card()'s returned dict (:54-65);
    values mirror the committed blend record (cagr 7.75, maxdd -17.2)."""
    card = {
        "key": "income_vector", "icon": "◎", "href": "china_allocation.html",
        "name_en": "China Income Vector", "name_zh": "中国收入向量",
        "thesis_en": "Diversification, not timing: a static income + gold + short-bond blend.",
        "thesis_zh": "靠分散而非择时：红利 + 黄金 + 短债的静态组合。",
        "experimental": False,
        "cagr": 7.75, "hodl_cagr": 1.9, "sharpe": 0.94, "hodl_sharpe": 0.42,
        "maxdd": -17.2, "hodl_maxdd": -45.5, "income": 2.6, "years": 12.3,
        "stance_en": "Income + gold + bonds", "stance_zh": "红利 + 黄金 + 国债",
    }
    card.update(over)
    return card


def _timed_card(**over) -> dict:
    """A card shaped exactly like scripts/build_strategies.py _card() returns (:218-238)
    — read at the seed, never imported here."""
    card = {
        "key": "cn_credit_vol", "icon": "◆", "href": "strategy_cn_credit_vol.html",
        "name_en": "Credit Vol Timed", "name_zh": "信用波动择时",
        "thesis_en": "Rules-based sleeve on the credit ETF.",
        "thesis_zh": "信用债ETF的规则化模块。",
        "experimental": False,
        "cagr": 6.1, "hodl_cagr": 1.9, "sharpe": 0.5, "hodl_sharpe": 0.42,
        "maxdd": -30.0, "hodl_maxdd": -45.5, "income": 3.1, "years": 9.6,
        "stance_en": "Risk on cash off", "stance_zh": "风险开 现金关",
        "as_of": "2026-10-19", "score": None,
    }
    card.update(over)
    return card


# --------------------------------------------------------------------------- #
# the helper: scripts/_china_income_card.py sample_tile()


def test_sample_tile_reads_episode_count_and_window_start():
    from scripts._china_income_card import sample_tile
    assert sample_tile({"bear_episodes": [{}, {}], "start": "2013-07-19", "cagr": 7.75}) == {
        "income": None, "bear_n": 2, "win_start": "2013-07-19"}


def test_sample_tile_without_backtest_keeps_the_fallback_income():
    from scripts._china_income_card import sample_tile
    # no "income" key here, so **tile leaves the builder's fallback 2.6 untouched
    assert sample_tile(None) == {"bear_n": None, "win_start": None}
    empty = sample_tile({})
    assert empty["bear_n"] == 0 and empty["win_start"] is None


# --------------------------------------------------------------------------- #
# the template tile


def test_vector_card_prints_drawdown_count_not_income():
    card = _vector_card(income=None, bear_n=2, win_start="2013-07-19", years=12.3)
    seg = _metrics_seg(_render([card]))
    assert "Drawdowns ≥10%" in seg and "回撤≥10%次数" in seg
    assert ">2<" in seg and "2013-07-19" in seg
    for banned in ("Income", "票息", "7.8%", "None"):
        assert banned not in seg


def test_fallback_card_keeps_the_income_tile():
    card = _vector_card(income=2.6, bear_n=None, win_start=None, years=8.4)
    seg = _metrics_seg(_render([card]))
    assert _income_line(seg) == _income_tile(2.6, 8.4)
    assert "Income" in seg and "票息" in seg and "2.6%" in seg


def test_other_cards_render_byte_identically():
    card = _timed_card()  # income=3.1 and no bear_n key at all
    seg = _metrics_seg(_render([card]))
    assert _income_line(seg) == _income_tile(3.1, 9.6)
    assert "Drawdowns" not in seg


def test_en_and_zh_views_each_carry_one_language():
    card = _vector_card(income=None, bear_n=2, win_start="2013-07-19", years=12.3)
    seg = _card_seg(_render([card]))
    en, zh = _view(seg, "en"), _view(seg, "zh")
    assert "Drawdowns ≥10%" in en and "since" in en and "回撤" not in en
    assert "回撤≥10%次数" in zh and "自" in zh and "Drawdowns" not in zh
    for view in (en, zh):
        assert ">2<" in view and "2013-07-19" in view


def test_new_tile_adds_no_style_or_colour_literal():
    src = (_ROOT / "templates" / _TEMPLATE).read_text(encoding="utf-8")
    guard = "{%- if c.income is not number and c.bear_n is number %}"
    assert guard in src, "the drawdown tile guard exists in the template source"
    i = src.index(guard)
    block = src[i:src.index("{%- endif %}", i) + len("{%- endif %}")]
    assert "style=" not in block
    assert "<style" not in block
    assert not re.search(r"#[0-9a-fA-F]{3,6}", block)
    assert "rgb(" not in block and "hsl(" not in block


def test_missing_window_start_prints_no_dangling_label():
    card = _vector_card(income=None, bear_n=2, win_start=None, years=12.3)
    seg = _metrics_seg(_render([card]))
    i = seg.index("Drawdowns ≥10%")
    line = seg[seg.rfind("\n", 0, i) + 1:seg.index("\n", i)]
    assert "since" not in line and "自" not in line and "None" not in line
    assert '<span class="m-sub"></span>' in line


def test_cards_have_no_whitespace_only_line():
    # Every card whose 4th tile is the seed markup (fallback + _card-shaped) and the
    # drawdown card render with no empty or whitespace-only line in <a class="scard">…</a>.
    # Cards here carry experimental=True: with it False the untouched seed line 180
    # {% if c.experimental %} prints its own 8-space indent as a whitespace-only line
    # inside <div class="scard-top"> — seed behaviour, outside this tile's scope.
    fallback = _vector_card(income=2.6, bear_n=None, win_start=None, years=8.4,
                            experimental=True)
    drawdown = _vector_card(income=None, bear_n=2, win_start="2013-07-19", years=12.3,
                            experimental=True)
    for card in (drawdown, fallback, _timed_card(experimental=True)):
        assert re.search(r"\n[ \t]*\n", _card_seg(_render([card]))) is None
    seg = _card_seg(_render([fallback]))
    assert '</div>\n        <div><span class="m-k"><span class="l-en">Income</span>' in seg
    assert '8.4y</span></div>\n      </div>' in seg


# --------------------------------------------------------------------------- #
# the as-of line: each card prints its own data date (parity with the US grid)

# ci-trigger-closure: data — the builder is read as text only, never imported
_BUILDER = _ROOT / "scripts/build_china_strategies.py"

_ASOF_SPAN = ('      </div>\n      <span class="m-sub"><span class="l-en">As of</span>'
              '<span class="l-zh">截至</span> Oct 16, 2026</span>\n      <div class="scard-foot">')


def test_as_of_label_formats_a_date():
    from scripts._china_income_card import as_of_label
    assert as_of_label("2026-10-16") == "Oct 16, 2026"
    assert as_of_label("2013-07-01") == "Jul 01, 2013"


def test_as_of_label_refuses_everything_else():
    from datetime import datetime
    from scripts._china_income_card import as_of_label
    for bad in (None, 5, datetime(2026, 10, 16), "2026/10/16", "", "Oct 16, 2026",
                "2026-13-01", "2026-10-16T00:00:00"):
        assert as_of_label(bad) is None


def test_vector_card_prints_its_as_of():
    card = _vector_card(income=None, bear_n=2, win_start="2013-07-19",
                        as_of="Oct 16, 2026")
    assert _card_seg(_render([card])).count(_ASOF_SPAN) == 1


def test_timed_card_prints_its_as_of():
    assert _card_seg(_render([_timed_card(as_of="Oct 16, 2026")])).count(_ASOF_SPAN) == 1


def test_card_without_as_of_renders_the_seed_markup():
    renders = []
    for over in ({}, {"as_of": None}, {"as_of": ""}):
        html = _render([_vector_card(income=2.6, bear_n=None, win_start=None,
                                     years=8.4, **over)])
        assert '8.4y</span></div>\n      </div>\n      <div class="scard-foot">' in _card_seg(html)
        assert "As of" not in html and "截至" not in html
        renders.append(html)
    assert renders[0] == renders[1] == renders[2]


def test_as_of_en_and_zh_views():
    seg = _card_seg(_render([_timed_card(as_of="Oct 16, 2026")]))
    en, zh = _view(seg, "en"), _view(seg, "zh")
    assert "As of" in en and "Oct 16, 2026" in en and "截至" not in en
    assert "截至" in zh and "Oct 16, 2026" in zh and "As of" not in zh


def test_as_of_cards_have_no_whitespace_only_line():
    cards = (_vector_card(income=None, bear_n=2, win_start="2013-07-19", years=12.3,
                          as_of="Oct 16, 2026", experimental=True),
             _timed_card(as_of="Oct 16, 2026", experimental=True))
    for card in cards:
        assert re.search(r"\n[ \t]*\n", _card_seg(_render([card]))) is None


def test_as_of_line_adds_no_style_or_colour_literal():
    src = (_ROOT / "templates" / _TEMPLATE).read_text(encoding="utf-8")
    assert src.count("{%- if c.as_of %}") == 1
    i = src.index("{%- if c.as_of %}")
    block = src[i:src.index("{%- endif %}", i) + len("{%- endif %}")]
    lines = block.splitlines()
    assert len(lines) == 3
    assert "t('As of','截至')" in block and 'class="m-sub"' in block
    for bad in ("style=", "<style", "rgb(", "hsl("):
        assert bad not in block
    assert not re.search(r"#[0-9a-fA-F]{3,6}", block)
    for line in lines:
        assert len(line) <= 100


def test_builder_wires_the_vector_card_as_of():
    lines = _BUILDER.read_text(encoding="utf-8").splitlines()
    for prev, want in (("            income, tile = None, IC.sample_tile(bt)",
                        "            as_of = IC.as_of_label(ca._as_of())"),
                       ("        tile = IC.sample_tile(None)", "        as_of = None")):
        assert lines.count(prev) == 1 and lines.count(want) == 1
        assert lines[lines.index(prev) + 1] == want
    want = '        "as_of": as_of,'
    assert lines.count(want) == 1
    assert lines[lines.index(want) + 1] == "        **tile,"
