"""Guard tests for the SIC-P-COMP shared-component specimen.

Checks design_refs/sector-paper-20261021/components/ against the frozen spec:
all 22 component ids rendered in both theme sections (+ one zh-Hans row),
components.css uses only templates/theme.css tokens, no semantic edge borders,
no inset box-shadow, no emoji, no hex outside the marked GAP block, a
COMPONENTS.md section per id, and no occurrence of the house-forbidden
v-word (built by concatenation so this file itself stays clean).

Run: python3 -m pytest -q -p no:cacheprovider tests/test_sector_paper_components.py
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
COMPONENTS_DIR = REPO / "design_refs" / "sector-paper-20261021" / "components"
SPECIMEN = COMPONENTS_DIR / "specimen.html"
CSS_FILE = COMPONENTS_DIR / "components.css"
DOC_FILE = COMPONENTS_DIR / "COMPONENTS.md"
THEME = REPO / "templates" / "theme.css"

IDS = [
    "asof-stamp", "panel-footnote", "state-banner", "stance-chip",
    "direction-delta", "health-badge", "lock-chip", "model-prior-badge",
    "grader-caption", "source-rank-row", "section-header", "see-all-link",
    "skeleton-block", "empty-state", "error-state", "series-picker",
    "phase-chip", "leg-timeline-item", "hazard-ladder", "timing-ladder-row",
    "mobile-sheet", "table-alternative-toggle",
]

SPECIMEN_TEXT = SPECIMEN.read_text(encoding="utf-8")
CSS_TEXT = CSS_FILE.read_text(encoding="utf-8")
DOC_TEXT = DOC_FILE.read_text(encoding="utf-8")

# Emoji / emoji-presentation codepoint ranges (the monoline SVG set replaces
# every glyph job; nothing in these ranges may appear in any owned file).
_EMOJI_RANGES = (
    (0x1F000, 0x1FFFF),  # all SMP emoji blocks
    (0x2139, 0x2139),    # information source
    (0x2194, 0x2199),    # arrows with emoji presentation
    (0x21A9, 0x21AA),    # reply/forward arrows (emoji)
    (0x2300, 0x23FF),    # misc technical (watches, hourglass, media controls)
    (0x25A0, 0x25FF),    # geometric shapes
    (0x2600, 0x27BF),    # misc symbols + dingbats
    (0x2B00, 0x2BFF),    # stars, arrows asterisk
    (0xFE00, 0xFE0F),    # variation selectors
    (0x200D, 0x200D),    # zero-width joiner
    (0x20E3, 0x20E3),    # combining enclosing keycap
)


def _css_without_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


class _SpecimenScan(HTMLParser):
    """Collect data-component ids per theme section and under lang="zh-Hans"."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, dict]] = []
        self.per_theme: dict[str, set[str]] = {"dark": set(), "light": set()}
        self.section_count: dict[str, int] = {"dark": 0, "light": 0}
        self.zh: set[str] = set()

    def _record(self, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        cid = a.get("data-component")
        if cid is None:
            return
        theme = next(
            (s[1].get("data-theme") for s in reversed(self.stack)
             if s[0] == "section" and s[1].get("data-theme") in ("dark", "light")),
            None,
        )
        if theme is not None:
            self.per_theme[theme].add(cid)
        if any(s[1].get("lang") == "zh-Hans" for s in self.stack):
            self.zh.add(cid)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.stack.append((tag, a))
        if tag == "section" and a.get("data-theme") in ("dark", "light"):
            self.section_count[a["data-theme"]] += 1
        self._record(attrs)

    def handle_startendtag(self, tag, attrs):
        self._record(attrs)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                return


def _scan() -> _SpecimenScan:
    scan = _SpecimenScan()
    scan.feed(SPECIMEN_TEXT)
    scan.close()
    return scan


def test_all_components_in_both_theme_sections():
    scan = _scan()
    # one dark section, one light section, one dark zh-Hans section
    assert scan.section_count == {"dark": 2, "light": 1}
    for cid in IDS:
        assert cid in scan.per_theme["dark"], f"missing in dark section: {cid}"
        assert cid in scan.per_theme["light"], f"missing in light section: {cid}"


def test_one_zh_row_per_component():
    scan = _scan()
    for cid in IDS:
        assert cid in scan.zh, f"missing zh-Hans row: {cid}"


def test_css_vars_exist_in_theme():
    theme_names = set(re.findall(r"--([A-Za-z0-9-]+)\s*:", THEME.read_text(encoding="utf-8")))
    assert theme_names, "theme.css token extraction found nothing"
    used = set(re.findall(r"var\(\s*--([A-Za-z0-9-]+)", _css_without_comments(CSS_TEXT)))
    assert used, "components.css uses no tokens?"
    missing = sorted(used - theme_names)
    assert not missing, f"tokens not defined in templates/theme.css: {missing}"


def test_no_semantic_edge_borders():
    css = _css_without_comments(CSS_TEXT)
    for m in re.finditer(r"border-(?:left|right|top|bottom)\s*:\s*([^;{}]+)", css):
        value = m.group(1)
        for name in re.findall(r"var\(--([A-Za-z0-9-]+)", value):
            assert any(k in name for k in ("line", "border", "rule")), (
                f"non-neutral edge border: border value {value!r} names {name}")


def test_no_inset_box_shadow():
    css = _css_without_comments(CSS_TEXT)
    for m in re.finditer(r"box-shadow\s*:\s*([^;{}]+)", css):
        assert "inset" not in m.group(1), f"inset box-shadow forbidden: {m.group(0)}"


def test_no_hex_outside_gap_block():
    gap = re.search(r"/\*\s*GAP\b.*?\*/", CSS_TEXT, re.S)
    rest = CSS_TEXT.replace(gap.group(0), "") if gap else CSS_TEXT
    offenders = re.findall(r"#[0-9a-fA-F]{3,8}\b", rest)
    assert not offenders, f"hex literal outside the GAP block: {offenders}"


def test_no_emoji_codepoints():
    for path in (SPECIMEN, CSS_FILE, DOC_FILE, Path(__file__)):
        text = path.read_text(encoding="utf-8")
        for ch in set(text):
            cp = ord(ch)
            hit = next((f"U+{cp:04X}" for lo, hi in _EMOJI_RANGES if lo <= cp <= hi), None)
            assert hit is None, f"{path.name} contains emoji codepoint {hit}"


def test_doc_has_section_per_component():
    for cid in IDS:
        assert re.search(rf"^##\s+{re.escape(cid)}\b", DOC_TEXT, re.M), (
            f"COMPONENTS.md lacks a section for {cid}")


def test_forbidden_v_word_absent():
    vword = ("valid", "ated")
    needle = "".join(vword)
    for path in (SPECIMEN, CSS_FILE, DOC_FILE, Path(__file__)):
        text = path.read_text(encoding="utf-8").lower()
        assert needle not in text, f"{path.name} contains the forbidden v-word"


def test_fixed_copy_laws():
    assert "Conditional hit rate, not a win rate" in SPECIMEN_TEXT
    assert re.search(r"See all \d+", SPECIMEN_TEXT), "see-all-link must read 'See all N'"
    for stance in ("Act", "Get ready", "Watch — don't chase", "Protect gains",
                   "Stand aside", "Ignore"):
        assert stance in SPECIMEN_TEXT, f"missing stance value: {stance}"
    for phase in ("trough", "recovery", "expansion", "peak", "downturn"):
        assert f'data-phase="{phase}"' in SPECIMEN_TEXT, f"missing phase: {phase}"
    # hazard law: up/3m and up/6m cells are PRIOR (positions 5 and 6 of the grid)
    prior_cells = re.findall(r'<div class="spc-hz-cell" data-source="prior"', SPECIMEN_TEXT)
    assert len(prior_cells) >= 6, "expected PRIOR cells in every hazard ladder copy"
