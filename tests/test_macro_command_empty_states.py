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


def test_one_null_voice_drops_caption_and_matches_stance_for_e1_through_e6() -> None:
    """M2: every empty state's title is the stance; caption is not the explanation."""
    from lib import macro_suite_labels as L
    for empty_id in ("e1", "e2", "e3", "e4", "e5", "e6"):
        kwargs = {}
        if empty_id == "e5":
            kwargs["cta_href"] = "macro_rates_curves.html"
        if empty_id == "e6":
            kwargs["plan"] = "Pro"
        empty = builder._empty_state(empty_id, **kwargs)
        voice = builder._apply_empty_voice(empty)
        assert voice is not None, empty_id
        assert voice["text"]["en"] == L.EMPTY_STATES[empty_id]["title"]["en"]
        assert voice["text"]["zh"] == L.EMPTY_STATES[empty_id]["title"]["zh"]
        html = _render_empty(empty)
        assert "Each row shows the last two readings" not in html
        assert empty["title"]["en"] in html


def test_empty_states_have_no_repeated_visible_string() -> None:
    """E-M4: no two visible text nodes inside one empty state are equal."""
    from html.parser import HTMLParser

    class _Visible(HTMLParser):
        def __init__(self, lang: str) -> None:
            super().__init__()
            self.lang = lang
            self._skip = 0
            self._keep = 0
            self.texts: list[str] = []

        def handle_starttag(self, tag, attrs):
            cls = dict(attrs).get("class", "")
            if self.lang == "en" and "l-zh" in cls.split():
                self._skip += 1
            elif self.lang == "zh" and "l-en" in cls.split():
                self._skip += 1
            elif self._skip:
                self._skip += 1

        def handle_endtag(self, tag):
            if self._skip:
                self._skip -= 1

        def handle_data(self, data):
            if self._skip:
                return
            text = " ".join(data.split())
            if text:
                self.texts.append(text)

    for empty_id in ("e1", "e2", "e3", "e4", "e5", "e6"):
        kwargs: dict = {}
        if empty_id == "e5":
            kwargs["cta_href"] = "macro_rates_curves.html"
        if empty_id == "e6":
            kwargs["plan"] = "Pro"
        html = _render_empty(builder._empty_state(empty_id, **kwargs))
        for lang in ("en", "zh"):
            parser = _Visible(lang)
            parser.feed(html)
            assert parser.texts, (empty_id, lang)
            assert len(parser.texts) == len(set(parser.texts)), (
                empty_id, lang, parser.texts)


def test_e1_stance_and_slot_are_the_same_sentence() -> None:
    """m-a: E1 says one cause — stance title == slot title."""
    empty = builder._empty_state("e1")
    voice = builder._apply_empty_voice(empty)
    assert voice["text"]["en"] == empty["title"]["en"]
    assert voice["text"]["en"] == "We don't have this reading yet"
    assert "could not be read today" not in voice["text"]["en"]
