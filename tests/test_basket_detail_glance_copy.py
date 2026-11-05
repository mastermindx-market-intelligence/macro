"""Basket Detail keeps engineering vocabulary out of the primary reading path."""
from __future__ import annotations

import re
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
