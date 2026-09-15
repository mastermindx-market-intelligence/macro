"""Runtime-shape guard for the shared Brain widget asset (mm_brain.js).

Born from a production outage (2026-08-25, W1-C heal): a design comment INSIDE
the widget's CSS template literal used markdown-style backticks. The first
backtick terminated the template literal, the following ``.on`` became a
property access on the giant CSS string, and the next backtick re-opened a
template — turning the tail into a tagged-template CALL of a string:
``TypeError: "…" is not a function`` at load, on every page, with `node
--check` and the whole CI suite green (the defect is syntactically valid).

This test is dependency-free and pins the exact failure class: the widget's
CSS template literal may never contain an interior backtick, and the span it
closes must still contain the late-stylesheet composer rules (so an early
termination is named even if the interior backtick itself moved).
"""

from __future__ import annotations

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
COPIES = [ROOT / "templates" / "mm_brain.js", ROOT / "site" / "mm_brain.js"]


def _css_template_span(text: str) -> tuple[int, int]:
    """Return (open_index, close_index) of the `var CSS = <backtick>` literal."""
    marker = "var CSS = `"
    start = text.index(marker) + len(marker) - 1
    close = text.index("`", start + 1)
    return start, close


@pytest.mark.parametrize("path", COPIES, ids=lambda p: str(p.relative_to(ROOT)))
def test_css_template_literal_has_no_interior_backtick(path: pathlib.Path) -> None:
    if not path.exists():
        pytest.skip(f"{path} absent (sparse checkout)")
    text = path.read_text(encoding="utf-8")
    start, close = _css_template_span(text)
    body = text[start + 1 : close]
    line_of_close = text[:close].count("\n") + 1
    # The first backtick after the opener must terminate the WHOLE stylesheet:
    # the "explain this panel" affordance rules (.mmb-exp) are the final block
    # of the sheet, so if the span ends before them, an interior backtick split
    # the template and the tail becomes a tagged-template call of a string at
    # page load.
    assert ".mmb-exp" in body, (
        "CSS template literal of mm_brain.js terminated early at line "
        f"{line_of_close} — an interior backtick splits the stylesheet and "
        "the widget crashes at load (string-is-not-a-function outage, "
        "2026-08-25). Use quotes, never backticks, in comments inside the "
        "template."
    )


# ── the Research toggle reads the ceiling sentence (W9B F11-8) ───────────────
#
# The compact pill was a disclosure in name only. The widget's own sheet hides
# the hover tip below 560px (``@media(max-width:560px){.mmb-rtip{display:none}}``)
# and hides the label with it (``.mmb-rpill .mmb-l{display:none}``), so on a
# phone the control showed a mark and nothing on screen said what the mode
# commits the answer to. The seat ruling for this packet takes the stricter
# copy: the toggle's VISIBLE label is the full authority-ceiling sentence, in
# both languages, at every width, and the accessible name is that same sentence
# rather than a short stand-in.
#
# The sentence is not this test's invention. It is frozen verbatim by
# ``research/market_intelligence_productization/MARKET_ONTOLOGY_F11_POST_VERTICAL_CONTRACT_2026-09-06.md``
# §MO-PAID-031 ("Authority ceiling"), and it is byte-identical to the pair the
# gateway stamps on the end of every research answer AFTER #7100 lands — at this
# head the gateway stamps nothing yet, so the pair exists only in the contract,
# this widget and this test. Either way the toggle says ahead of time what the
# answer will say about itself.
CEILING_EN = (
    "This is a reading of what we already published. It is not a signal, "
    "not a rating, and not advice — nothing here changes any board, rank, or alert."
)
CEILING_ZH = (
    "这是对我们已经发布内容的解读。这不是信号、不是评级、也不是建议——"
    "这里的任何内容都不会改变任何看板、排名或提醒。"
)

_CEILING_CONST_RE = re.compile(
    r"var RESEARCH_CEILING_(EN|ZH)\s*=\s*'([^']*)'", re.MULTILINE
)


def _read(path: pathlib.Path) -> str:
    if not path.exists():
        pytest.skip(f"{path} absent (sparse checkout)")
    return path.read_text(encoding="utf-8")


def _research_toggle(text: str) -> str:
    """The concatenated markup that builds the Research toggle button, whole.

    The widget builds its DOM as one long JS string expression, so the button is
    found by its own ``data-act`` and read from its opening tag to its closing
    one. Everything inside that span is what the toggle can show; nothing
    outside it can satisfy an assertion about the toggle's visible label.
    """
    act = text.index('data-act="research"')
    start = text.rindex("<button", 0, act)
    return text[start : text.index("</button>", act)]


def _rpill_base_rule(text: str) -> str:
    """The ``.mmb-rpill{...}`` base rule, not one of its states or pseudos."""
    start = text.index(".mmb-rpill{")
    return text[start : text.index("}", start)]


_ROW_RULE_RE = re.compile(r"([^{}]*\.mmb-rrow[^{}]*)\{([^{}]*)\}")


def _row_hidden_rule(text: str) -> str | None:
    """A sheet rule that hides ``.mmb-rrow`` while its toggle is entitlement-hidden.

    Deliberately selector-shape agnostic: the row may be hidden with ``:has()``
    on the pill's own ``mmb-off`` state or with a class the widget puts on the
    row. What the guard owns is the OUTCOME — no rule may leave an empty row
    box on the composer.
    """
    for selector, body in _ROW_RULE_RE.findall(text):
        if "mmb-off" in selector and "display:none" in body.replace(" ", ""):
            return f"{selector}{{{body}}}"
    return None


def test_frozen_ceiling_copy_is_bilingual_and_plain() -> None:
    """The pinned sentence pair is the contract's, in real Chinese, no machine text."""
    assert CEILING_EN.endswith(".") and CEILING_ZH.endswith("。")
    # a real ZH twin: Chinese words and CJK punctuation, no ASCII prose left in it
    assert not re.search(r"[A-Za-z]", CEILING_ZH)
    assert re.search(r"[。，、—]", CEILING_ZH)
    for banned in ("falsifier", "refuted", "证伪", "validated"):
        assert banned not in CEILING_EN.lower()
        assert banned not in CEILING_ZH


@pytest.mark.parametrize("path", COPIES, ids=lambda p: str(p.relative_to(ROOT)))
def test_research_toggle_label_is_the_full_ceiling_sentence(path: pathlib.Path) -> None:
    text = _read(path)
    constants = dict(_CEILING_CONST_RE.findall(text))
    assert constants.get("EN") == CEILING_EN, (
        "the widget's research ceiling sentence drifted from the frozen F11 "
        "contract copy (MO-PAID-031 authority ceiling)"
    )
    assert constants.get("ZH") == CEILING_ZH, "the ZH twin drifted from the frozen copy"
    toggle = _research_toggle(text)
    # LB() is the dual-language label span: it carries both twins in data-en /
    # data-zh so the live language switch repaints it, and it renders one of
    # them as the visible text. A sentence anywhere else (an aria-label, a hover
    # tip) is not the visible mark this packet requires.
    assert "LB(RESEARCH_CEILING_EN, RESEARCH_CEILING_ZH)" in toggle, (
        "the Research toggle's visible label must be the full ceiling sentence "
        "in both languages, built with the widget's dual-language label span"
    )


@pytest.mark.parametrize("path", COPIES, ids=lambda p: str(p.relative_to(ROOT)))
def test_research_toggle_keeps_no_compact_mark_and_no_hover_only_tip(
    path: pathlib.Path,
) -> None:
    text = _read(path)
    toggle = _research_toggle(text)
    assert "mmb-rtip" not in toggle, (
        "the ceiling sentence must be in the mark itself, not in a hover tip"
    )
    assert "mmb-rtip" not in text, (
        "the hover-only tip is gone from the sheet: it was display:none below "
        "560px, so on touch it disclosed nothing"
    )
    for compact in ("'Deep'", "Deep Research", "深度研究"):
        assert compact not in toggle, (
            f"compact pill copy {compact!r} survived on the Research toggle"
        )


@pytest.mark.parametrize("path", COPIES, ids=lambda p: str(p.relative_to(ROOT)))
def test_research_toggle_sentence_wraps_at_every_width(path: pathlib.Path) -> None:
    text = _read(path)
    rule = _rpill_base_rule(text)
    assert "white-space:normal" in rule and "nowrap" not in rule, (
        "a full sentence cannot live on a nowrap pill — the toggle must wrap"
    )
    assert ".mmb-rpill .mmb-l{display:none}" not in text, (
        "the phone rule that collapsed the toggle to its mark would hide the "
        "ceiling sentence at 390px, which is the width the ruling names"
    )


@pytest.mark.parametrize("path", COPIES, ids=lambda p: str(p.relative_to(ROOT)))
def test_research_toggle_accessible_name_is_the_sentence(path: pathlib.Path) -> None:
    text = _read(path)
    toggle = _research_toggle(text)
    assert 'aria-pressed' in toggle, "the toggle must still announce its state"
    assert "aria-label" not in toggle, (
        "a short aria-label would override the visible sentence as the "
        "accessible name — the ruling is that the toggle READS the sentence"
    )
    assert "researchBtn.setAttribute('aria-label'" not in text, (
        "the language switch must not re-stamp a short accessible name over the "
        "sentence; the dual-language label span already repaints it"
    )


@pytest.mark.parametrize("path", COPIES, ids=lambda p: str(p.relative_to(ROOT)))
def test_research_toggle_is_its_own_row_not_a_fourth_depth_stop(
    path: pathlib.Path,
) -> None:
    text = _read(path)
    group_start = text.index('id="mmb-lane"')
    group = text[group_start : text.index("</div>", group_start)]
    assert 'data-act="research"' not in group, (
        "the Research toggle must not sit inside the depth group: research is a "
        "grounding mode that runs on Pro, not a fourth stop on the depth axis, "
        "and a full sentence does not fit inside a nowrap segmented control"
    )
    assert 'class="mmb-rrow"' in text, (
        "the toggle needs its own full-width row on the composer for the sentence "
        "to wrap inside"
    )


@pytest.mark.parametrize("path", COPIES, ids=lambda p: str(p.relative_to(ROOT)))
def test_entitlement_hidden_toggle_takes_its_row_with_it(path: pathlib.Path) -> None:
    """A hidden toggle must leave nothing behind on the composer.

    ``.mmb-rrow`` carries its own padding (``0 10px 2px``, ``0 8px 2px`` on
    phones), so while ``.mmb-rpill.mmb-off`` hides the button — the widget's
    first paint before quotas load, and the settled state of every session that
    is not Pro-eligible — the empty row still rendered a 2px band between the
    textarea and the depth control. The row has to disappear on the same
    condition as the toggle inside it.
    """
    text = _read(path)
    assert ".mmb-rpill.mmb-off{display:none}" in text, (
        "the toggle's entitlement-hidden state is no longer expressed as "
        ".mmb-rpill.mmb-off — retarget this guard at the new hidden state"
    )
    assert _row_hidden_rule(text) is not None, (
        "the research row keeps its padding when the toggle inside it is "
        "entitlement-hidden, so an empty 2px band renders on the composer for "
        "every non-Pro session; hide the row on the same condition"
    )
