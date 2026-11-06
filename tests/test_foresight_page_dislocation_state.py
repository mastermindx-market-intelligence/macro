"""D03 T35: an unavailable source is not a confirmed closed entry window.

Full-template renders only; no engine, live data, network or repository site
writes. F04's missing producer reason/clock remains an explicit limitation.
"""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader


ROOT = Path(__file__).resolve().parents[1]
_MISSING = object()


def _render(dislocation=_MISSING):
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")),
                      autoescape=True)
    context = dict(
        cascade={"sizing": None, "demand_pool": None},
        themes=[], stage_counts={}, stage_order=[], demand_pool=None,
        track={"foresight": 0, "bottleneck": 0, "glut": 0, "revisions": 0,
               "guidance": 0, "emergence": 0, "subsector": 0, "recent": []},
        grade=None, emergence=None, subsectors=None, convergence=None,
        power=None, analyst=None, monitor=None, health=None,
        asof="2026-11-04", generated_utc="2026-11-04 00:00 UTC",
        nav_prefix="", active_section="research", active_page="foresight",
    )
    if dislocation is not _MISSING:
        context["dislocation"] = dislocation
    return env.get_template("foresight.html.j2").render(**context)


class _GateHTML(HTMLParser):
    """Retain exactly the gate, not similarly worded content elsewhere."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.depth = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if self.depth or "fx-gate" in dict(attrs).get("class", "").split():
            self.depth += 1
            self.parts.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        if self.depth:
            self.parts.append(f"</{tag}>")
            self.depth -= 1

    def handle_startendtag(self, tag, attrs):
        if self.depth:
            self.parts.append(self.get_starttag_text())

    def handle_data(self, data):
        if self.depth:
            self.parts.append(data)

    def handle_entityref(self, name):
        if self.depth:
            self.parts.append(f"&{name};")

    def handle_charref(self, name):
        if self.depth:
            self.parts.append(f"&#{name};")


def _gate(html):
    parser = _GateHTML()
    parser.feed(html)
    assert parser.parts, "entry-window component missing"
    return "".join(parser.parts)


@pytest.mark.parametrize("source", [
    None, {}, [], "", "unavailable", False, 1,
    {"active": None}, {"active": "false"}, {"active": 0},
    {"verdict": "buyable_washout"},
])
def test_missing_or_malformed_projection_is_unavailable(source):
    gate = _gate(_render(source))
    assert 'data-state="unavailable"' in gate
    assert "Unavailable — no dislocation read" in gate
    assert "暂不可用——缺少错位判读" in gate
    assert "source reason and observation time are unavailable" in gate
    assert "数据源未提供原因或观测时间" in gate
    assert "Closed —" not in gate
    assert "关闭——" not in gate
    assert "Open —" not in gate
    assert "Detection runs continuously" not in gate
    assert "检测持续运行" not in gate


def test_absent_template_input_is_unavailable():
    gate = _gate(_render())
    assert 'data-state="unavailable"' in gate
    assert "Unavailable — no dislocation read" in gate
    assert "Closed —" not in gate


@pytest.mark.parametrize("source", [
    {"active": False, "verdict": None},
    {"active": False, "verdict": "neutral"},
    {"active": False, "verdict": "watch", "headline": "Source says wait"},
])
def test_explicit_closed_projection_keeps_its_meaning(source):
    gate = _gate(_render(source))
    assert 'data-state="closed"' in gate
    assert "Closed — no dislocation yet" in gate
    assert "关闭——暂无错位" in gate
    assert "Unavailable —" not in gate
    assert "Open —" not in gate


@pytest.mark.parametrize("source", [
    {"active": True, "verdict": None},
    {"active": True, "verdict": "neutral"},
    {"active": False, "verdict": "buyable_washout"},
])
def test_known_open_including_verdict_driven_open_is_preserved(source):
    gate = _gate(_render(source))
    assert 'data-state="open"' in gate
    assert "Open — a dislocation to buy into" in gate
    assert "开启——出现可买入的错位" in gate
    assert "Unavailable —" not in gate
    assert "Closed —" not in gate


@pytest.mark.parametrize("active", [False, True])
def test_supplied_headline_is_preserved_and_escaped(active):
    gate = _gate(_render({"active": active, "headline": '<img src=x onerror="bad()">'}))
    assert "&lt;img" in gate and "&gt;" in gate
    assert "<img" not in gate
    assert "onerror=&#34;bad()&#34;" in gate


def test_malformed_projection_cannot_smuggle_a_live_headline():
    gate = _gate(_render({"headline": "LIVE_WINDOW_OPEN", "active": "true"}))
    assert 'data-state="unavailable"' in gate
    assert "LIVE_WINDOW_OPEN" not in gate


@pytest.mark.parametrize("active", [False, True])
@pytest.mark.parametrize("verdict", [True, 0, {}, []])
def test_nontext_verdict_invalidates_the_projection(active, verdict):
    gate = _gate(_render({"active": active, "verdict": verdict,
                          "headline": "UNTRUSTED_HEADLINE"}))
    assert 'data-state="unavailable"' in gate
    assert "UNTRUSTED_HEADLINE" not in gate
    assert "Closed —" not in gate and "Open —" not in gate


@pytest.mark.parametrize("active", [False, True])
@pytest.mark.parametrize("headline", [None, 0, {"unexpected": "headline"}, [], "  "])
def test_nontext_or_blank_headline_uses_known_state_fallback(active, headline):
    gate = _gate(_render({"active": active, "headline": headline}))
    assert f'data-state="{"open" if active else "closed"}"' in gate
    expected = "Review the source and timing" if active else "The supplied read shows no dislocation"
    assert expected in gate
    assert "unexpected" not in gate


def test_touched_gate_has_no_accent_stripe_or_emoji_state_icon():
    source = (ROOT / "templates" / "foresight.html.j2").read_text(encoding="utf-8")
    gate_css = source[source.index("/* entry-gate banner */"):source.index("/* ---------- section chrome")]
    assert "border-left" not in gate_css
    assert "font-size:12px" in gate_css
    assert "font-size:14px" in gate_css
    for state in (None, {"active": False}, {"active": True}):
        gate = _gate(_render(state))
        assert "ic-svg" in gate
        assert 'aria-hidden="true"' in gate
        assert "✅" not in gate and "⏳" not in gate
