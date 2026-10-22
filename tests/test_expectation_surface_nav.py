"""Pin the Expectation Surface row's contract in the shared Research mega-menu.

The row itself (R1–R4 of the commission): LAST row of the Research drill list,
immediately after Macro Weather; icon drawn in the shared research-icon family
stylesheet in the same accent group as Macro Weather; the derived site/ pair and
the regenerated chat.html pair follow; nothing else in the menu moves.
"""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

REPO = Path(__file__).resolve().parents[1]
TEMPLATES = REPO / "templates"

ROW_HREF = '{{ NP }}expectation_surface.html'
ROW_ICON = 'research-icon research-icon-expectation-surface'
ROW_LABEL_EN = "Expectation Surface"
ROW_LABEL_ZH = "预期曲面"
ROW_DESC_EN = "How consensus estimates moved"
ROW_DESC_ZH = "一致预期如何变动"

# The six pre-existing Research drill rows (href → icon class) that must stay
# in place, once each, in their original order.
RESEARCH_DRILL_ROWS = [
    ("markets.html", "research-icon-global-cycles"),
    ("country_cycles.html", "research-icon-country-cycles"),
    ("sector_cycles.html", "research-icon-sector-cycles"),
    ("sector_cycles_china.html", "research-icon-sector-cycles"),
    ("cycle.html", "research-icon-cycle-intelligence"),
    ("macro_context.html", "research-icon-macro-weather"),
]


def _navlinks() -> str:
    return (TEMPLATES / "_navlinks.html.j2").read_text(encoding="utf-8")


def test_row_is_last_research_drill_row_right_after_macro_weather() -> None:
    html = _navlinks()
    row = html.count(f'<a class="nav-mega-item" href="{ROW_HREF}">')
    assert row == 1, f"expected exactly one Expectation Surface row, found {row}"
    assert ROW_ICON in html
    for s in (ROW_LABEL_EN, ROW_LABEL_ZH, ROW_DESC_EN, ROW_DESC_ZH):
        assert s in html, f"missing string {s!r}"

    # Immediately after the Macro Weather drill row, with nothing but
    # whitespace between the end of that row and the new row.
    anchor = '<a class="nav-mega-item" href="{{ NP }}macro_context.html"><span class="nm-ic research-icon research-icon-macro-weather"'
    i_macro = html.find(anchor)
    assert i_macro != -1, "Macro Weather drill row not found"
    i_macro_end = html.find("</a>", i_macro) + len("</a>")
    i_new = html.find(f'<a class="nav-mega-item" href="{ROW_HREF}">')
    assert i_new != -1, "Expectation Surface row not found"
    assert html[i_macro_end:i_new].strip() == "", "Expectation row is not immediately after Macro Weather"

    # Last row of the drill list: the next non-whitespace after the row is the
    # panel's closing tag.
    row_end = html.find("</a>", i_new) + len("</a>")
    tail = html[row_end:]
    assert tail.lstrip().startswith("</div>"), "Expectation row is not the last row of the drill list"


def test_six_preexisting_research_drill_rows_unchanged() -> None:
    html = _navlinks()
    for href, icon in RESEARCH_DRILL_ROWS:
        needle = f'href="{{{{ NP }}}}{href}"><span class="nm-ic research-icon {icon}"'
        n = html.count(needle)
        assert n == 1, f"{href}: expected exactly 1 drill row with {icon}, found {n}"


def test_icon_rule_and_accent_group_membership() -> None:
    css = (TEMPLATES / "product-nav-icons.css").read_text(encoding="utf-8")
    assert css.count(".research-icon-expectation-surface{") == 1
    mask_pos = css.find(".research-icon-expectation-surface{")
    rule = css[mask_pos:css.find("}", mask_pos)]
    assert "--research-icon-mask:url(\"data:image/svg+xml," in rule, "icon rule must carry the mask data URI"
    # Family idiom on the mask itself.
    for token in ("viewBox='0 0 24 24'", "fill='none'", "stroke='black'",
                  "stroke-width='1.5'", "stroke-linecap='round'", "stroke-linejoin='round'"):
        assert token in rule, f"mask missing family idiom token {token!r}"

    # Same accent group as Macro Weather: some `.nav-mega :is(...)` selector
    # block lists both icon classes.
    for block in _accent_group_blocks(css):
        if ".research-icon-macro-weather" in block:
            assert ".research-icon-expectation-surface" in block, (
                "expectation-surface icon must sit in the same accent group as macro-weather"
            )
            break
    else:
        raise AssertionError("no accent group containing .research-icon-macro-weather found")


def _accent_group_blocks(css: str) -> list[str]:
    """Return the parenthesized member lists of every `.nav-mega :is(...)` block."""
    blocks: list[str] = []
    needle = ".nav-mega :is("
    pos = 0
    while True:
        start = css.find(needle, pos)
        if start == -1:
            return blocks
        open_paren = start + len(needle) - 1
        close_paren = css.find(")", open_paren)
        assert close_paren != -1, "unbalanced :is( in product-nav-icons.css"
        blocks.append(css[open_paren:close_paren])
        pos = close_paren


def test_site_icon_pair_is_byte_copy() -> None:
    template = (TEMPLATES / "product-nav-icons.css").read_bytes()
    site = (REPO / "site" / "product-nav-icons.css").read_bytes()
    assert template == site, "site/product-nav-icons.css must byte-equal the template"


def test_rendered_nav_carries_the_row_without_banned_word() -> None:
    # Pages own the t() macro (each page template defines it before including
    # the shared nav), so the render wrapper supplies the partial's own macro
    # definition verbatim — the same contract a real page render satisfies.
    navlinks = _navlinks()
    start = navlinks.find("{% macro t(")
    end = navlinks.find("{%- endmacro %}", start)
    assert start != -1 and end != -1, "t() macro definition not found in _navlinks.html.j2"
    macro_src = navlinks[start:end + len("{%- endmacro %}")]
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=False)
    tpl = env.from_string(macro_src + '{% include "_site_nav.html.j2" %}')
    for prefix in ("", "../"):
        html = tpl.render(nav_prefix=prefix)
        expected_href = f'href="{prefix}expectation_surface.html"'
        assert expected_href in html, f"rendered nav (prefix {prefix!r}) lacks {expected_href}"
        assert ROW_ICON in html
        for s in (ROW_LABEL_EN, ROW_LABEL_ZH, ROW_DESC_EN, ROW_DESC_ZH):
            assert s in html
        assert "申报" not in html, "banned word 申报 must not appear in rendered nav"


# --- Round 2: the client-side icon-drawing bridge (nav_market.js) ----------


def _nav_market_js() -> str:
    return (TEMPLATES / "nav_market.js").read_text(encoding="utf-8")


def _research_icon_map_block(js: str) -> str:
    start = js.find("var MOCKUP_RESEARCH_ICON_BY_FILE = {")
    assert start != -1, "MOCKUP_RESEARCH_ICON_BY_FILE not found"
    end = js.find("};", start)
    assert end != -1, "MOCKUP_RESEARCH_ICON_BY_FILE closing brace not found"
    return js[start:end]


def test_bridge_drawing_added_to_mockup_icon_paths() -> None:
    js = _nav_market_js()
    marker = "MOCKUP_ICON_PATHS.expectation_surface = '"
    assert js.count(marker) == 1, (
        f"expected exactly one expectation_surface drawing assignment, found {js.count(marker)}"
    )
    start = js.find(marker) + len(marker)
    end = js.find("';", start)
    assert end != -1, "unterminated expectation_surface drawing string"
    drawing = js[start:end]
    for cls in ('class="ghost"', 'class="accent"', 'class="soft-fill"'):
        assert cls in drawing, f"drawing missing structural class {cls}"
    for banned in ("fill=", "stroke=", "#", "rgb(", "style="):
        assert banned not in drawing, f"drawing carries banned token {banned!r}"


def test_bridge_map_entry_after_macro_context_before_close() -> None:
    js = _nav_market_js()
    entry = "'expectation_surface.html': ['expectation_surface', 'violet'],"
    assert js.count(entry) == 1, (
        f"expected exactly one expectation_surface map entry, found {js.count(entry)}"
    )
    map_start = js.find("var MOCKUP_RESEARCH_ICON_BY_FILE = {")
    i_close = js.find("};", map_start)
    i_macro = js.find("'macro_context.html'", map_start)
    i_entry = js.find(entry)
    assert i_macro != -1, "macro_context map entry missing"
    assert i_macro < i_entry, "expectation_surface entry must appear after macro_context"
    assert i_entry < i_close, "expectation_surface entry must precede the map's closing brace"


def test_site_nav_market_js_pair_is_byte_copy() -> None:
    template = (TEMPLATES / "nav_market.js").read_bytes()
    site = (REPO / "site" / "nav_market.js").read_bytes()
    assert template == site, "site/nav_market.js must byte-equal templates/nav_market.js"


def test_six_drill_files_still_in_research_icon_map() -> None:
    block = _research_icon_map_block(_nav_market_js())
    for href, _icon in RESEARCH_DRILL_ROWS:
        needle = f"'{href}':"
        n = block.count(needle)
        assert n == 1, f"{href}: expected exactly 1 map entry, found {n}"
