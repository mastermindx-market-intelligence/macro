"""Basket Detail keeps engineering vocabulary out of the primary reading path."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "basket_detail.html.j2"
PAGE_DIRS = [
    ROOT / "site" / "basket",
    ROOT / "site" / "basket_china",
    ROOT / "site" / "basket_hk",
    ROOT / "site" / "basket_canada",
    ROOT / "site" / "basket_intl",
]


def _src() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def _pages() -> list[Path]:
    return [p for d in PAGE_DIRS for p in d.glob("*.html")]


def test_primary_section_names_are_reader_language() -> None:
    src = _src()
    assert "Timing &amp; risk textures" not in src
    assert "${L('Timing &amp; risk','择时与风险')}" in src
    assert "Fast tape is display-only" not in src
    assert "Fast moves are context" in src
    assert "Same narrative elsewhere','其他市场的同一叙事')} <span class=\"chip\"" not in src


def test_entry_tier_codes_are_demoted_to_tooltip_detail() -> None:
    src = _src()
    assert "const TIER_LABELS=" in src
    assert "confirmed setup" in src
    assert "early setup" in src
    assert "forming" in src
    assert "first sign" in src
    helper = src[src.index("function tierBadgeHtml"):src.index("const LABEL_COLOR", src.index("function tierBadgeHtml"))]
    badge = src[src.index("const tierBadge="):src.index("const sortMembers=", src.index("const tierBadge="))]
    assert "Technical tier" in helper
    assert ">${s.tier}" not in helper
    assert "tierBadgeHtml(sg.tier" in badge
    assert "T1 CONFIRMED" not in src
    assert "T2 PRIME" not in src
    assert "T3 APPROACHING" not in src
    assert "T4 FIRST SPARK" not in src


def test_fast_turn_watch_uses_plain_stage_words() -> None:
    src = _src()
    assert "A fresh T1/T2 signal shows up here" not in src
    assert "A fresh early-turn sign appears here" in src
    watch = src[src.index("const fastWatch="):src.index("// coverage disclosure", src.index("const fastWatch="))]
    assert "tierBadgeHtml(x.tier" in watch
    assert ">${esc(x.tier)}" not in watch


def test_potential_explanation_is_short_and_non_engineering() -> None:
    src = _src()
    m = re.search(r"<div class=\"disc\">\$\{L\('Potential combines ([^']+)'", src)
    assert m, "plain Potential explanation missing"
    words = ("Potential combines " + m.group(1)).split()
    assert len(words) <= 48
    for banned in ("T1", "T2", "T3", "T4", "confluence", "repaint"):
        assert banned not in " ".join(words)


def test_score_mechanics_are_progressive_disclosure() -> None:
    src = _src()
    assert "Score Anatomy" not in src
    assert "评分解剖" not in src
    assert '<details class="ftr-anatomy-disclosure">' in src
    assert "How this score is built" in src
    assert "评分如何构成" in src
    assert '<span class="idx">W8</span>' not in src
    assert "W8b pre-registration" not in src
    assert "FT-R7" not in src


def test_footer_is_concise_product_guidance() -> None:
    src = _src()
    assert "Conviction Profile and trust tier" not in src
    assert "validated buy list" not in src
    assert "Research dashboard, not investment advice" in src


def test_all_committed_basket_pages_match_the_glance_contract() -> None:
    pages = _pages()
    assert len(pages) >= 100
    banned = (
        "Timing &amp; risk textures",
        "Fast tape is display-only",
        "A fresh T1/T2 signal shows up here",
        "Potential ranks buy readiness, not the speed of a turn:",
        "Score Anatomy",
        "评分解剖",
        '<span class="idx">W8</span>',
        "Conviction Profile and trust tier",
    )
    for page in pages:
        html = page.read_text(encoding="utf-8")
        for phrase in banned:
            assert phrase not in html, f"{page.relative_to(ROOT)} still contains {phrase!r}"
        assert "How this score is built" in html
        assert "Research dashboard, not investment advice" in html


def test_generated_pages_share_the_new_fingerprinted_stylesheet() -> None:
    import hashlib
    import re

    pages = _pages()
    refs = set()
    for page in pages:
        html = page.read_text(encoding="utf-8")
        m = re.search(r"\.\./assets/css/([0-9a-f]{8})\.css\?v=\1", html)
        assert m, f"{page.relative_to(ROOT)} missing fingerprinted basket CSS"
        refs.add(m.group(1))
    assert len(refs) == 1
    digest = refs.pop()
    css = ROOT / "site" / "assets" / "css" / f"{digest}.css"
    assert css.is_file()
    assert hashlib.sha256(css.read_bytes()).hexdigest()[:8] == digest
    # A valid hash alone can still point to a hand-projected copy that drifts
    # when a later regional build emits the canonical template bytes.
    style = re.search(r"<style>(.*?)</style>", _src(), re.S)
    assert style, "canonical Basket Detail stylesheet is missing"
    assert css.read_text(encoding="utf-8") == style.group(1)
    text = css.read_text(encoding="utf-8")
    assert ".ftr-anatomy-disclosure > summary" in text


# Keep the bilingual cycle-window regression in the EXISTING basket-detail
# template CI suite; a standalone new suite would be unrun by the CI contract.
def _run_js(js: str) -> None:
    result = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=12)
    assert result.returncode == 0, result.stderr + result.stdout


def test_theme_detail_cycle_projection_is_time_honest_en_and_zh() -> None:
    text = TEMPLATE.read_text()
    start = text.index("const CYC_PHASE_ZH=")
    end = text.index("const VH_COLOR=", start)
    renderer = text[start:end]
    assert "function projectionWindowState(" in renderer
    # No real site/endpoint call. Fix date and render both locales.
    cases = r"""
const OldDate = Date;
global.Date = class extends OldDate {
  constructor(...args) { super(...(args.length ? args : ["2026-11-03T00:00:00.000Z"])); }
};
let language = "en";
function L(en, zh) { return language === "zh" ? zh : en; }
function cssv() { return "#456789"; }
function esc(x) { return String(x); }
const make = (pr) => ({
  price: Array.from({length:12}, (_,i)=>({x:2025.15+i*.16,v:90+i})),
  xDomain: [2025, 2027.6], today: 2026.84, turns: [],
  proj: pr, phases: {}, now: {phase:"Expansion",pos:55}
});
const expired = {nextTurn:"peak",central:"2026-01",low:"2025-11",high:"2026-04",central_x:2026.04};
const active = {nextTurn:"peak",central:"2026-10",low:"2026-09",high:"2026-12",central_x:2026.76};
const future = {nextTurn:"peak",central:"2027-01",low:"2026-12",high:"2027-03",central_x:2027.04};
const invalid = {nextTurn:"peak",central:"2026-13",low:"2026-09",high:"2027-02",central_x:2026.95};
function check(ok, reason) { if (!ok) throw Error(reason); }
function forLanguage(lang) {
  language = lang;
  const e = cycleSectionHtml(make(expired),"retail");
  const a = cycleSectionHtml(make(active),"retail");
  const f = cycleSectionHtml(make(future),"retail");
  const u = cycleSectionHtml(make(invalid),"retail");
  const expiredLabel = lang==="en" ? "Historical projection window elapsed" : "历史预测窗口已结束";
  const activeLabel = lang==="en" ? "Projection window in progress" : "预测窗口进行中";
  const futureLabel = lang==="en" ? "Projected next turn" : "推演下一拐点";
  const noProjection = lang==="en" ? "No valid current projection" : "暂无有效当前预测";
  check(e.includes('preserveAspectRatio="xMidYMid meet"'), "chart aspect ratio regression");
  check(e.includes('viewBox="0 0 1080 240"'), "chart geometry regression");
  check(e.includes(expiredLabel), "expired projection not disclosed");
  check(!e.includes(futureLabel) && !e.includes("next peak"), "expired projection falsely called next");
  check(!e.includes("▲</text>"), "expired projection has a future-turn marker");
  check(a.includes(activeLabel) && !a.includes(futureLabel), "active window falsely called next");
  check(!a.includes("▲</text>"), "in-progress projection has future-turn marker");
  check(f.includes(futureLabel) && f.includes(lang==="en" ? "next peak" : "下一顶部"), "genuinely future projection lost");
  check(f.includes("▲</text>"), "genuinely future turn lost marker");
  check(u.includes(noProjection) && !u.includes(futureLabel), "invalid date accepted as projection");
  check(!u.includes("▲</text>"), "invalid projection has a future marker");
}
forLanguage("en"); forLanguage("zh");
check(projectionWindowState(expired,"2026-11")==="expired","expired state");
check(projectionWindowState(active,"2026-11")==="in_progress","in-progress state");
check(projectionWindowState(future,"2026-11")==="future","future state");
check(projectionWindowState(invalid,"2026-11")==="unavailable","invalid date state");
check(projectionWindowState({nextTurn:"peak",central:"2027-01",low:"2026-12",high:"2027-03"},"wrong")==="unavailable","invalid as-of state");
check(projectionWindowState({nextTurn:"peak",central:"2027-01",low:"2027-03",high:"2026-12"},"2026-11")==="unavailable","reversed dates state");
"""
    _run_js(renderer + "\n" + cases)
