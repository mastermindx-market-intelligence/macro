"""Rendered-behavior tests for the additive Prophet opportunity card component.

Spec under test: research/PROPHET_PRODUCT_IMPLEMENTATION_20261015.md, step A —
the frozen opportunity-card anatomy as ``_prophet_opportunity_card.html.j2`` +
``_prophet_opportunity.css.j2``. These are presentation-only component tests:
they execute the ACTUAL Jinja templates under ``Environment(autoescape=True,
undefined=StrictUndefined)`` — the strictest contract the component must
survive, with both the complete and the minimal read model — and assert on the
rendered DOM via the standard library's ``html.parser``. No browser, no
network, no new packages, no fixtures beyond these dicts.

Covered, per the component contract:
· the complete read model renders bilingual .l-en/.l-zh pairs, with the
  documented English fallback when a record omits zh;
· the three clocks (quote / chart / terms) each keep their own publication
  date and never borrow each other's;
· chart ink follows the chart's OWN direction, never the stance;
· priority 0 and amount 0 are real values and must survive truthiness;
· minimal/None/partial read models render short, specific missing states
  without fabricating numbers, dates, clocks or maturity;
· malformed chart points (NaN/±inf/out-of-range/bool/string/None/single/
  wrong container) render the neutral History unavailable state, never a fake
  line, and per-point filtering keeps only the honest points;
· hostile strings are autoescaped and never become tags, attributes or class
  names; only safe site-relative hrefs render anchors;
· cautions use native details/summary exactly when there is something to
  expand, with the most consequential caution visible at rest;
· DOM ids and compare-checkbox bindings are unique and correctly bound, and
  the checkbox is disabled when no comparable identity exists;
· the stylesheet keeps its scoping, token, typography, grid and height laws.

Known limitations, stated plainly: there is no browser in this loop, so CSS is
asserted at the rule level and no pixel/visual acceptance is claimed (spec:
"A screenshot count is not acceptance"). That visual review is a separate,
later gate. JavaScript behavior is out of scope by design: the component ships
no script.
"""

from __future__ import annotations

import math
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
CARD = "_prophet_opportunity_card.html.j2"
STYLESHEET = "_prophet_opportunity.css.j2"

_IMPORT = "{%- from '_prophet_opportunity_card.html.j2' import opportunity_card -%}"


# ── minimal DOM over the standard-library parser ──────────────────────────────
class _Node:
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag, attrs, parent):
        self.tag = tag
        self.attrs = attrs
        self.parent = parent
        self.children = []  # _Node | str


_ROOT = "#root"
_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
         "meta", "param", "source", "track", "wbr"}


class _TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node(_ROOT, {}, None)
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = _Node(tag, dict(attrs), self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in _VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(_Node(tag, dict(attrs), self.stack[-1]))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if data:
            self.stack[-1].children.append(data)


def parse(html: str) -> _Node:
    builder = _TreeBuilder()
    builder.feed(html)
    builder.close()
    return builder.root


def walk(node: _Node):
    for child in node.children:
        if isinstance(child, _Node):
            yield child
            yield from walk(child)


def find_all(node: _Node, tag=None, cls=None, attrs=None) -> list[_Node]:
    hits = []
    for n in walk(node):
        if tag is not None and n.tag != tag:
            continue
        if cls is not None and cls not in (n.attrs.get("class") or "").split():
            continue
        if attrs:
            if any(n.attrs.get(k) != v for k, v in attrs.items()):
                continue
        hits.append(n)
    return hits


def find(node: _Node, tag=None, cls=None, attrs=None) -> _Node:
    hits = find_all(node, tag, cls, attrs)
    assert len(hits) == 1, f"expected exactly 1 <{tag} .{cls} {attrs}>, got {len(hits)}"
    return hits[0]


def maybe_find(node: _Node, tag=None, cls=None, attrs=None):
    hits = find_all(node, tag, cls, attrs)
    return hits[0] if hits else None


def text_of(node: _Node) -> str:
    parts = []
    for child in node.children:
        if isinstance(child, _Node):
            parts.append(text_of(child))
        else:
            parts.append(child)
    return "".join(parts)


def classes(node: _Node) -> set[str]:
    return set((node.attrs.get("class") or "").split())


def element_children(node: _Node) -> list[_Node]:
    return [c for c in node.children if isinstance(c, _Node)]


# ── rendering under the strict contract ───────────────────────────────────────
def render_raw(v: dict, *, extra: str = "") -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)),
                      autoescape=True, undefined=StrictUndefined)
    return env.from_string(f"{_IMPORT}{extra}{{{{ opportunity_card(v) }}}}").render(v=v)


def render_card(v: dict) -> _Node:
    return parse(render_raw(v))


def render_many(*cards: dict) -> str:
    calls = "".join(f"{{{{ opportunity_card(_c{i}) }}}}" for i in range(len(cards)))
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)),
                      autoescape=True, undefined=StrictUndefined)
    names = {f"_c{i}": c for i, c in enumerate(cards)}
    return env.from_string(f"{_IMPORT}{calls}").render(**names)


# ── read-model fixtures ───────────────────────────────────────────────────────
def rich_card(**over) -> dict:
    """The complete read model: every slot supplied, EN+ZH records throughout.
    The three clocks are deliberately distinct (14th / 13th / 12th)."""
    v = {
        "id": "nvda-2026-10",
        "stance": "buy",
        "stance_label": {"en": "Constructive", "zh": "偏多"},
        "strategy": {"en": "Early Leadership", "zh": "早期领涨"},
        "horizon": {"en": "Swing · weeks", "zh": "波段 · 数周"},
        "quote": {"price": "188.42", "change": "+2.1%", "direction": "up",
                  "asof": "2026-10-14 16:00 ET", "currency": "USD"},
        "chart": {"points": [{"x": 0, "y": 80}, {"x": 25, "y": 70}, {"x": 50, "y": 55},
                             {"x": 75, "y": 40}, {"x": 100, "y": 20}],
                  "label": {"en": "Close, last 5 sessions", "zh": "近 5 个交易日收盘"},
                  "asof": "2026-10-13", "direction": "up"},
        "identity": {"ticker": "NVDA",
                     "name": {"en": "NVIDIA Corporation", "zh": "英伟达"},
                     "industry": {"en": "Semiconductors", "zh": "半导体"},
                     "sector": {"en": "Technology", "zh": "科技"}},
        "priority": {"value": 0,
                     "meaning": {"en": "Board order, not a recommendation",
                                 "zh": "榜面顺序，非操作建议"}},
        "observation": {"en": "Base holding above the 50-day; volume drying on pullbacks.",
                        "zh": "守住 50 日线整理；回调缩量。"},
        "cautions": [{"en": "Extended 9% above the 20-day.", "zh": "较 20 日线乖离 9%。"},
                     {"en": "Earnings window opens in 11 days.", "zh": "11 个交易日后进入财报窗口。"},
                     {"en": "Leadership breadth narrowing.", "zh": "领涨宽度收窄。"}],
        "stages": [{"label": {"en": "Base", "zh": "筑底"}, "active": True},
                   {"label": {"en": "Turn", "zh": "转向"}, "active": False},
                   {"label": {"en": "Ready", "zh": "就绪"}, "active": False},
                   {"label": {"en": "Trend", "zh": "趋势"}, "active": False}],
        "marks": [{"en": "New", "zh": "新上榜", "tone": "info"},
                  {"en": "Theme turned", "zh": "主题转暖", "tone": "warn"},
                  {"en": "Wide float", "zh": "流通盘大", "tone": "not-a-tone"}],
        "context": {"href": "/research/nvda-base-2026-10",
                    "label": {"en": "Full base study", "zh": "完整形态研究"}},
        "terms": {"label": {"en": "Entry zone", "zh": "入场区间"},
                  "value": "168–176", "asof": "2026-10-12", "currency": "USD"},
        "setup_href": "/setup/NVDA",
        "compare_enabled": True,
    }
    v.update(over)
    return v


# ── 1. the complete card ──────────────────────────────────────────────────────
def test_complete_card_renders_bilingual_records():
    root = render_card(rich_card())
    card = find(root, cls="po-card")
    assert "po-buy" in classes(card)
    en_texts = [text_of(n) for n in find_all(root, cls="l-en")]
    zh_texts = [text_of(n) for n in find_all(root, cls="l-zh")]
    assert len(en_texts) == len(zh_texts) and len(en_texts) >= 12
    for en, zh in (("Constructive", "偏多"), ("Early Leadership", "早期领涨"),
                   ("NVIDIA Corporation", "英伟达"), ("Entry zone", "入场区间"),
                   ("View setup", "查看形态")):
        assert en in en_texts and zh in zh_texts
    # the identity and terms values themselves render verbatim
    assert text_of(find(root, cls="po-ticker")) == "NVDA"
    assert "168–176" in text_of(find(root, cls="po-terms-value"))


def test_bilingual_record_without_zh_falls_back_to_english():
    root = render_card(rich_card(
        identity={"ticker": "NVDA", "name": {"en": "Board order only"}},
        observation={"en": "Only the English line was supplied."}))
    name = find(root, cls="po-name")
    assert text_of(find(name, cls="l-en")) == "Board order only"
    assert text_of(find(name, cls="l-zh")) == "Board order only"


def test_frozen_anatomy_order():
    root = render_card(rich_card())
    card = find(root, cls="po-card")
    order = [f"{n.tag}.{'-'.join(sorted(classes(n)))}" for n in element_children(card)]
    assert order == [
        "header.po-head", "figure.po-chart", "div.po-id", "p.po-obs",
        "details.po-cautions", "ol.po-stages", "a.po-context",
        "div.po-terms", "footer.po-foot",
    ]


# ── 2. three independent clocks ───────────────────────────────────────────────
def test_three_clocks_stay_independent():
    root = render_card(rich_card())
    quote = find(root, attrs={"data-po-clock": "quote"})
    chart = find(root, attrs={"data-po-clock": "chart"})
    terms = find(root, attrs={"data-po-clock": "terms"})
    assert "2026-10-14 16:00 ET" in text_of(quote)
    assert "2026-10-13" in text_of(chart)
    assert "2026-10-12" in text_of(terms)
    # no clock borrows another clock's publication date
    assert "2026-10-13" not in text_of(quote) and "2026-10-12" not in text_of(quote)
    assert "2026-10-12" not in text_of(chart)
    assert "2026-10-13" not in text_of(terms)
    # quote freshness never rewrites the terms band
    assert "2026-10-14" not in text_of(terms)


def test_missing_publication_date_is_stated_not_invented():
    root = render_card(rich_card(quote={"price": "12"}, terms={"value": "9-11"}, chart=None))
    assert text_of(find(root, attrs={"data-po-clock": "quote"})).count("Date unverified") == 1
    assert text_of(find(root, attrs={"data-po-clock": "terms"})).count("Date unverified") == 1
    assert "History unavailable" in text_of(root)  # chart clock absent with the chart


# ── 3. chart geometry, direction independence, garbage rejection ─────────────
def test_valid_chart_plots_supplied_points_verbatim():
    pts = [{"x": 0, "y": 80}, {"x": 25, "y": 70}, {"x": 50, "y": 55},
           {"x": 75, "y": 40}, {"x": 100, "y": 20}]
    svg = find(render_card(rich_card(chart={"points": pts, "direction": "up",
                                            "asof": "2026-10-13"})), tag="svg")
    assert svg.attrs["viewbox"] == "0 0 100 100"
    assert svg.attrs["preserveaspectratio"] == "none"
    poly = find(svg, tag="polyline")
    assert poly.attrs["points"].split() == [f"{round(p['x'], 2)},{round(p['y'], 2)}" for p in pts]


def test_float_points_round_for_the_points_attribute_only():
    pts = [{"x": 0.5, "y": 12.3456}, {"x": 99.99, "y": 0.001}]
    poly = find(render_card(rich_card(chart={"points": pts})), tag="polyline")
    assert poly.attrs["points"].split() == ["0.5,12.35", "99.99,0.0"]


@pytest.mark.parametrize("direction", ["up", "down", "flat", "sideways", None])
def test_chart_ink_follows_chart_direction_never_stance(direction):
    chart = {"points": [{"x": 0, "y": 0}, {"x": 100, "y": 100}]}
    if direction is not None:
        chart["direction"] = direction
    root = render_card(rich_card(stance="buy", chart=chart))
    assert "po-buy" in classes(find(root, cls="po-card"))
    plot = find(root, cls="po-chart-plot")
    expected = direction if direction in ("up", "down", "flat") else "flat"
    assert f"po-dir-{expected}" in classes(plot)
    # the direction class never leaks onto the card, the stance never onto the chart
    assert not any(c.startswith("po-dir-") for c in classes(find(root, cls="po-card")))
    assert not any(c.startswith("po-") and c in ("po-buy", "po-near", "po-wait",
                                                 "po-hold", "po-avoid") for c in classes(plot))


def test_quote_change_ink_is_directional_and_independent():
    root = render_card(rich_card(quote={"price": "5", "change": "-1.0%", "direction": "down"}))
    assert "po-dir-down" in classes(find(root, cls="po-chg"))
    root = render_card(rich_card(quote={"price": "5", "change": "+1.0%", "direction": "up"}))
    assert "po-dir-up" in classes(find(root, cls="po-chg"))
    root = render_card(rich_card(quote={"price": "5", "change": "0.0%", "direction": "weird"}))
    assert "po-dir-flat" in classes(find(root, cls="po-chg"))


BAD_CHARTS = [
    None,
    {},
    {"points": []},
    {"points": None},
    {"points": 5},
    {"points": "ab"},
    {"points": {"x": 0, "y": 0}},
    {"points": [{"x": 0, "y": 0}]},                                    # single point
    {"points": [{"x": math.nan, "y": 0}, {"x": 1, "y": 1}]},           # NaN
    {"points": [{"x": math.inf, "y": 0}, {"x": 1, "y": 1}]},           # +inf
    {"points": [{"x": 0, "y": -math.inf}, {"x": 1, "y": 1}]},          # -inf
    {"points": [{"x": 150, "y": 0}, {"x": 1, "y": 1}]},                # out of range
    {"points": [{"x": 0, "y": -1}, {"x": 1, "y": 1}]},
    {"points": [{"x": "0", "y": 0}, {"x": 1, "y": 1}]},                # numeric string
    {"points": [{"x": True, "y": 0}, {"x": 1, "y": 1}]},               # boolean
    {"points": [{"x": None, "y": 0}, {"x": 1, "y": 1}]},
    {"points": [{"x": 0, "y": 0}, {"x": 200, "y": 5}]},                # only one survives
    {"points": [{"x": 0, "y": 0}, {"x": 1, "y": 1, "z": 9}]},          # junk extra key is fine
]


@pytest.mark.parametrize("chart", BAD_CHARTS[:-1], ids=range(len(BAD_CHARTS) - 1))
def test_garbage_history_renders_neutral_state_never_a_fake_line(chart):
    root = render_card(rich_card(chart=chart))
    assert find_all(root, tag="svg") == []
    assert maybe_find(root, cls="po-nochart") is not None
    assert "History unavailable" in text_of(root)
    assert find_all(root, tag="polyline") == []


def test_per_point_filtering_keeps_only_honest_points():
    chart = {"points": [{"x": 0, "y": 10}, {"x": math.nan, "y": 5}, {"x": 100, "y": 90}]}
    poly = find(render_card(rich_card(chart=chart)), tag="polyline")
    assert poly.attrs["points"].split() == ["0,10", "100,90"]


def test_empty_history_is_explicit():
    root = render_card(rich_card(chart={"points": [], "label": "Close", "asof": "2026-10-13"}))
    assert find_all(root, tag="svg") == []
    assert "History unavailable" in text_of(root)
    # an unavailable history publishes no clock — there is no observation time to show
    assert maybe_find(root, attrs={"data-po-clock": "chart"}) is None


# ── 4. zero is a real value; truthiness never eats it ─────────────────────────
def test_priority_zero_renders():
    root = render_card(rich_card(priority={"value": 0, "meaning": {"en": "Board order"}}))
    assert text_of(find(root, cls="po-priority-value")) == "0"


def test_zero_quote_values_render():
    root = render_card(rich_card(quote={"price": 0, "change": 0, "direction": "flat"}))
    assert text_of(find(root, cls="po-price")) == "0"
    assert text_of(find(root, cls="po-chg")) == "0"


def test_boolean_is_not_a_display_value():
    root = render_card(rich_card(quote={"price": True}, priority={"value": False}))
    assert "Quote unavailable" in text_of(root)
    assert find_all(root, cls="po-priority-value") == []
    assert "Priority unavailable" not in text_of(root)  # the record exists; the value is a dash
    assert maybe_find(root, cls="po-priority") is not None


# ── 5. missing / null / minimal data ─────────────────────────────────────────
def test_minimal_dict_renders_under_strictundefined():
    out = render_raw({})
    root = parse(out)
    card = find(root, cls="po-card")
    assert "po-unknown" in classes(card)
    assert card.attrs["data-po-stance"] == "unknown"
    assert "No read yet" in text_of(card)
    for missing in ("Strategy unavailable", "Horizon unavailable", "Quote unavailable",
                    "History unavailable", "Identity unavailable", "Priority unavailable",
                    "Observation unavailable", "Stage information unavailable",
                    "Terms unavailable", "Setup unavailable"):
        assert missing in text_of(root), missing


def test_minimal_card_fabricates_nothing():
    out = render_raw({})
    assert "As of" not in out                      # no clocks invented
    assert not re.search(r"20\d\d", out)           # no dates invented
    assert 'aria-current' not in out               # no maturity invented
    assert "Compare" not in text_of(parse(out))    # no control invented


def test_null_fields_render_specific_missing_states():
    root = render_card(rich_card(quote=None, chart=None, identity=None, priority=None,
                                 terms=None, stages=None, context=None, cautions=None,
                                 strategy=None, horizon=None, observation=None))
    for missing in ("Quote unavailable", "History unavailable", "Identity unavailable",
                    "Priority unavailable", "Terms unavailable",
                    "Stage information unavailable", "Strategy unavailable",
                    "Horizon unavailable", "Observation unavailable"):
        assert missing in text_of(root), missing
    assert find_all(root, cls="po-stages-missing") and find_all(root, cls="po-terms-missing")


def test_partial_quote_reports_what_is_missing():
    root = render_card(rich_card(quote={"price": "188.42"}))
    quote = find(root, attrs={"data-po-clock": "quote"})
    assert "188.42" in text_of(find(root, cls="po-price"))
    assert "Change unavailable" in text_of(quote)
    assert find_all(quote, cls="po-currency") == []         # no currency invented
    assert "Date unverified" in text_of(quote)


def test_mistyped_records_degrade_to_missing_states():
    root = render_card(rich_card(quote="188.42", identity="NVDA", priority=0,
                                 terms=42, context="/setup/x"))
    for missing in ("Quote unavailable", "Identity unavailable",
                    "Priority unavailable", "Terms unavailable",
                    "Context link unavailable"):
        assert missing in text_of(root), missing


# ── 6. stance vocabulary ──────────────────────────────────────────────────────
@pytest.mark.parametrize("stance", ["buy", "near", "wait", "hold", "avoid", "unknown"])
def test_supplied_stance_enum_maps_to_class_and_data(stance):
    card = find(render_card(rich_card(stance=stance)), cls="po-card")
    assert f"po-{stance}" in classes(card)
    assert card.attrs["data-po-stance"] == stance


@pytest.mark.parametrize("stance", ["moon", "BUY", "", None])
def test_off_enum_stance_defaults_to_unknown(stance):
    card = find(render_card(rich_card(stance=stance)), cls="po-card")
    assert "po-unknown" in classes(card)
    assert "No read yet" in text_of(card)


def test_canonical_stance_words_when_no_label_supplied():
    root = render_card(rich_card(stance="wait", stance_label=None))
    assert "Wait" in [text_of(n) for n in find_all(root, cls="l-en")]
    assert "等待" in [text_of(n) for n in find_all(root, cls="l-zh")]


def test_stance_label_override_wins():
    root = render_card(rich_card(stance="buy", stance_label={"en": "Constructive", "zh": "偏多"}))
    assert "Constructive" in [text_of(n) for n in find_all(root, cls="l-en")]


# ── 7. hostile strings: autoescape, class names, ids ─────────────────────────
def test_hostile_strings_stay_text():
    v = rich_card(
        id='x"><script>alert(1)</script>',
        identity={"ticker": 'NV"><img src=x onerror=alert(1)>',
                  "name": {"en": "<b>bold</b> & <i>tags</i>",
                           "zh": "<script>alert(1)</script>"}},
        observation={"en": 'Only "quoted" & <em>marked</em> text.'},
        stance_label={"en": '"><svg onload=alert(1)>', "zh": "<iframe src=x>"},
    )
    out = render_raw(v)
    assert "<script" not in out and "<img" not in out and "<iframe" not in out
    assert "&lt;script" in out and "&amp;" in out
    root = parse(out)
    assert find_all(root, tag="script") == []
    assert find_all(root, tag="img") == []
    assert find_all(root, tag="iframe") == []
    # the only <svg> is the fixture's own legitimate chart, inside the chart slot
    for svg in find_all(root, tag="svg"):
        assert svg.parent is not None and "po-chart-plot" in classes(svg.parent)
    # the hostile text survived as TEXT of the affected slots
    assert "onerror=alert(1)" in text_of(find(root, cls="po-ticker"))
    # and the id was sanitized to the safe charset, never an attribute escape
    card = find(root, cls="po-card")
    assert re.fullmatch(r"[a-z0-9_-]+", card.attrs["id"])
    assert re.fullmatch(r"[a-z0-9_-]+", find(root, tag="input").attrs["id"].replace("-compare", ""))


def test_class_names_are_whitelisted_never_data_authored():
    root = render_card(rich_card(
        marks=[{"en": "Evil", "tone": "warn padding:9999px\"><script>"}],
        quote={"price": "5", "change": "1%", "direction": "up onclick=alert(1)"},
        chart={"points": [{"x": 0, "y": 0}, {"x": 1, "y": 1}], "direction": "down onerror=x"}))
    for n in walk(root):
        for value in n.attrs.values():
            assert "<" not in value and ">" not in value
    assert any("po-mark-neutral" in c for n in find_all(root, cls="po-mark") for c in classes(n))


def test_no_inline_style_attributes_anywhere():
    root = render_card(rich_card())
    assert all(not n.attrs.get("style") for n in walk(root))


# ── 8. href law ───────────────────────────────────────────────────────────────
BAD_HREFS = [
    "javascript:alert(1)",
    "JavaScript:alert(1)",
    "data:text/html,<b>x</b>",
    "//evil.com/x",
    "///evil",
    "https://evil.com/x",
    "http://evil.com",
    "/\\evil.com",
    "\\evil",
    " /setup/x",
    "/setup/x\n",
    "/setup/x\tmore",
    "jav\tascript:alert(1)",
]


@pytest.mark.parametrize("href", BAD_HREFS)
def test_unsafe_setup_href_never_renders_an_anchor(href):
    root = render_card(rich_card(setup_href=href))
    assert find_all(root, cls="po-setup") == []
    assert all(a.attrs.get("href") != href for a in find_all(root, tag="a"))
    assert "Setup unavailable" in text_of(root)


@pytest.mark.parametrize("href", BAD_HREFS)
def test_unsafe_context_href_never_renders_an_anchor(href):
    root = render_card(rich_card(context={"href": href, "label": {"en": "Context"}}))
    assert find_all(root, cls="po-context") == []
    assert all(a.attrs.get("href") != href for a in find_all(root, tag="a"))
    assert "Context link unavailable" in text_of(root)


@pytest.mark.parametrize("href", ["/setup/NVDA", "#nvda", "/", "#"])
def test_safe_site_relative_hrefs_render_real_anchors(href):
    root = render_card(rich_card(setup_href=href))
    assert find(root, cls="po-setup").attrs["href"] == href


def test_context_link_renders_only_when_safe():
    root = render_card(rich_card())
    link = find(root, cls="po-context")
    assert link.attrs["href"] == "/research/nvda-base-2026-10"
    assert "Full base study" in text_of(link)


def test_absent_context_and_absent_cautions_render_no_block():
    root = render_card(rich_card(context=None, cautions=None))
    assert find_all(root, cls="po-context") == []
    assert find_all(root, cls="po-context-missing") == []
    assert find_all(root, cls="po-cautions") == []
    assert find_all(root, cls="po-caution-single") == []


def test_querystring_href_is_escaped_into_the_attribute():
    root = render_card(rich_card(setup_href="/setup/NVDA?a=1&b=2"))
    assert find(root, cls="po-setup").attrs["href"] == "/setup/NVDA?a=1&b=2"


# ── 9. cautions: native disclosure, top caution visible ──────────────────────
def test_multiple_cautions_expand_from_native_details_summary():
    root = render_card(rich_card())
    det = find(root, cls="po-cautions")
    assert det.tag == "details"
    first_element = element_children(det)[0]
    assert first_element.tag == "summary"
    summary_text = text_of(first_element)
    assert "Key caution" in summary_text
    assert "Extended 9% above the 20-day." in summary_text      # most consequential at rest
    assert "+2" in summary_text
    items = [text_of(li) for li in find_all(det, tag="li")]
    assert len(items) == 2
    assert any("Earnings window" in t for t in items)
    assert not any("Extended 9%" in t for t in items)           # not duplicated in the list
    assert "open" not in det.attrs                              # collapsed at rest


def test_single_caution_never_fakes_a_disclosure_control():
    root = render_card(rich_card(cautions=[{"en": "Only one caution.", "zh": "只有一条注意事项。"}]))
    assert find_all(root, tag="details") == []
    single = find(root, cls="po-caution-single")
    assert "Only one caution." in text_of(single)


# ── 10. stages, marks ─────────────────────────────────────────────────────────
def test_native_stages_render_supplied_labels_and_active_flag():
    root = render_card(rich_card())
    stages = find_all(root, cls="po-stage")
    assert [text_of(s).strip() for s in stages] == ["Base筑底", "Turn转向", "Ready就绪", "Trend趋势"]
    on = find(root, cls="po-stage-on")
    assert on.attrs.get("aria-current") == "step"
    assert len(find_all(root, cls="po-stage-on")) == 1


def test_stage_absence_is_stated_never_a_default_lifecycle():
    root = render_card(rich_card(stages=None))
    assert find_all(root, tag="ol") == []
    assert "Stage information unavailable" in text_of(root)
    assert "aria-current" not in render_raw(rich_card(stages=None))


def test_mark_tone_is_whitelisted():
    root = render_card(rich_card())
    tones = [next(iter((classes(m) & {"po-mark-info", "po-mark-warn", "po-mark-neutral"})))
             for m in find_all(root, cls="po-mark")]
    assert tones == ["po-mark-info", "po-mark-warn", "po-mark-neutral"]


# ── 11. ids and compare bindings ─────────────────────────────────────────────
def test_ids_are_unique_and_checkbox_bindings_match():
    root = parse(render_many(rich_card(id="alpha"), rich_card(id="beta")))
    ids = [n.attrs["id"] for n in walk(root) if n.attrs.get("id")]
    assert sorted(ids) == ["po-alpha", "po-alpha-compare", "po-beta", "po-beta-compare"]
    for cid in ("alpha", "beta"):
        box = find(root, tag="input", attrs={"id": f"po-{cid}-compare"})
        assert find(root, tag="label", attrs={"for": f"po-{cid}-compare"}) is not None
        assert box.attrs["type"] == "checkbox"
        assert box.attrs["value"] == cid
        assert "disabled" not in box.attrs


def test_fallback_ids_never_collide():
    root = parse(render_many(rich_card(id=None), rich_card(id=None), rich_card(id=None)))
    card_ids = [n.attrs["id"] for n in find_all(root, cls="po-card")]
    assert len(card_ids) == 3 and len(set(card_ids)) == 3
    assert all(re.fullmatch(r"po-card-\d+", cid) for cid in card_ids)
    # and the whole page — ids, checkbox bindings included — stays duplicate-free
    all_ids = [n.attrs["id"] for n in walk(root) if n.attrs.get("id")]
    assert len(all_ids) == len(set(all_ids))


def test_checkbox_disabled_without_comparable_identity():
    root = render_card(rich_card(identity=None))
    box = find(root, tag="input")
    assert "disabled" in box.attrs  # html.parser yields valueless attrs as present
    assert find(root, tag="label").attrs["for"] == box.attrs["id"]


def test_no_compare_control_when_not_enabled():
    root = render_card(rich_card(compare_enabled=False))
    assert find_all(root, tag="input") == []
    assert find_all(root, cls="po-compare") == []
    assert "View setup" in text_of(find(root, cls="po-setup"))


def test_missing_setup_never_renders_a_fake_button():
    root = render_card(rich_card(setup_href=None, context=None))
    assert find_all(root, cls="po-setup") == []
    assert "Setup unavailable" in text_of(root)
    assert find_all(root, tag="button") == []


# ── 12. long content ─────────────────────────────────────────────────────────
def test_long_labels_parse_and_survive():
    name = "A" * 500
    ticker = "T" * 200
    price = "9" * 80
    root = render_card(rich_card(identity={"ticker": ticker, "name": {"en": name}},
                                 quote={"price": price, "change": "x" * 60}))
    assert name in text_of(find(root, cls="po-name"))
    assert ticker in text_of(find(root, cls="po-ticker"))
    assert price in text_of(find(root, cls="po-price"))
    assert len(text_of(find(root, cls="po-chg"))) == 60


# ── 13. stylesheet contract ──────────────────────────────────────────────────
CSS_TEXT = (TEMPLATES / STYLESHEET).read_text(encoding="utf-8")
CARD_SRC = (TEMPLATES / CARD).read_text(encoding="utf-8")
# Comments may legitimately NAME a banned construct (e.g. "no @import"); the
# contract scans the code, not the prose.
CSS_CODE = re.sub(r"/\*.*?\*/", "", re.sub(r"\{#.*?#\}", "", CSS_TEXT, flags=re.S), flags=re.S)
CARD_CODE = re.sub(r"\{#.*?#\}", "", CARD_SRC, flags=re.S)
_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")


def _css_rules():
    txt = re.sub(r"@media[^{]*", "", CSS_CODE)                # keep the rules
    return [(sel.strip(), body.strip()) for sel, body in _RULE.findall(txt)]


def test_stylesheet_scopes_every_rule_under_po():
    rules = _css_rules()
    assert len(rules) >= 30
    for sel, _body in rules:
        assert ".po" in sel, f"unscoped selector: {sel}"
        assert ":root" not in sel
        assert sel.strip() in ("html[data-theme=\"light\"] .po-card",) or ".po-" in sel or ".po-grid" in sel


def test_stylesheet_uses_theme_tokens_and_no_literal_colors():
    assert re.search(r"#[0-9a-fA-F]{3,8}\b", CSS_CODE) is None
    assert "@import" not in CSS_CODE and "url(" not in CSS_CODE
    for token in ("--panel", "--panel2", "--line", "--text", "--muted", "--pv-buy",
                  "--pv-near", "--pv-wait", "--pv-hold", "--pv-avoid", "--ink-up",
                  "--ink-down", "--ink-warn", "--ink-info", "--link", "--card-shadow",
                  "--info", "--r-ctl"):
        assert f"var({token}" in CSS_CODE, token


def test_stylesheet_grid_law():
    assert "grid-template-columns:minmax(0,1fr)" in CSS_CODE          # below 640 → 1
    for width, cols in (("640px", 2), ("960px", 3), ("1200px", 4)):
        assert f"@media (min-width:{width})" in CSS_CODE
        assert f"repeat({cols},minmax(0,1fr))" in CSS_CODE


def test_stylesheet_typography_and_shape_law():
    for size in ("font-size:12px", "font-size:14px", "font-size:18px", "font-size:24px"):
        assert size in CSS_CODE, size
    assert "font-variant-numeric:tabular-nums" in CSS_CODE
    assert "padding:16px" in CSS_CODE and "gap:12px" in CSS_CODE
    assert "var(--r-ctl,8px)" in CSS_CODE


def test_stylesheet_never_fixes_card_height_and_never_spacers():
    assert not re.search(r"min-height\s*:", CSS_CODE)
    heights = re.findall(r"(?<![-a-zA-Z])height:([^;}]*)", CSS_CODE)
    assert heights and set(h.strip() for h in heights) <= {"72px", "16px", "3px", "8px"}
    assert "margin-top:auto" not in CSS_CODE and "margin-bottom:auto" not in CSS_CODE
    assert "position:fixed" not in CSS_CODE


def test_light_treatment_uses_the_existing_shadow_token():
    assert "html[data-theme=\"light\"] .po-card" in CSS_TEXT
    light_rule = dict(_css_rules())["html[data-theme=\"light\"] .po-card"]
    assert "var(--card-shadow)" in light_rule


# ── 14. the component is presentation only ───────────────────────────────────
def test_card_template_ships_no_behaviour_and_no_network():
    low = CARD_CODE.lower()
    for banned in ("<script", "onclick", "|safe", "<style", "http://", "https://",
                   "fetch(", "xmlhttprequest", "eventlistener"):
        assert banned not in low, banned


def test_rendered_card_has_no_scripts_buttons_or_images():
    root = render_card(rich_card())
    for tag in ("script", "button", "img", "iframe", "style", "form"):
        assert find_all(root, tag=tag) == [], tag
