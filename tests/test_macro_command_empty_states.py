"""Macro Command P3 — the six typed empty states (pin §G, spec §7)."""
from __future__ import annotations

import re
from html import unescape
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from lib import macro_suite_labels as L
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
    assert "No reading arrived today." in e2
    assert "今天没有新的读数。" in e2
    assert "Today's number didn't arrive" not in e2
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
    assert "包含在更高方案中" in e6
    assert "This section is included in a higher plan." not in e6
    assert "本板块包含在更高方案中。" not in e6
    assert "本板块属于Pro。" in e6
    assert "The reading is available on upgrade." in e6
    assert "升级后可查看该读数。" in e6
    assert "See it with an upgrade." in e6
    assert "升级即可查看。" in e6
    assert "Upgrade to see it" in e6
    assert "查看升级方案" in e6
    assert 'href="plans.html"' in e6
    assert e6.count("Upgrade to see it") == 1
    assert e6.count("查看升级方案") == 1
    assert "mc-empty-next" not in e6
    assert "包含于更高级别方案" not in e6
    assert "升级后即可查看" not in e6


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
    """MINOR-E6: the empty card speaks; section stance is suppressed."""
    for empty_id in ("e1", "e2", "e3", "e4", "e5", "e6"):
        kwargs = {}
        if empty_id == "e5":
            kwargs["cta_href"] = "macro_rates_curves.html"
        if empty_id == "e6":
            kwargs["plan"] = "Pro"
        empty = builder._empty_state(empty_id, **kwargs)
        voice = builder._apply_empty_voice(empty)
        assert voice is None, empty_id
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


def test_empty_card_hides_title_when_the_panel_already_has_the_stance() -> None:
    """M6: one null voice per section — stance line OR card title, not both."""
    src = (ROOT / "templates" / "_macro_command_fragment.html.j2").read_text(
        encoding="utf-8")
    assert "fig.empty(s.empty, hide_title=true)" in src
    assert "fig.empty(tab.empty, hide_title=true)" in src
    isolated = _render_empty(builder._empty_state("e2"))
    assert "No reading arrived today" in isolated or "Today's number didn't arrive" in isolated


def test_e1_stance_and_slot_are_the_same_sentence() -> None:
    """MINOR-E6: E1's title lives on the card; stance is not a second copy."""
    empty = builder._empty_state("e1")
    voice = builder._apply_empty_voice(empty)
    assert voice is None
    html = _render_empty(empty)
    assert "We don't have this reading yet" in html
    assert html.count("We don't have this reading yet") == 1
    assert "could not be read today" not in html


def test_e6_suite_vocabulary_is_pinned() -> None:
    """E6 ZH TITLE UNIFICATION: one vocabulary across the suite."""
    from lib import macro_suite_labels as L
    spec = L.EMPTY_STATES["e6"]
    assert spec["title"] == {
        "en": "Included in a higher plan", "zh": "包含在更高方案中"}
    assert spec["stance"] == {
        "en": "The reading is available on upgrade.",
        "zh": "升级后可查看该读数。"}
    assert spec["unlock"] == {
        "en": "See it with an upgrade.", "zh": "升级即可查看。"}
    assert spec["cta_label"] == {
        "en": "Upgrade to see it", "zh": "查看升级方案"}
    assert spec["why"]["en"] == "This section is part of {plan}."
    assert spec["why"]["zh"] == "本板块属于{plan}。"


def test_hydrated_empty_section_has_no_repeated_sentence() -> None:
    """MINOR-E6: no visible sentence appears twice in one section."""
    from html.parser import HTMLParser

    class _Visible(HTMLParser):
        def __init__(self, lang: str) -> None:
            super().__init__()
            self.lang = lang
            self._skip = 0
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

    data_root = ROOT / "site" / "macrodata"
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "site"
        builder.render(
            ROOT, data_root=data_root, out_dir=dest,
            page_built_at="2026-09-06T00:00:00Z")
        hub = dest.joinpath("macro_monetary.html").read_text(encoding="utf-8")
        frag = dest.joinpath("macro", "fragments", "rates.html").read_text(
            encoding="utf-8")
        match = re.search(
            r'<section class="mc-panel" id="rates".*?(?=<section class="mc-panel"|</main>)',
            hub, re.S)
        assert match
        panel = match.group(0)
        composed = (
            panel.replace(
                '<p class="mc-figure-pending" hidden data-mc-pending>',
                '<p class="mc-figure-pending" hidden data-mc-pending hidden-skip>',
            ).replace(
                '<p class="mc-figure-offer" data-mc-offer>',
                "<div>" + frag + '</div><p class="mc-figure-offer" hidden data-mc-offer>',
            )
        )
        text = unescape(composed)
        for sentence in (
            "No reading arrived today.",
            "今天没有新的读数。",
            "The data provider did not deliver in time",
            "数据提供方未能及时送达",
        ):
            assert text.count(sentence) == 1, sentence
        for lang in ("en", "zh"):
            parser = _Visible(lang)
            parser.feed(composed)
            empty_lines = [
                t for t in parser.texts
                if "No reading arrived" in t or "没有新的读数" in t
                or "did not deliver" in t or "未能及时送达" in t
            ]
            assert empty_lines, lang
            assert len(empty_lines) == len(set(empty_lines)), (lang, empty_lines)
