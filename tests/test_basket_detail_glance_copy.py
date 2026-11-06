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


def test_theme_detail_contested_cycle_uses_current_projection_window() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    start = text.index("const CYC_PHASE_ZH=")
    renderer = text[start:text.index("const VH_COLOR=", start)]
    start = text.index("function contestedList(")
    consumer = text[start:text.index("// Distance-to-label-change", start)]
    cases = r"""
const NativeDate = Date;
global.Date = class extends NativeDate {
  constructor(...args) { super(...(args.length ? args : ["2026-11-03T00:00:00.000Z"])); }
};
function check(ok, reason) { if (!ok) throw Error(reason); }
const future = {nextTurn:"trough",low:"2026-12",central:"2027-01",high:"2027-03"};
const cases = [
  ["expired", {nextTurn:"trough",low:"2025-11",central:"2026-01",high:"2026-04"}, false],
  ["future", future, true],
  ["in-progress", {nextTurn:"trough",low:"2026-09",central:"2026-11",high:"2026-12"}, false],
  ["malformed", {nextTurn:"trough",low:"2026-12",central:"2027-13",high:"2027-03"}, false],
  ["reversed", {nextTurn:"trough",low:"2027-03",central:"2027-01",high:"2026-12"}, false],
  ["missing-window", {nextTurn:"trough"}, false],
  ["missing-projection", null, false],
  ["future-peak", {...future,nextTurn:"peak"}, false],
];
const peak = {k:"peak",provisional:true};
for (const [name,proj,isFutureTrough] of cases) {
  const rows = contestedList({}, {cycle:{proj,turns:[]}});
  check(rows.length === (isFutureTrough ? 1 : 0), name+": stale/invalid projection counted as a cycle texture");
  if (isFutureTrough) {
    check(rows[0][0].includes("projecting a trough next"), name+": future trough English reason lost");
    check(rows[0][1].includes("推演下一拐点为底部"), name+": future trough Chinese reason lost");
    check(!rows[0][0].includes("provisional peak") && !rows[0][1].includes("临时顶部"), name+": invented provisional peak");
  }
  const withPeak = contestedList({}, {cycle:{proj,turns:[peak]}});
  check(withPeak.length === 1, name+": independent provisional peak lost or one cycle texture double-counted");
  check(withPeak[0][0].includes("at a provisional peak"), name+": provisional peak English reason lost");
  check(withPeak[0][1].includes("处于临时顶部"), name+": provisional peak Chinese reason lost");
  check(withPeak[0][0].includes("projecting a trough next") === isFutureTrough, name+": false next-trough English copy");
  check(withPeak[0][1].includes("推演下一拐点为底部") === isFutureTrough, name+": false next-trough Chinese copy");
}
check(contestedList({}, null).length === 0, "missing cycle invented a reason");
check(contestedList({}, {cycle:{proj:null,turns:[{k:"peak",provisional:false}]}}).length === 0,
      "an observed peak was promoted to a provisional peak");
const reasons = contestedList(
  {rs_pctile:0.96,textures:{rollover_risk:{band:"high",band_zh:"高",reasons:["breadth"]}}},
  {cycle:{proj:future,turns:[peak]}}
);
check(reasons.length === 3, "cycle, extension and roll-over must remain three independent textures");
check(reasons[1][0].includes("very extended") && reasons[1][1].includes("相对强度极端延展"),
      "independent extension reason changed");
check(reasons[2][0].includes("roll-over risk high") && reasons[2][1].includes("回落风险高"),
      "independent roll-over reason changed");
"""
    _run_js(renderer + "\n" + consumer + "\n" + cases)


# P12.T54 — execute the actual bilingual thesis expression and its source helpers.
def _thesis_render(basket: dict) -> dict:
    import json
    import subprocess

    src = _src()
    helpers = "\n".join([
        next(line for line in src.splitlines() if line.startswith("const L =")),
        next(line for line in src.splitlines() if line.startswith("const esc =")),
        src[src.index("const briefText ="):src.index("const cssv =")],
    ])
    match = re.search(r'<div class="thesis">\$\{(L\(.*\))\}</div>', src)
    assert match, "actual hero thesis expression missing"
    script = helpers + "\nconst b=" + json.dumps(basket) + ";\n" + (
        "JSON.stringify({html:" + match.group(1) + ",briefEn:esc(briefText(b.thesis)),"
        "briefZh:esc(briefText(b.thesis_zh || b.thesis))})"
    )
    runner = "const vm=require('node:vm');process.stdout.write(vm.runInNewContext(JSON.parse(require('fs').readFileSync(0,'utf8')),{}, {timeout:1000}));"
    result = subprocess.run(["node", "-e", runner], input=json.dumps(script),
                            text=True, capture_output=True, check=True, timeout=10)
    return json.loads(result.stdout)


def test_thesis_uses_existing_curated_zh_and_preserves_english() -> None:
    en = "Mainland state banks plus HSBC and BOCHK."
    zh = "内地国有银行加汇丰和中银香港。"
    out = _thesis_render({"thesis": en, "thesis_zh": zh})
    assert out["html"] == f'<span class="l-en">{en}</span><span class="l-zh">{zh}</span>'


def test_thesis_missing_or_empty_zh_keeps_existing_source_fallback() -> None:
    for basket in [{"thesis": "Retained English"}, {"thesis": "Retained English", "thesis_zh": ""}]:
        out = _thesis_render(basket)
        assert out["html"] == '<span class="l-en">Retained English</span><span class="l-zh">Retained English</span>'


def test_thesis_both_languages_keep_existing_markup_escaping() -> None:
    out = _thesis_render({"thesis": '<script>"EN"</script>', "thesis_zh": '<img onerror="ZH">'})
    assert out["html"] == '<span class="l-en">&lt;script&gt;&quot;EN&quot;&lt;/script&gt;</span><span class="l-zh">&lt;img onerror=&quot;ZH&quot;&gt;</span>'


def test_thesis_long_zh_uses_actual_existing_brief_rule() -> None:
    out = _thesis_render({"thesis": "English context", "thesis_zh": "南向高股息和信贷核心板块" * 30})
    assert out["briefZh"].endswith("...") and len(out["briefZh"]) <= 263
    assert out["html"] == '<span class="l-en">English context</span><span class="l-zh">' + out["briefZh"] + '</span>'
