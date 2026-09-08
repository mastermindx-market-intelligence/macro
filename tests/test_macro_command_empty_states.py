"""Macro Command P3 — the six typed empty states (pin §G, spec §7)."""
from __future__ import annotations

from html import unescape
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from scripts import build_macro_suite_pages as builder

ROOT = Path(__file__).resolve().parents[1]


def _render_empty(state: dict) -> str:
    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=True,
        undefined=StrictUndefined,
    )
    tmpl = env.from_string(
        '{% import "_macro_command_figures.html.j2" as fig %}{{ fig.empty(state) }}'
    )
    return unescape(tmpl.render(state=state))


def test_e1_through_e6_render_the_spec_sentences_verbatim() -> None:
    e1 = _render_empty(builder._empty_state("e1"))
    assert 'data-mc-empty="e1"' in e1
    assert "We don't have this reading yet" in e1
    assert "该读数暂不可用" in e1
    assert "has not published a dated reading" in e1
    assert "Checked again in tonight's update" in e1

    e2 = _render_empty(builder._empty_state("e2"))
    assert 'data-mc-empty="e2"' in e2
    assert "Today's number didn't arrive" in e2
    assert "昨天的数字当作今天的" in e2
    assert "mc-empty-next" not in e2  # unlock/next merged into unlock

    e3 = _render_empty(builder._empty_state("e3"))
    assert "We can't show the change yet" in e3
    assert "任何箭头都会是臆造的" in e3

    e4 = _render_empty(builder._empty_state("e4"))
    assert "Not open yet" in e4
    assert "尚未开放" in e4
    assert "nothing you need to do" in e4

    e5 = _render_empty(builder._empty_state("e5", cta_href="macro_rates_curves.html"))
    assert "This section didn't load" in e5
    assert 'href="macro_rates_curves.html"' in e5
    assert "Reload the page, or open the full workspace" in e5

    e6 = _render_empty(builder._empty_state("e6", plan="Pro"))
    assert "Included in a higher plan" in e6
    assert "本板块属于Pro。" in e6
    assert 'href="plans.html"' in e6
    assert "mc-empty-next" not in e6


def test_e2_and_e6_are_never_a_bad_tone() -> None:
    """A missing input / paywall is not a market verdict (pin §G, §3.4)."""
    for state_id, kwargs in (("e2", {}), ("e6", {"plan": "Pro"})):
        html = _render_empty(builder._empty_state(state_id, **kwargs))
        assert "mq-tone-bad" not in html
        assert 'data-mc-empty="' + state_id + '"' in html


def test_empty_macro_omits_optional_rows_that_are_none() -> None:
    e3 = builder._empty_state("e3")
    assert e3["unlock"] is None
    html = _render_empty(e3)
    assert "mc-empty-unlock" not in html
    assert "mc-empty-cta" not in html


def test_e6_interpolates_the_plan_name_in_both_languages() -> None:
    state = builder._empty_state("e6", plan="Research")
    assert "Research" in state["why"]["en"]
    assert "Research" in state["why"]["zh"]
    assert "{plan}" not in state["why"]["en"]
