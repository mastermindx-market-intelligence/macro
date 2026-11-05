"""Every authenticated/product page header comes from ONE source.

Companion to tests/test_public_chrome.py, which guards the *anonymous* family
(_public_nav.html.j2 + the hand-authored landing). This module guards the
*product* family: templates/_site_nav.html.j2.

WHY THIS EXISTS (operator report 2026-08-01, "many of our pages have different
menus... super confusing and ruins UX"):

_navlinks.html.j2 was introduced to stop the menu drifting, but by design it
shared only the LINK LIST — its own header says "the surrounding chrome (the
<nav> wrapper, the search box, the theme/lang controls) stays per-page". So 59
templates each kept a hand-copied right-hand chrome, frozen at whatever date
that page was last edited. A census of the 235 built product pages found
**12 distinct headers**: 5 pages carried a theme-rotation bell, 10 an "AI Daily
Brief" button, 39 a Mastermind pill that 161 others lacked, 2 had no controls at
all, and 14 had no search box.

The fix moved the WHOLE header into _site_nav.html.j2. These tests keep it there.

DESIGN NOTE — these pins are STRUCTURAL, not a banned-word list. The load-bearing
assertion is that the `nav-ctrls` *container* may be authored exactly once; that
catches any new control anyone invents, whereas a list of the four slugs removed
in 2026-08 would only ever re-pin that one postmortem.

SCOPE NOTE — these tests read templates/ only, never site/. A template-only PR
does not re-render site/, so any assertion that a built page matches its
template is unsatisfiable until the render lane runs.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"

CANONICAL = "_site_nav.html.j2"

# templates/chat.html is a plain-copy page: scripts/check_template_site_sync.py
# requires it to byte-match site/chat.html, so a Jinja {% include %} cannot run
# there. It is an EXPLICIT, ENUMERATED exception with its own assertions below —
# never a silent skip. Its link list and nav stylesheet are still divergent; see
# the module docstring of that follow-up work before adding anything here.
PLAIN_COPY_EXCEPTIONS = {"chat.html"}

# _vector_polish.html.j2 restyles .site-nav for pages that don't link theme.css.
# It is CSS only — it must never author header MARKUP.
CSS_ONLY = {"_vector_polish.html.j2"}

# The anonymous/corporate header family, guarded by tests/test_public_chrome.py.
PUBLIC_FAMILY = {"index.html"}


def _t(en: str, zh: str = "") -> Markup:
    return Markup(en)


def _render_canonical() -> str:
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=False)
    return env.get_template(CANONICAL).render(t=_t)


def _product_templates() -> list[Path]:
    """Full pages that render the shared PRODUCT menu.

    Three things are deliberately not product pages:
    - partials (no <body>) — they are included by pages, they are not pages;
    - templates that merely *mention* _navlinks.html.j2 in a comment;
    - the anonymous/corporate family, which has its own header
      (_public_nav.html.j2) and its own guard in tests/test_public_chrome.py.
      templates/index.html is the hand-authored landing that mirrors that
      family, so it belongs to the public side despite carrying `nav-links`
      (a <ul> there, not the product family's <div>).
    """
    out = []
    for p in sorted(TEMPLATES.glob("*.html.j2")) + sorted(TEMPLATES.glob("*.html")):
        if p.name in CSS_ONLY | PUBLIC_FAMILY:
            continue
        s = p.read_text(encoding="utf-8")
        if "<body" not in s:  # a partial, not a page
            continue
        if "_public_nav.html.j2" in s:  # anonymous family
            continue
        # Match BOTH include styles. A converted page includes _site_nav.html.j2
        # and never names _navlinks.html.j2 — keying only on the latter would
        # silently shrink this set to nothing the moment the sweep succeeded,
        # leaving every test built on it green and vacuous.
        includes_menu = re.search(
            r"{%\s*include\s+['\"](?:_navlinks|_site_nav)\.html\.j2", s
        )
        if includes_menu or '<div class="nav-links"' in s:
            out.append(p)
    return out


def test_nav_ctrls_has_exactly_one_source() -> None:
    """The right-hand header chrome may be authored in exactly one file.

    This is the pin that actually holds the line. Adding a bell, an "AI Daily
    Brief" pill, or any control not yet imagined to a single page means opening
    a second <div class="nav-ctrls"> — which fails here regardless of what the
    control is called.
    """
    authors = {
        p.name
        for p in list(TEMPLATES.glob("*.html.j2")) + list(TEMPLATES.glob("*.html"))
        if '<div class="nav-ctrls"' in p.read_text(encoding="utf-8")
    }
    assert authors == {CANONICAL} | PLAIN_COPY_EXCEPTIONS, (
        "the product header's control row must be authored only in "
        f"{CANONICAL} (plus the enumerated plain-copy pages), but found it in: "
        f"{sorted(authors)}. Put the control in {CANONICAL} so every page gets "
        "it, or it will exist on that page alone — which is exactly how this "
        "site reached 12 different headers."
    )


def test_no_template_hand_rolls_the_site_nav_wrapper() -> None:
    """A page opens <nav class="site-nav"> only by including the partial."""
    offenders = sorted(
        p.name
        for p in list(TEMPLATES.glob("*.html.j2")) + list(TEMPLATES.glob("*.html"))
        if p.name not in {CANONICAL} | PLAIN_COPY_EXCEPTIONS | CSS_ONLY
        and '<nav class="site-nav"' in p.read_text(encoding="utf-8")
    )
    assert not offenders, (
        f"these templates hand-roll the header wrapper: {offenders}. "
        f'Replace the whole <nav class="site-nav">...</nav> block with '
        f'{{% include "{CANONICAL}" %}}.'
    )


def test_every_product_page_takes_the_whole_header() -> None:
    """Showing the shared menu means taking the shared chrome with it.

    Pins the specific 2026-08 regression: leader_radar.html.j2 and
    flow_leaders.html.j2 included _navlinks.html.j2 alone, so they rendered the
    menu with no search box, no Terminal button and no theme/lang controls.
    """
    offenders = []
    for p in _product_templates():
        if p.name in {CANONICAL} | PLAIN_COPY_EXCEPTIONS:
            continue
        if f'"{CANONICAL}"' not in p.read_text(encoding="utf-8"):
            offenders.append(p.name)
    assert not offenders, (
        f"these templates pull in the menu without the header chrome: "
        f"{offenders}. Include {CANONICAL} (which includes _navlinks.html.j2 "
        "itself) rather than _navlinks.html.j2 directly."
    )


def test_canonical_header_renders_the_agreed_control_set() -> None:
    """Search + Terminal + theme + lang — asserted on RENDERED output.

    Rendering (not grepping source) keeps this honest: a control commented out,
    moved behind a Jinja conditional, or renamed still fails here.
    """
    html = _render_canonical()
    assert 'class="nav-search"' in html, "the header lost its search box"
    assert "product-icon-terminal" in html, "the header lost the Terminal link"
    assert 'class="theme-switch"' in html, "the header lost the dark/light toggle"
    assert 'class="lang-toggle"' in html, "the header lost the EN/中文 toggle"


def test_controls_removed_by_operator_stay_removed() -> None:
    """operator 2026-08-01, on the three stranded controls.

    - "the bell is useless we don't want it"
    - AI Daily Brief: already embedded in each country's macro dashboard
      (_aibrief_body.html.j2 in dashboard/china/hk), so the pill duplicated it
    - Mastermind: theme.js injects mm_brain.js on every page, which mounts its
      own bottom-right launcher, so the nav pill was redundant

    Asserted on rendered output for the same reason as the test above.
    """
    html = _render_canonical()
    assert "theme-bell" not in html, "the theme-rotation bell is back in the header"
    assert "AI Daily Brief" not in html, (
        "the AI Daily Brief pill is back; that content is embedded in each "
        "country's macro dashboard already"
    )
    assert "product-icon-mastermind" not in html, (
        "the Mastermind pill is back; theme.js already mounts the Mastermind "
        "launcher bottom-right on every page"
    )


def test_context_link_slot_works() -> None:
    """The sanctioned way to add a page-specific link to the header row.

    Rendered, not grepped: if someone "simplifies" the loop away, pages that
    pass nav_context_links would silently render nothing and their links would
    vanish — which is precisely how the back-links below got lost mid-sweep.
    """
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=False)
    html = env.get_template(CANONICAL).render(
        t=_t,
        nav_context_links=[
            {"href": "../baskets.html", "icon": "🧺", "en": "All themes", "zh": "全部主题"},
            {
                "href": "china.html",
                "icon_class": "menu-icon menu-icon-flag menu-icon-cn",
                "en": "China",
                "zh": "中国",
            },
        ],
    )
    assert 'href="../baskets.html"' in html and "All themes" in html
    assert 'href="china.html"' in html
    assert 'class="menu-icon menu-icon-flag menu-icon-cn"' in html
    # and it must stay optional — pages that pass nothing render no extras
    bare = env.get_template(CANONICAL).render(t=_t)
    assert "nav-context-link" not in bare


def test_drilldown_pages_keep_a_way_back() -> None:
    """Detail pages must retain the link back to their index.

    basket_detail and subsector_detail each carried an "All themes" /
    "All subsectors" back-link inside their hand-rolled header. A sweep that
    replaces hand-rolled headers wholesale silently deletes real navigation
    along with the duplicated chrome — this pin is what catches that.
    """
    for name, target in (
        ("basket_detail.html.j2", "baskets.html"),
        ("subsector_detail.html.j2", "subsectors.html"),
    ):
        s = (TEMPLATES / name).read_text(encoding="utf-8")
        # Match the assignment exactly and read only INSIDE its list, so neither
        # renaming the variable nor the target merely appearing elsewhere in the
        # page can satisfy this.
        m = re.search(
            r"{%\s*set\s+nav_context_links\s*=\s*\[(.*?)\]\s*%}", s, re.DOTALL
        )
        assert m, f"{name} lost its nav_context_links back-link slot"
        assert target in m.group(1), (
            f"{name}'s back-link no longer points at {target}; slot contains: "
            f"{m.group(1).strip()[:120]}"
        )


def test_shared_header_always_has_its_base_styling() -> None:
    """A page taking the shared header must also load CSS that styles it.

    Repeat of the #286 regression: a self-contained page adopts
    <nav class="site-nav"> but links no theme.css, so the menu loses ALL base
    styling and renders as an unstyled, fully-expanded list.
    _vector_polish.html.j2 exists to restore it on exactly those pages.

    It recurred silently in china_narrative_radar.html.j2: #3235 converted the
    template on 2026-07-22, but build_narrative_radar.py was wired into no
    workflow, so the page never rebuilt and nobody saw the broken nav for six
    weeks. Adopting the header and its stylesheet is now one indivisible step.
    """
    offenders = []
    for p in _product_templates():
        s = p.read_text(encoding="utf-8")
        if f'"{CANONICAL}"' not in s:
            continue
        if "theme.css" in s or "_vector_polish.html.j2" in s:
            continue
        offenders.append(p.name)
    assert not offenders, (
        f"these pages include {CANONICAL} but link neither theme.css nor "
        f'_vector_polish.html.j2, so the menu renders unstyled: {offenders}. '
        'Add {% include "_vector_polish.html.j2" %} after the page\'s </style>.'
    )


def test_shared_header_always_has_its_behavior() -> None:
    """A page taking the shared header must also load theme.js.

    Sibling of the styling pin above, and the half it missed. theme.js owns
    every control in _site_nav.html.j2: the dropdown menus, the unified stock
    search (`ensureNavSearchCss` -> `initNavSearch`), the theme switch and the
    EN/中文 toggle. A page that links theme.css but not theme.js therefore
    renders a header that LOOKS roughly right and does nothing at all — no menu
    opens, neither toggle fires, search never upgrades.

    That is not a hypothetical: ticker_index.html.j2 (/stocks/index.html)
    shipped this way and was reported as "this page uses our old menu", because
    an inert header is indistinguishable from an older one to the person
    clicking it. market_structure.html.j2 and stage_analysis.html.j2 carried the
    same defect. Taking the header, its stylesheet and its script is one
    indivisible step.
    """
    offenders = []
    for p in _product_templates():
        s = p.read_text(encoding="utf-8")
        if "theme.js" in s:
            continue
        offenders.append(p.name)
    assert not offenders, (
        f"these pages take the shared header but never load theme.js, so every "
        f"control in it is dead markup: {offenders}. Add "
        '<script defer src="{{ nav_prefix }}theme.js"></script> beside the '
        "page's theme.css link."
    )


def test_search_placeholder_is_one_unified_universe() -> None:
    """No page may re-scope the search box to a single market.

    theme.js merges every market's nightly library and routes each pick to the
    analyzer that owns it. Before this sweep, three different placeholders were
    in circulation, one of them ("Search any market…") still implying the old
    per-market scoping.
    """
    stale = sorted(
        p.name
        for p in _product_templates()
        if re.search(r'placeholder="Search any market', p.read_text(encoding="utf-8"))
    )
    assert not stale, (
        f"these templates still scope search to one market: {stale}. The search "
        f"box is one unified universe; override copy via "
        "nav_search_placeholder_en/zh only when a page genuinely differs."
    )


def test_subsector_detail_uses_unified_intelligence_shell_and_responsive_member_cards():
    template = (TEMPLATES / "subsector_detail.html.j2").read_text()
    for token in ('class="id-hero"', 'class="id-group-read"', 'class="id-structure"',
                  'class="members-table-wrap"', 'class="member-cards"', 'class="id-evidence"'):
        assert token in template
    compact = template.replace(" ", "")
    assert "@media(max-width:640px)" in compact
    assert ".members-table-wrap{display:none" in compact
    assert ".member-cards{display:grid" in compact


def test_subsector_detail_preserves_payload_truth_and_existing_chart_consumer():
    template = (TEMPLATES / "subsector_detail.html.j2").read_text()
    for token in ("g.as_of", "g.n_priced", "g.n_members", "g.reliability", "g.members", "r.action", "e.reason"):
        assert token in template
    assert "window.StockChart.mount" in template
    assert "CHART_KEY" in template
    assert "T1 · confirmed setup" in template  # preserve the incumbent tier code visibly on touch/mobile
    assert 'data-tier="' in template
    assert "AI Semiconductors" not in template
    assert ">66<" not in template


def _execute_subsector_detail_render(detail: dict) -> str:
    """Render the real template, execute its inline consumer, and return #app HTML."""
    from scripts import build_subsector_confluence as bsc

    html = bsc._env().get_template("subsector_detail.html.j2").render(
        detail_json=json.dumps(detail, ensure_ascii=False),
        group_name=detail["group"]["label"],
        chart_key=None,
        has_signals=False,
        back_href="../subsectors.html",
    )
    scripts = re.findall(r"<script(?: [^>]*)?>(.*?)</script>", html, flags=re.S)
    js = next(block for block in scripts if "const DETAIL =" in block)
    node = shutil.which("node")
    assert node is not None, "node is required to execute the intelligence-detail consumer contract"
    harness = (
        "const app={innerHTML:''};"
        "global.document={getElementById:(id)=>id==='app'?app:{},addEventListener:()=>{}};"
        "global.window={};\n"
        + js
        + "\nprocess.stdout.write(app.innerHTML);\n"
    )
    run = subprocess.run([node, "-e", harness], capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stderr
    return run.stdout


def test_subsector_detail_render_preserves_localized_truth_all_stats_and_mobile_member_parity():
    detail = {
        "kind": "concept",
        "group": {
            "key": "demo", "basket_id": "demo", "label": "Demo", "label_zh": "示例",
            "sector": "Technology", "sector_zh": "科技", "n_members": 1, "n_priced": 6,
            "reliability": "med", "as_of": "2026-09-22", "class": "forming",
            "entry": {
                "tier": "T3", "buyable": True, "reason": "forward confirmation pending",
                "ticks": 0, "bars_to_cross": 1.5, "above200": True,
            },
            "regime": {
                "side": "tactical", "label": "English label", "label_zh": "中文标签",
                "action": "English action", "action_zh": "中文行动",
                "stoch_3d": 12, "rs_60d": 3.2,
            },
            "members": [{
                "ticker": "AAA", "name_zh": "甲", "price": 123.45,
                "stock_tier": "T2", "ret_20d": 4.2, "vs_basket": 1.1,
                "stock_state": "BUY", "stock_buyable": True,
                "behaves_as": {
                    "home_id": "other", "home_label": "Other", "home_label_zh": "其他",
                    "homes": [{"label": "Other", "corr20": 0.88}],
                },
            }],
        },
    }
    rendered = _execute_subsector_detail_render(detail)

    assert '<span class="l-en">English action</span><span class="l-zh">中文行动</span>' in rendered
    assert '<span class="l-en">English label</span><span class="l-zh">中文标签</span>' in rendered
    assert '<span class="l-en">Medium</span><span class="l-zh">中</span>' in rendered

    stats = rendered.split('<div class="id-stats">', 1)[1].split(
        '<section class="id-structure"', 1
    )[0]
    assert stats.count('class="id-stat"') == 5
    for label in ("Washout", "RS60", "Cross age", "To cross", "200d trend"):
        assert label in stats

    cards = rendered.split('<div class="member-cards">', 1)[1].split('</section>', 1)[0]
    assert "123.45" in cards
    assert "behaves-as Other" in cards
    assert "类同 其他" in cards


def test_subsector_detail_adapts_visible_identity_without_builder_fork():
    from scripts import build_subsector_confluence as bsc

    html = bsc._env().get_template("subsector_detail.html.j2").render(
        detail_json='{"kind":"concept"}', group_name="Smart Home", chart_key=None,
        has_signals=False, back_href="../subsectors_china.html",
    )
    assert "<title>Smart Home — Intelligence Detail</title>" in html
    assert "Intelligence groups" in html
    assert "情报分组" in html
    assert "pageIdentity = DETAIL.kind" in html
    assert 'L("Theme Intelligence", "主题情报")' in html
    assert 'L("Sector Intelligence", "板块情报")' in html
    assert 'L("Subsector Intelligence", "子行业情报")' in html
