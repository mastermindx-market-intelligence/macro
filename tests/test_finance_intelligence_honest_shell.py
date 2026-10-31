"""Ruling F-5 — the Finance Intelligence shell is an honest unbuilt page.

With ``FI_READ_URL == ""`` the public page is NOT a reading of the financial
sector and must never read like one: no synthetic watching constant, an
unbuilt status panel that says so without JavaScript, a hint roster framed
as research hints (not exposure), and no banned words or ISO dates in the
page's own visible text. The connected render keeps today's structure, so a
future bound evidence service keeps every mount.

The shared site nav is frozen (29 suites pin ``_navlinks.html.j2``) and
carries its own governed copy ("Live session board", 盘中实时看板), so the
visible-text scan covers the page's own markup: everything rendered except
the ``nav.site-nav`` include.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from scripts.build_finance_intelligence_page import render_shell

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"

# Common-rules banned words in user-visible copy, plus `refuted` per spec.
_BANNED = ("实时", "申报", "证伪", "validated", "已验证", "live", "forecast",
           "falsifier", "refuted")


def _shell_html(tmp_path: Path) -> str:
    """The builder's temp render — the worktree site/ is never written."""
    (tmp_path / "templates").symlink_to(TEMPLATES, target_is_directory=True)
    return render_shell(tmp_path).read_text(encoding="utf-8")


def _halves(html: str) -> tuple[list[str], list[str]]:
    """Text of every l-en span, then every l-zh span (the language halves)."""
    en = re.findall(r'<span class="l-en">(.*?)</span>', html, re.S)
    zh = re.findall(r'<span class="l-zh">(.*?)</span>', html, re.S)
    return en, zh


class _VisibleTextCollector(HTMLParser):
    """Collect visible text nodes; <script>/<style> bodies are not visible."""

    def __init__(self) -> None:
        super().__init__()
        self.texts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.texts.append(data)


def _page_visible_text(html: str) -> str:
    """Page-owned visible text: script/style bodies and comments dropped,
    tags stripped, and the frozen shared nav include excluded."""
    no_nav = re.sub(r'<nav class="site-nav">.*?</nav>', "", html, flags=re.S)
    no_scripts = re.sub(r"<script.*?</script>", "", no_nav, flags=re.S)
    no_styles = re.sub(r"<style.*?</style>", "", no_scripts, flags=re.S)
    no_comments = re.sub(r"<!--.*?-->", "", no_styles, flags=re.S)
    collector = _VisibleTextCollector()
    collector.feed(no_comments)
    return "\n".join(line for line in
                     (t.strip() for t in collector.texts) if line)


# ──────────────────────────────────────────────────────────────────────────
# 1-2 · no synthetic constant; the shell marks itself not-connected
# ──────────────────────────────────────────────────────────────────────────

def test_shell_has_no_synthetic_constant(tmp_path: Path) -> None:
    """The builder bakes no frozen synthetic watching item into the page.

    No "Synthetic limit", no syn-case id, no 合成限制, none of the fabricated
    windows, and no ``<li class="fi-falsifier"`` row at all — the watching
    include renders empty without ``watching_items``.
    """
    html = _shell_html(tmp_path)
    for token in ("Synthetic limit", "syn-case", "合成限制",
                  "2024-06-30", "2023-11-02", '<li class="fi-falsifier'):
        assert token not in html, token


def test_shell_marks_itself_not_connected_without_js(tmp_path: Path) -> None:
    """The static ``<main>`` start tag carries ``data-state="not-connected"``
    so the honest page holds with JavaScript off (the runtime sets the same
    state in boot())."""
    html = _shell_html(tmp_path)
    main_tag = re.search(r"<main\b[^>]*>", html, re.S)
    assert main_tag, "no <main> start tag in the rendered shell"
    assert 'data-state="not-connected"' in main_tag.group(0)


# ──────────────────────────────────────────────────────────────────────────
# 3-4 · the unbuilt banner; the page's own visible copy stays honest
# ──────────────────────────────────────────────────────────────────────────

def test_unbuilt_banner_once_in_each_language(tmp_path: Path) -> None:
    """Exactly one unbuilt status panel, bilingual, in the l-en/l-zh halves."""
    html = _shell_html(tmp_path)
    en, zh = _halves(html)
    assert en.count("This dossier is not built yet.") == 1
    assert zh.count("本档案尚未建成。") == 1
    assert en.count("A planned dossier on how the financial system moves money, settles "
                    "trades and prices assets. This is planned scope, not yet a "
                    "reading.") == 1
    assert zh.count("关于金融体系如何转移资金、结算交易并为资产定价的计划档案。"
                    "这是计划范围，还不是读数。") == 1
    assert en.count("No evidence service is connected, so nothing on this page "
                    "is a reading of the financial sector. It shows no "
                    "observations or figures.") == 1
    assert zh.count("证据服务尚未接入，因此本页内容都不是对金融板块的读数。"
                    "本页没有观察或数字。") == 1


def test_visible_text_has_no_banned_word_and_no_iso_date(tmp_path: Path) -> None:
    """The page's own visible copy carries no banned word and no ISO date.

    A not-connected page with no evidence service must show no observation,
    date or figure of the financial sector — the only dates it may print are
    none at all.
    """
    text = _page_visible_text(_shell_html(tmp_path))
    lowered = text.lower()
    for word in _BANNED:
        assert word not in (text if word == word.lower() else lowered), word
    assert not re.search(r"\d{4}-\d{2}-\d{2}", text), re.findall(
        r"\d{4}-\d{2}-\d{2}", text)


# ──────────────────────────────────────────────────────────────────────────
# 5-6 · the hint roster reads as hints; the head claims no exposure
# ──────────────────────────────────────────────────────────────────────────

def test_hint_roster_copy_is_honest(tmp_path: Path) -> None:
    """Eleven rows; a lede naming them hints; the chip says not confirmed."""
    html = _shell_html(tmp_path)
    rows = re.findall(r'<li class="fi-hint-row"', html)
    assert len(rows) == 11, f"expected 11 hint rows, got {len(rows)}"
    en, zh = _halves(html)
    assert en.count("These names are research hints under study. "
                    "None has been confirmed.") == 1
    assert zh.count("这些名称是研究中的线索，均未确认。") == 1
    assert en.count("Research hint, not confirmed") == 11
    assert zh.count("研究线索，尚未确认") == 11
    assert not [t for t in en if "validated" in t.lower()]
    assert not [t for t in zh if "已验证" in t]


def test_exposure_head_is_not_presented_as_exposure(tmp_path: Path) -> None:
    """Not connected: the section head is `Names under study`, no eyebrow.

    The page has no exposure figures, so its head must not be headed as if
    it had. `Company exposure` stays only in the hidden TOC/caption mounts
    kept for a connected page."""
    html = _shell_html(tmp_path)
    head = re.search(r'<section id="company-exposure".*?</header>', html, re.S)
    assert head, "#company-exposure head missing from the render"
    block = head.group(0)
    assert "Names under study" in block
    assert "研究中的名称" in block
    assert "Company exposure" not in block
    assert "公司敞口" not in block
    assert "fi-section-eyebrow" not in block


# ──────────────────────────────────────────────────────────────────────────
# 7 · a connected render keeps today's page
# ──────────────────────────────────────────────────────────────────────────

def test_connected_render_keeps_the_page() -> None:
    """A non-empty fi_read_url renders today's page: no not-connected state,
    no unbuilt banner, the exposure head and deck exactly as shipped."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=True)
    html = env.get_template("finance_intelligence.html.j2").render(
        generated_utc="runtime-api",
        active_section="research",
        active_page="finance_intelligence",
        fi_read_url="https://example.invalid/read-model",
    )
    assert 'data-state="not-connected"' not in html
    assert "fi-unbuilt" not in html
    assert "Company exposure" in html
    assert "公司敞口" in html
    assert "Names under study" not in html
    assert "研究中的名称" not in html
    assert "never a hidden score" in html
    assert "context only, not a trade call." in html
    assert "research context, not a trade call." in html


# ──────────────────────────────────────────────────────────────────────────
# 8-9 · the runtime and the stylesheet agree with the static page
# ──────────────────────────────────────────────────────────────────────────

def test_js_keep_map_only_keeps_exposure() -> None:
    """Source pin: not_connected keeps #company-exposure only, its head plus
    the hint lede and roster, and the identity chip says not confirmed."""
    js = (TEMPLATES / "finance_intelligence.js").read_text(encoding="utf-8")
    assert ("var keep = kind === 'not_connected' ? { 'company-exposure': 1 } : {};"
            in js)
    assert "var keepSel = '.fi-section-head, .fi-hint-lede, .fi-hint-roster';" in js
    pairs = re.findall(r"RESEARCH_HINT_UNVALIDATED:\s*\['([^']*)',\s*'([^']*)'\]", js)
    assert len(pairs) == 1, f"label map must define it exactly once: {pairs}"
    en, zh = pairs[0]
    assert en == "Research hint, not confirmed"
    assert zh == "研究线索，尚未确认"


def test_css_hides_unpainted_sections() -> None:
    """Source pin: the static not-connected hides exist and carry no colour
    literal in the .fi-unbuilt / .fi-hint-lede blocks."""
    css = (TEMPLATES / "finance_intelligence.css").read_text(encoding="utf-8")
    for rule in (
        '.fi-shell[data-state="not-connected"] .fi-section:not(#company-exposure)'
        " { display: none; }",
        '.fi-shell[data-state="not-connected"] .fi-toc { display: none; }',
        '.fi-shell[data-state="not-connected"] .fi-provenance { display: none; }',
        '.fi-shell[data-state="not-connected"] [data-fi-mount="notice"]'
        " { display: none; }",
        '.fi-shell[data-state="not-connected"] #company-exposure >'
        " :not(.fi-section-head,",
        ".fi-hint-lede, .fi-hint-roster) { display: none; }",
    ):
        assert rule in css, rule

    def _rule_body(selector: str) -> str:
        rule = re.search(rf"^{re.escape(selector)} \{{([^}}]*)\}}", css, re.M)
        assert rule is not None, f"missing rule: {selector}"
        return rule.group(1)

    for selector in (".fi-unbuilt", ".fi-hint-lede"):
        body = _rule_body(selector)
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b", body), selector
        assert "rgb(" not in body, selector


# ──────────────────────────────────────────────────────────────────────────
# 10-11 · the entry-point cards promise only the unbuilt page
# ──────────────────────────────────────────────────────────────────────────

def _partial_html(name: str) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=True)
    return env.get_template(name).render()


def test_theme_tracker_card_has_no_synthetic_copy() -> None:
    """The Theme Tracker card names the watching paragraph no more."""
    html = _partial_html("_finance_sector_deep_dive.html.j2")
    assert "fi-sdd-watching" not in html
    assert 'aria-describedby="fi-sdd-watching' not in html
    assert "Synthetic" not in html
    assert "合成" not in html
    en, zh = _halves(html)
    assert any("not built yet" in t for t in en)
    assert any("尚未建成" in t for t in zh)


def test_financials_launch_card_promises_nothing_absent() -> None:
    """The Financials basket launch card promises no rerating map."""
    html = _partial_html("_finance_financials_launch.html.j2")
    assert "rerating map" not in html
    assert "重估地图" not in html
    en, zh = _halves(html)
    assert any("not built yet" in t for t in en)
    assert any("尚未建成" in t for t in zh)


def test_committed_page_is_the_honest_shell() -> None:
    """The page readers are served is the honest shell, not an older bake."""
    html = (ROOT / "site" / "finance_intelligence.html").read_text(encoding="utf-8")
    assert 'data-state="not-connected"' in html
    assert 'data-fi-mount="unbuilt"' in html
    for token in ("Synthetic limit", "syn-case", "合成限制", "2024-06-30", "2023-11-02",
                  "Research hint, not validated"):
        assert token not in html, token
