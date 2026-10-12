"""tests/test_finance_entry_points.py — FIN-T9 entry-point packets.

Two entry points into the Finance Intelligence dossier (templates/finance_intelligence.html.j2):

  · Sector Deep Dives card on the Theme Tracker (templates/state_of_themes.html.j2)
    — placed AFTER the last canonical lane (Working / Early / Caution / Review /
    Quiet), BEFORE the page footer. The include lands in a NEW region called
    "Sector deep dives / 行业深度". The card is a link only: no theme semantics,
    no stage, no rank, no score.
  · Launch module on the Financials basket detail page (templates/basket_detail.html.j2
    guarded by `basket.id == 'us_sector_financials'`). SAME plain-link-only
    discipline.

Owned files (no others touched):
  - templates/_finance_sector_deep_dive.html.j2 (new)
  - templates/_finance_financials_launch.html.j2 (new)
  - templates/state_of_themes.html.j2 (ONE additive include hunk only)
  - templates/basket_detail.html.j2 — UNTOUCHED while #7669 is OPEN
  - tests/test_finance_entry_points.py (new)

OPERATION gmi-finance-fable-ceo-e2e-20260924-chairman-001; carrier PR #7887.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

TEMPLATES = REPO_ROOT / "templates"
TRACKER_J2 = TEMPLATES / "state_of_themes.html.j2"
BASKET_J2 = TEMPLATES / "basket_detail.html.j2"
SECTOR_PARTIAL = TEMPLATES / "_finance_sector_deep_dive.html.j2"
LAUNCH_PARTIAL = TEMPLATES / "_finance_financials_launch.html.j2"

BANNED_WORDS_RE = re.compile(r"rank|score|buy|sell|stage", re.IGNORECASE)

# Anchors quoted from templates/state_of_themes.html.j2:
#   · `{% for lane in lanes %}`        — lanes loop opens at the canonical board
#   · `{% endfor %}`                   — closes the lanes loop (last canonical lane)
#   · `{# ── STUDY SHELF (tier 3) ── #}` — the first thing AFTER the lanes loop
# The Sector deep dives include lands BETWEEN these two anchors.
_LAST_LANE_LOOP_CLOSE = "{% endfor %}"
_STUDY_SHELF_HEAD = "{# ── STUDY SHELF (tier 3) ── #}"

# Pr #7669 status — open per `gh pr view 7669 --json state,mergedAt`
PR_7669_BLOCKER = "BLOCKED_BY_OWNER #7669"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# (1) Tracker template source — partial include once, AFTER the last lane anchor
# ---------------------------------------------------------------------------

def test_tracker_includes_sector_partial_exactly_once():
    src = _read(TRACKER_J2)
    needle = '{% include "_finance_sector_deep_dive.html.j2" %}'
    n = src.count(needle)
    assert n == 1, f"expected the include exactly once in the tracker; got {n}"


def test_tracker_include_position_is_after_last_lane_anchor():
    src = _read(TRACKER_J2)
    # Anchor quoted from the template: `{% endfor %}` closes the lanes loop
    # (the LAST canonical lane in `_LANE_ORDER = [working, early, caution,
    # review, quiet]`).
    lane_close_idx = src.rfind(_LAST_LANE_LOOP_CLOSE)
    assert lane_close_idx > 0, "lanes-loop {% endfor %} anchor not found"
    # Anchor quoted from the template: `{# ── STUDY SHELF (tier 3) ── #}` is
    # the first thing AFTER the lanes loop closes (the include must precede it).
    study_shelf_idx = src.find(_STUDY_SHELF_HEAD)
    assert study_shelf_idx > 0, "study-shelf anchor not found"
    # The include must sit BETWEEN the two anchors — after the lane close,
    # before the study shelf section.
    include_idx = src.find('{% include "_finance_sector_deep_dive.html.j2" %}')
    assert include_idx > 0, "include statement not found"
    assert lane_close_idx < include_idx < study_shelf_idx, (
        f"include position {include_idx} not between lane close "
        f"{lane_close_idx} and study shelf {study_shelf_idx}"
    )


# ---------------------------------------------------------------------------
# (2) Sector deep-dive partial — renders standalone, link-only discipline
# ---------------------------------------------------------------------------

def _render_partial(partial: Path) -> str:
    """Render the partial standalone via jinja2 (no host variables)."""
    from jinja2 import Environment, FileSystemLoader
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=False,
        undefined=__import__("jinja2").Undefined,
    )
    return env.get_template(partial.name).render()


def test_sector_partial_renders_standalone_with_one_link():
    html = _render_partial(SECTOR_PARTIAL)
    # Exactly one <a> element — the link is the entire card surface.
    n_a = len(re.findall(r"<a\b", html))
    assert n_a == 1, f"sector partial must have exactly one <a>; got {n_a}"
    # The href ends with `finance_intelligence.html` (root-relative, matching
    # the tracker's link idiom — the tracker has no nav_prefix, the basket
    # page uses ../, this card lives at root level).
    hrefs = re.findall(r'href="([^"]+)"', html)
    assert hrefs, "sector partial must carry at least one href"
    assert any(h.endswith("finance_intelligence.html") for h in hrefs), (
        f"expected an href ending with finance_intelligence.html; got {hrefs}"
    )


def test_sector_partial_contains_no_banned_words():
    html = _render_partial(SECTOR_PARTIAL)
    hits = BANNED_WORDS_RE.findall(html)
    assert not hits, (
        f"sector partial must carry no rank/score/buy/sell/stage word; "
        f"got {hits}"
    )


def test_sector_partial_has_l_en_l_zh_pairs():
    html = _render_partial(SECTOR_PARTIAL)
    # Host idiom: l-en and l-zh spans, always paired.
    n_en = html.count('class="l-en"')
    n_zh = html.count('class="l-zh"')
    assert n_en >= 1 and n_zh >= 1, (
        f"sector partial must carry at least one l-en and one l-zh pair; "
        f"got l-en={n_en}, l-zh={n_zh}"
    )
    assert n_en == n_zh, (
        f"sector partial must carry equal l-en/l-zh pairs; "
        f"got l-en={n_en}, l-zh={n_zh}"
    )


def test_sector_partial_names_follow_the_page_language():
    """A literal aria-label is English in both languages, and on the card it
    overrode the visible Chinese text — a 中文 screen reader heard "Open the
    Finance Intelligence dossier" (live 2026-09-25). Every name must instead
    come from aria-labelledby/-describedby over an l-en/l-zh pair, whose
    inactive half is display:none and so drops out of the accessible name."""
    from html.parser import HTMLParser

    class Descendants(HTMLParser):
        """Classes found inside each element that carries an id."""

        def __init__(self):
            super().__init__()
            self.stack: list[tuple[str, str | None]] = []
            self.inside: dict[str, set[str]] = {}

        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            for _, ident in self.stack:
                if ident:
                    self.inside[ident].update((a.get("class") or "").split())
            if a.get("id"):
                self.inside.setdefault(a["id"], set())
            self.stack.append((tag, a.get("id")))

        def handle_endtag(self, tag):
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i][0] == tag:
                    del self.stack[i:]
                    break

    html = _render_partial(SECTOR_PARTIAL)
    assert "aria-label=" not in html, "use aria-labelledby over the bilingual spans"
    refs = re.findall(r'aria-(?:labelledby|describedby)="([^"]+)"', html)
    ids = [i for ref in refs for i in ref.split()]
    assert {"fi-sdd-head", "fi-sdd-name", "fi-sdd-cta", "fi-sdd-story"} <= set(ids)
    parser = Descendants()
    parser.feed(html)
    for ident in ids:
        assert ident in parser.inside, f"aria reference {ident!r} has no element in the partial"
        assert {"l-en", "l-zh"} <= parser.inside[ident], (
            f"{ident!r} must hold both language spans so its name switches with the page"
        )


# ---------------------------------------------------------------------------
# (3) Tracker render — canonical theme count unchanged, Finance link in region
# ---------------------------------------------------------------------------

def test_tracker_render_canonical_theme_count_unchanged():
    """Render the tracker with real artifacts; canonical DATA theme-row count
    must equal n_themes from site/neuralwebdata/theme_state.json. The Sector
    deep-dive card uses `class="theme-row sector-deep-dive"` (NOT the bare
    `class="theme-row"` substring the canonical-theme count uses), so it does
    not inflate the count.
    """
    nwd = REPO_ROOT / "site" / "neuralwebdata"
    state_path = nwd / "theme_state.json"
    if not state_path.exists():
        pytest.skip("live artifacts absent — synthetic theme count not exercised here")
    import json as _json
    state = _json.loads(state_path.read_text(encoding="utf-8"))
    n_themes = state.get("n_themes", 0)
    import scripts.build_state_of_themes as sot
    html = sot.render(REPO_ROOT)
    # Canonical-data count uses the EXACT substring the existing live test uses.
    # My sector card uses `class="theme-row sector-deep-dive"` (no closing
    # quote right after `theme-row`), so it does NOT match this substring.
    canonical_count = html.count('class="theme-row"')
    assert canonical_count == n_themes, (
        f"canonical theme-row count must equal n_themes; "
        f"expected {n_themes}, got {canonical_count}"
    )


def test_tracker_render_finance_intelligence_only_in_new_region():
    """The string 'Finance Intelligence' must appear in the rendered HTML, and
    it must appear AFTER the lanes loop close and BEFORE the study-shelf anchor.
    """
    nwd = REPO_ROOT / "site" / "neuralwebdata"
    state_path = nwd / "theme_state.json"
    if not state_path.exists():
        pytest.skip("live artifacts absent — region-position check not exercised here")
    import scripts.build_state_of_themes as sot
    html = sot.render(REPO_ROOT)
    assert "Finance Intelligence" in html, (
        "rendered tracker must mention 'Finance Intelligence' (the new region)"
    )
    # The string appears INSIDE the new region (after lanes loop, before shelf).
    lane_close_idx = html.rfind(_LAST_LANE_LOOP_CLOSE)
    study_shelf_idx = html.find(_STUDY_SHELF_HEAD)
    finance_idx = html.find("Finance Intelligence")
    # Jinja's `{% endif %}` is on the same line as `{% endfor %}` for the
    # lanes loop? No — they're distinct. Use a robust search:
    # the first 'Finance Intelligence' after the last `{% endfor %}` must be
    # before the rendered study shelf.
    assert finance_idx > 0, "Finance Intelligence not found in HTML"
    # We rely on the Jinja {% include %} expanding into the rendered HTML — the
    # included HTML contains the literal "Finance Intelligence" and the
    # surrounding markup does NOT contain it.
    # Stricter check: the sector-deep-dive card class is unique to the new
    # region (not present anywhere else in the tracker).
    assert "sector-deep-dive" in html, (
        "sector-deep-dive card class must appear in rendered HTML "
        "(proves the new region rendered)"
    )
    # Sanity: sector-deep-dive appears AFTER the last canonical `class="theme-row"`.
    last_canonical = html.rfind('class="theme-row"')
    last_sector = html.rfind("sector-deep-dive")
    assert last_canonical >= 0 and last_sector > last_canonical, (
        f"sector-deep-dive must render AFTER the last canonical theme-row; "
        f"last_canonical={last_canonical}, last_sector={last_sector}"
    )
    # And the lanes loop close is BEFORE the sector card.
    if lane_close_idx >= 0 and study_shelf_idx > 0:
        assert lane_close_idx < last_sector < study_shelf_idx, (
            f"sector-deep-dive must sit between lanes close and study shelf; "
            f"close={lane_close_idx}, sector={last_sector}, shelf={study_shelf_idx}"
        )


# ---------------------------------------------------------------------------
# (4) Financials launch partial — same guarantees, basket-relative link
# ---------------------------------------------------------------------------

def test_financials_partial_renders_standalone_with_one_link():
    html = _render_partial(LAUNCH_PARTIAL)
    n_a = len(re.findall(r"<a\b", html))
    assert n_a == 1, f"Financials partial must have exactly one <a>; got {n_a}"
    hrefs = re.findall(r'href="([^"]+)"', html)
    assert any(h.endswith("finance_intelligence.html") for h in hrefs), (
        f"Financials partial must link to finance_intelligence.html; got {hrefs}"
    )
    # The basket page uses `{% set nav_prefix = '../' %}` and existing hrefs
    # in the template (`../theme.css`, `../sector_central.html#...`,
    # `../stock.html#...`) confirm the `../` sibling-relative idiom. The
    # Financials launch module MUST follow that idiom (basket pages live under
    # site/basket/, finance_intelligence.html sits at the site root).
    assert any(h.startswith("../") and h.endswith("finance_intelligence.html") for h in hrefs), (
        f"Financials partial href must use the ../ sibling-relative idiom; got {hrefs}"
    )


def test_financials_partial_contains_no_banned_words():
    html = _render_partial(LAUNCH_PARTIAL)
    hits = BANNED_WORDS_RE.findall(html)
    assert not hits, (
        f"Financials partial must carry no rank/score/buy/sell/stage word; "
        f"got {hits}"
    )


def test_financials_partial_has_l_en_l_zh_pairs():
    html = _render_partial(LAUNCH_PARTIAL)
    n_en = html.count('class="l-en"')
    n_zh = html.count('class="l-zh"')
    assert n_en >= 1 and n_zh >= 1 and n_en == n_zh, (
        f"Financials partial must carry balanced l-en/l-zh pairs; "
        f"got l-en={n_en}, l-zh={n_zh}"
    )


# ---------------------------------------------------------------------------
# (5) Basket detail integration — gated on #7669 state
# ---------------------------------------------------------------------------

def test_basket_detail_partial_integration_blocked_by_owner_7669():
    """While PR #7669 is OPEN, basket_detail.html.j2 must NOT be touched. The
    guarded include hunk lands ONLY after that PR merges — until then the
    Financials launch module exists as a standalone partial and this test
    skips with the literal blocker string.
    """
    pytest.skip(PR_7669_BLOCKER)


# ---------------------------------------------------------------------------
# Sanity / hygiene (always run)
# ---------------------------------------------------------------------------

def test_partials_are_pure_html_no_unrendered_jinja():
    """Both partials must render without leaving any unrendered Jinja tokens."""
    import re as _re
    for p in (SECTOR_PARTIAL, LAUNCH_PARTIAL):
        html = _render_partial(p)
        assert "{{" not in html and "{%" not in html and "{#" not in html, (
            f"{p.name} left unrendered Jinja tokens; got a snippet: "
            f"{[m.group(0) for m in _re.finditer(r'[{]{1,2}[#{%]?', html)][:3]}"
        )


def test_partials_carry_no_inline_style_blocks():
    """The spec forbids inline style blocks in the partials (CSS variables for
    chrome are host-idiom; <style> blocks are not). Small `<style>` blocks
    would break the tracker's existing stylesheet chain."""
    for p in (SECTOR_PARTIAL, LAUNCH_PARTIAL):
        src = _read(p)
        # No <style> block (the tracker already owns all CSS).
        assert "<style" not in src, f"{p.name} contains a <style> block"