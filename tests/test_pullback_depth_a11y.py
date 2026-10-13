"""Accessibility invariants for the measured-pullback "Pullback underway" section.

Every state the fragment can produce from SYNTHETIC observations is rendered the
way the product renders it — through lib.pullback_depth.present (via the US and
CN adapters) for the chart states, and through the shipped US modal and CN
dialog shells for the leading states — then parsed with stdlib html.parser and
checked against the section's accessibility contract:

A1 unique ids; every aria-labelledby / aria-describedby / aria-controls / for=
   reference resolves to an id in the same render
A2 every <time> carries a datetime that parses; timestamps carry an explicit
   UTC offset (bare dates excepted)
A3 the chart has a non-empty accessible name; decorative svgs are aria-hidden
   and a non-hidden text alternative stands beside them
A4 the price-history table is named and its header cells declare scope
A5 every <details> has a direct, non-empty <summary>
A6 no positive tabindex; no interactive element inside aria-hidden
A7 the "Estimate unavailable" block carries both languages, no figure, and is
   not hidden
A8 every metric value has an adjacent text label (never colour or icon alone)
A9 heading levels inside the section never skip

The settled-close stamp omits ``<time>`` when asof is missing, and the
price-history table carries a caption plus ``scope`` on its header cells.
"""
from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path
import re

import pytest

from lib import cn_pullback_observation as cn_adapter
from lib import us_pullback_observation as us_adapter
from tests.test_risk_radar_pullback_depth_template import (
    native_view,
    render as render_fragment,
)

ROOT = Path(__file__).resolve().parents[1]

ACTIVE_PHASES = ("underway", "stabilizing", "recovering")

# Synthetic owner paths (percent drawdowns). The raw series may reach back
# before the retained peak; the presenter slices it to the episode window.
RAW_PATH = {
    "dates": ["2026-09-11", "2026-09-14", "2026-09-16", "2026-09-21",
              "2026-09-24", "2026-09-29", "2026-09-30"],
    "vals": [-2.0, 0.0, -2.1, -7.4, -5.2, -6.9, -6.8],
}
SHORT_PATH = {"dates": ["2026-09-14", "2026-09-21", "2026-09-30"],
              "vals": [0.0, -7.4, -6.8]}
RECLAIM_PATH = {"dates": ["2026-09-14", "2026-09-21", "2026-09-24", "2026-09-30"],
                "vals": [0.0, -7.4, -3.1, 0.0]}
EVIDENCE = {
    "onset_session": "2026-09-16",
    "low_session": "2026-09-21",
    "no_new_low_closes": 4,
    "loss_recovered_pct": 8.11,
    "below_20_close_average": True,
    "price_transitions": [
        {"date": "2026-09-16", "phase": "underway"},
        {"date": "2026-09-24", "phase": "stabilizing"},
        {"date": "2026-09-29", "phase": "recovering"},
    ],
    "history_gap_count": 2,
}


def _observation(market, phase, *, path=None, **fields):
    """A synthetic native view, presented by the market's real adapter."""
    view = native_view(market)
    view["phase"] = phase
    view["observation"]["phase"] = phase
    view["observation"]["active"] = phase in ACTIVE_PHASES
    if phase in ("monitoring", "developing"):
        view["observation"]["low_close"] = None
    view["observation"].update(fields)
    if path is None:
        return view
    view["observation"]["price_path"] = path
    present = us_adapter.present if market == "us" else cn_adapter.present
    return present(view["observation"])


def _uncovered(market, phase="underway", **fields):
    """A presented view whose history on record supports no window at all."""
    view = _observation(market, phase, **fields)
    present = us_adapter.present if market == "us" else cn_adapter.present
    return present(view["observation"])


def _us_dialog_html(view):
    from tests.test_macro_risk_dialog import _render, _vm

    vm = _vm()
    vm["us_pullback_view"] = view
    return _render(vm=vm, mode="macro")


def _cn_dialog_html(view):
    from jinja2 import Environment, FileSystemLoader

    from tests.test_risk_radar_dlg_partial import _RD

    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=False)
    tpl = env.from_string(
        '{% import "_risk_radar_dlg.html.j2" as rrd %}'
        "{{ rrd.risk_radar_dlg(mkt, rd, none, ctx) }}"
    )
    ctx = {"title_en": "China Risk Radar", "title_zh": "中国风险雷达",
           "pullback_view": view}
    return tpl.render(mkt="cn", rd=_RD, ctx=ctx)


def _fragment_state(market, phase, *, path=None, **fields):
    return lambda: render_fragment(
        _observation(market, phase, path=path, **fields), market)


def _neutral_state(market):
    """Current assessment, no chart provenance at all: the neutral copy."""
    def build():
        view = native_view(market)
        view["observation"]["valid_until"] = "2026-10-01T09:00:00"  # naive: no deadline row
        view["detail_chart_html"] = ""
        return render_fragment(view, market)
    return build


def _unavailable_state(market, view):
    return lambda: render_fragment(view, market)


def _unqualified(market, **fields):
    view = native_view(market)
    view["observation"].update(fields)
    return view


def _dialog_state(kind, market, phase):
    def build():
        view = _observation(market, phase, path=RAW_PATH, **EVIDENCE)
        if kind == "us":
            return _us_dialog_html(view)
        return _cn_dialog_html(view)
    return build


def _states():
    return {
        # Chart drawn from the presenter's checked window, both markets.
        "us-underway-chart": ("us", _fragment_state("us", "underway", path=RAW_PATH, **EVIDENCE)),
        "cn-underway-chart": ("cn", _fragment_state("cn", "underway", path=RAW_PATH, **EVIDENCE)),
        "us-stabilizing-chart": ("us", _fragment_state("us", "stabilizing", path=RAW_PATH, **EVIDENCE)),
        "cn-stabilizing-chart": ("cn", _fragment_state("cn", "stabilizing", path=RAW_PATH, **EVIDENCE)),
        "us-recovering-chart": ("us", _fragment_state("us", "recovering", path=RAW_PATH, **EVIDENCE)),
        "cn-recovering-chart": ("cn", _fragment_state("cn", "recovering", path=RAW_PATH, **EVIDENCE)),
        # A close back above the retained high stays measurable at the 0% line.
        "us-recovering-reclaim": ("us", _fragment_state(
            "us", "recovering", path=RECLAIM_PATH, low_session="2026-09-21", close=101.0)),
        # Episode phases outside the repair watch, and the repaired phase.
        "cn-monitoring-chart": ("cn", _fragment_state("cn", "monitoring", path=RAW_PATH)),
        "cn-repaired-chart": ("cn", _fragment_state(
            "cn", "repaired", path=RAW_PATH, low_session="2026-09-21")),
        # Chart withheld: too few closes, and a history that supports no window.
        "us-underway-short": ("us", _fragment_state(
            "us", "underway", path=SHORT_PATH, low_session="2026-09-21")),
        "cn-underway-short": ("cn", _fragment_state(
            "cn", "underway", path=SHORT_PATH, low_session="2026-09-21")),
        "us-underway-uncovered": ("us", lambda: render_fragment(
            _uncovered("us", low_session="2026-09-21"), "us")),
        "cn-underway-uncovered": ("cn", lambda: render_fragment(
            _uncovered("cn", low_session="2026-09-21"), "cn")),
        "cn-monitoring-evidence": ("cn", lambda: render_fragment(
            _uncovered("cn", "monitoring", **EVIDENCE), "cn")),
        # Current but with no chart provenance at all: the neutral copy.
        "us-underway-neutral": ("us", _neutral_state("us")),
        # Unqualified observations: the "Price update needed" shape (also the
        # shape the client expiry owner stamps into an expired section).
        "unavailable-none": ("cn", _unavailable_state("cn", None)),
        "unavailable-empty": ("us", _unavailable_state("us", {})),
        "unavailable-source": ("cn", _unavailable_state(
            "cn", _unqualified("cn", available=False, quality="source_unavailable"))),
        "unavailable-delayed": ("us", _unavailable_state(
            "us", _unqualified("us", quality="delayed"))),
        # Leading states inside the shipped dialog shells.
        "dlg-us-underway": ("us", _dialog_state("us", "us", "underway")),
        "dlg-us-stabilizing": ("us", _dialog_state("us", "us", "stabilizing")),
        "dlg-us-recovering": ("us", _dialog_state("us", "us", "recovering")),
        "dlg-cn-underway": ("cn", _dialog_state("cn", "cn", "underway")),
        "dlg-cn-recovering": ("cn", _dialog_state("cn", "cn", "recovering")),
    }


STATES = _states()
ALL_STATES = tuple(STATES)
UNAVAILABLE_STATES = (
    "unavailable-none", "unavailable-empty", "unavailable-source", "unavailable-delayed")
CHART_STATES = tuple(
    label for label in ALL_STATES
    if label not in UNAVAILABLE_STATES
    and label not in ("us-underway-short", "cn-underway-short", "us-underway-uncovered",
                      "cn-underway-uncovered", "cn-monitoring-evidence", "us-underway-neutral"))
TABLE_STATES = CHART_STATES
CURRENT_STATES = tuple(label for label in ALL_STATES if label not in UNAVAILABLE_STATES)


# --------------------------------------------------------------------------- #
# Minimal DOM over stdlib html.parser (no bs4/lxml dependency here).
# --------------------------------------------------------------------------- #
VOID = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
})
BARE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REF_ATTRS = ("aria-labelledby", "aria-describedby", "aria-controls")
INTERACTIVE = ("a", "button", "summary")


class Element:
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag, attrs, parent):
        self.tag = tag
        self.attrs = attrs
        self.children = []
        self.parent = parent

    def iter(self):
        yield self
        for child in self.children:
            if isinstance(child, Element):
                yield from child.iter()

    def text(self):
        parts = []

        def walk(node):
            for child in node.children:
                if isinstance(child, Element):
                    walk(child)
                else:
                    parts.append(child)

        walk(self)
        return "".join(parts)


class _Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Element("#root", {}, None)
        self.stack = [self.root]

    def _append(self, tag, attrs, *, push):
        clean = {}
        for key, value in attrs:  # HTML: the first occurrence of an attribute wins.
            clean.setdefault(key, value if value is not None else "")
        node = Element(tag, clean, self.stack[-1])
        self.stack[-1].children.append(node)
        if push and tag not in VOID:
            self.stack.append(node)

    def handle_starttag(self, tag, attrs):
        self._append(tag, attrs, push=True)

    def handle_startendtag(self, tag, attrs):
        self._append(tag, attrs, push=False)

    def handle_endtag(self, tag):
        for depth in range(len(self.stack) - 1, 0, -1):
            if self.stack[depth].tag == tag:
                del self.stack[depth:]
                return

    def handle_data(self, data):
        if data:
            self.stack[-1].children.append(data)


def parse(html):
    tree = _Tree()
    tree.feed(html)
    tree.close()
    return tree.root


def classes(node):
    return set((node.attrs.get("class") or "").split())


def is_hidden(node):
    return (node.attrs.get("aria-hidden") or "").strip().lower() == "true"


def in_hidden_subtree(node):
    while node is not None and node.tag != "#root":
        if is_hidden(node):
            return True
        node = node.parent
    return False


def accessible_name(node):
    """aria-labelledby first, then aria-label — the HTML-AAM name algorithm."""
    labelledby = (node.attrs.get("aria-labelledby") or "").split()
    if labelledby:
        root = node
        while root.parent is not None:
            root = root.parent
        parts = []
        for ref in labelledby:
            for el in root.iter():
                if el is not node and el.attrs.get("id") == ref:
                    parts.append(el.text())
                    break
        return " ".join(parts)
    return node.attrs.get("aria-label") or ""


@lru_cache(maxsize=None)
def built(label):
    """(whole render, section element) for one rendered state."""
    _market, build = STATES[label]
    root = parse(build())
    hits = [el for el in root.iter()
            if el.tag == "section" and {"rrp", "pbx"} <= classes(el)]
    assert len(hits) == 1, f"{label}: expected exactly one measured section"
    return root, hits[0]


# Unavailable renders with no asof at all. The settled close is a plain em dash
# there, so those states have no empty datetime to reject.
NO_ASOF_STATES = ("unavailable-none", "unavailable-empty")


def a2_states():
    return list(ALL_STATES)


def a4_states():
    return list(TABLE_STATES)


# --------------------------------------------------------------------------- #
# A1 — ids and references
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("label", ALL_STATES)
def test_a1_ids_are_unique_within_the_section(label):
    _, section = built(label)
    seen = set()
    for node in section.iter():
        if "id" in node.attrs:
            assert node.attrs["id"] not in seen, f"duplicate id {node.attrs['id']!r}"
            seen.add(node.attrs["id"])


@pytest.mark.parametrize("label", ALL_STATES)
def test_a1_aria_and_label_references_resolve_in_the_same_render(label):
    root, section = built(label)
    ids = {node.attrs["id"] for node in root.iter() if "id" in node.attrs}
    for node in section.iter():
        for attr in REF_ATTRS:
            for ref in (node.attrs.get(attr) or "").split():
                assert ref in ids, f"{attr} points at #{ref}, absent from this render"
        target = node.attrs.get("for")
        if target is not None:
            assert target in ids, f"for= points at #{target}, absent from this render"


# --------------------------------------------------------------------------- #
# A2 — <time> elements
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("label", a2_states())
def test_a2_time_elements_carry_parseable_datetimes(label):
    _, section = built(label)
    times = [node for node in section.iter() if node.tag == "time"]
    # A missing asof is a plain em dash, not a <time datetime="">. Every time
    # that is present still has to carry a parseable datetime.
    for node in times:
        stamp = node.attrs.get("datetime")
        assert stamp, f'<time> without a datetime attribute: {node.attrs}'
        parsed = datetime.fromisoformat(stamp)
        if not BARE_DATE.match(stamp):
            assert parsed.tzinfo is not None and parsed.utcoffset() is not None, (
                f'<time datetime="{stamp}"> is a timestamp without an explicit UTC offset')


def test_a2_zoned_deadline_and_bare_asof_pair_in_the_current_render():
    root, section = built("cn-underway-chart")
    stamps = [node.attrs.get("datetime") for node in section.iter() if node.tag == "time"]
    assert stamps == ["2026-09-30", "2026-10-01T09:00:00+00:00"]


def test_a2_naive_valid_until_renders_no_timestamp_time():
    _, section = built("us-underway-neutral")
    stamps = [node.attrs.get("datetime") for node in section.iter() if node.tag == "time"]
    assert stamps == ["2026-09-30"]


# --------------------------------------------------------------------------- #
# A3 — the chart's name and its text alternative
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("label", CHART_STATES)
def test_a3_chart_has_a_name_and_its_decorative_svg_is_hidden(label):
    market, _ = STATES[label]
    _, section = built(label)
    figures = [node for node in section.iter()
               if node.tag == "figure" and "img" in (node.attrs.get("role") or "").split()]
    assert len(figures) == 1, "the drawn chart is exactly one role=img figure"
    name = accessible_name(figures[0])
    assert name.strip(), "the chart figure has an empty accessible name"
    needle = "SPY" if market == "us" else "Shanghai Composite"
    assert needle in name and "drawdown" in name, (
        f"chart name does not read as this market's drawdown: {name!r}")
    svgs = [node for node in section.iter() if node.tag == "svg"]
    assert svgs, "the drawn chart carries an svg body"
    for svg in svgs:
        assert is_hidden(svg), "an unnamed svg must be aria-hidden"
    holders = [node for node in section.iter() if "rrp-chart" in classes(node)]
    assert holders and is_hidden(holders[0]), "the chart container is decorative (aria-hidden)"
    # The visible text alternative stands beside the decorative chart.
    caption = [node for node in section.iter() if "rrp-chart-caption" in classes(node)]
    assert caption and caption[0].text().strip() and not in_hidden_subtree(caption[0])
    table = [node for node in section.iter()
             if node.tag == "table" and not in_hidden_subtree(node)]
    assert table, "the history table is the chart's text alternative"


# --------------------------------------------------------------------------- #
# A4 — the price-history table
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("label", TABLE_STATES)
def test_a4_history_table_structure_uses_th_and_td(label):
    _, section = built(label)
    holders = [node for node in section.iter() if "rrp-history" in classes(node)]
    assert len(holders) == 1
    tables = [node for node in holders[0].iter() if node.tag == "table"]
    assert len(tables) == 1
    heads = [node for node in tables[0].iter() if node.tag == "thead"]
    assert len(heads) == 1
    header_cells = [node for node in heads[0].iter() if node.tag == "th"]
    assert header_cells, "header cells must be <th>"
    for cell in header_cells:
        assert cell.text().strip()
    bodies = [node for node in tables[0].iter() if node.tag == "tbody"]
    assert len(bodies) == 1
    for node in bodies[0].iter():
        assert node.tag != "th", "data cells must not be header cells"


@pytest.mark.parametrize("label", a4_states())
def test_a4_history_table_has_a_caption_or_accessible_name(label):
    _, section = built(label)
    holder = next(node for node in section.iter() if "rrp-history" in classes(node))
    table = next(node for node in holder.iter() if node.tag == "table")
    captions = [child for child in table.children
                if isinstance(child, Element) and child.tag == "caption"]
    name = accessible_name(table)
    assert captions or name.strip(), (
        "the price-history table has neither a <caption> nor an accessible name")


@pytest.mark.parametrize("label", a4_states())
def test_a4_history_table_header_cells_declare_scope(label):
    _, section = built(label)
    holder = next(node for node in section.iter() if "rrp-history" in classes(node))
    table = next(node for node in holder.iter() if node.tag == "table")
    cells = [node for node in table.iter() if node.tag == "th"]
    assert cells
    missing = [cell for cell in cells if not (cell.attrs.get("scope") or "").strip()]
    assert not missing, (
        "header cells without scope=: "
        + ", ".join(cell.text().strip() for cell in missing))


# --------------------------------------------------------------------------- #
# A5 — disclosures
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("label", ALL_STATES)
def test_a5_every_details_has_a_direct_non_empty_summary(label):
    _, section = built(label)
    disclosures = [node for node in section.iter() if node.tag == "details"]
    assert disclosures, "the section carries its method disclosures"
    for node in disclosures:
        summaries = [child for child in node.children
                     if isinstance(child, Element) and child.tag == "summary"]
        assert len(summaries) == 1, "a <details> needs exactly one direct <summary>"
        assert summaries[0].text().strip(), "the summary must carry visible text"


# --------------------------------------------------------------------------- #
# A6 — focus order and hidden interactive elements
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("label", ALL_STATES)
def test_a6_no_positive_tabindex(label):
    _, section = built(label)
    for node in section.iter():
        if "tabindex" in node.attrs:
            value = node.attrs["tabindex"].strip()
            assert value.lstrip("-").isdigit(), f"non-integer tabindex {value!r}"
            assert int(value) <= 0, f"tabindex={value} steals the tab order"


@pytest.mark.parametrize("label", ALL_STATES)
def test_a6_no_interactive_element_is_hidden(label):
    _, section = built(label)
    for node in section.iter():
        if node.tag in INTERACTIVE:
            assert not in_hidden_subtree(node), (
                f"interactive <{node.tag}> inside an aria-hidden subtree")


# --------------------------------------------------------------------------- #
# A7 — the unavailable-estimate block
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("label", ALL_STATES)
def test_a7_forecast_block_names_both_languages_without_figures(label):
    _, section = built(label)
    blocks = [node for node in section.iter() if "rrp-forecast" in classes(node)]
    assert len(blocks) == 1
    block = blocks[0]
    assert block.attrs.get("data-forecast-status") == "unavailable"
    assert not in_hidden_subtree(block), "the estimate block must stay exposed"
    text = block.text()
    assert "Estimate unavailable" in text and "估计暂不可用" in text
    figures = sorted({ch for ch in text if ch.isdigit() or ch == "%"})
    assert not figures, f"digits/percent leaked into the estimate block: {figures}"
    placeholders = [node for node in block.iter()
                    if node.tag == "strong" and node.text().strip() == "—"]
    assert placeholders, "each pending figure prints its — placeholder"


# --------------------------------------------------------------------------- #
# A8 — metric values have text labels
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("label", CURRENT_STATES)
def test_a8_metric_values_have_adjacent_text_labels(label):
    _, section = built(label)
    metrics = [node for node in section.iter() if "data-metric" in node.attrs]
    assert metrics, "the current assessment prints its measured metrics"
    kinds = {node.attrs["data-metric"] for node in metrics}
    assert {"current", "worst", "rebound", "age"} <= kinds
    for node in metrics:
        assert node.text().strip(), f"[data-metric={node.attrs['data-metric']}] prints no value"
        if node.attrs["data-metric"] == "age":
            words = re.sub(r"[\d\s%.,−\-+]+", "", node.text(), flags=re.UNICODE)
            assert words.strip(), "the age row must label its count in words"
        else:
            label = next((el for el in node.parent.iter()
                          if "rrp-label" in classes(el)), None)
            assert label is not None, "each metric tile carries a text label"
            assert label.text().strip() and not in_hidden_subtree(label)


# --------------------------------------------------------------------------- #
# A9 — heading order
# --------------------------------------------------------------------------- #
def _headings(section):
    return [node for node in section.iter() if re.fullmatch(r"h[1-6]", node.tag)]


@pytest.mark.parametrize("label", ALL_STATES)
def test_a9_heading_levels_never_skip(label):
    _, section = built(label)
    levels = [int(node.tag[1]) for node in _headings(section)]
    assert levels, "the section carries its own headings"
    assert levels[0] == 2, f"the section starts at h{levels[0]}"
    for prev, nxt in zip(levels, levels[1:]):
        assert nxt <= prev + 1, f"heading level skipped h{prev} -> h{nxt}"


@pytest.mark.parametrize("label", ALL_STATES)
def test_heading_pairing_is_bilingual(label):
    _, section = built(label)
    heading = _headings(section)[0]
    en = [node for node in heading.iter() if "l-en" in classes(node)]
    zh = [node for node in heading.iter() if "l-zh" in classes(node)]
    assert en and en[0].text().strip(), "the English heading string is missing"
    assert zh and zh[0].text().strip(), "the Chinese heading string is missing"


# --------------------------------------------------------------------------- #
# The expiry receipt stays a status region in every state.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("label", ALL_STATES)
def test_expiry_notice_is_a_status_region(label):
    _, section = built(label)
    notices = [node for node in section.iter() if "pbx-expiry" in classes(node)]
    assert len(notices) == 1
    assert notices[0].attrs.get("role") == "status"
    assert notices[0].text().strip()
