"""Tests for the UD-B1 Unified Macro Dashboard hero skeleton.

The hero (templates/_unified_dashboard_hero.html.j2) is included from
templates/dashboard.html.j2 only when `mode == "macro"`. These tests pin the
binding contract: hero markup + class modifiers live on REAL view-model
keys (no illustrative numbers), the score prints ONCE (one-integer law),
no banned machine-text vocab ("1 alert(s) fired" etc), and the design
ratchet passes on the file as added.

The PR reviewer applied these tests after a fix-up that moved all hero
CSS out of an inline <style> block and into templates/theme.css. The
tests also fail RED-first on the pre-fix template (verifying #1, #2).
"""
from __future__ import annotations

import re
from pathlib import Path

import jinja2

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"


def _env() -> jinja2.Environment:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES)),
        autoescape=True,
    )
    env.filters["min"] = lambda seq: min(seq)
    from engine import i18n  # noqa: PLC0415 — same import site as build_site.py
    env.globals.update(td=i18n.td, tr=i18n.tr, zip=zip)
    return env


def _base_vm() -> dict:
    """Synthetic view-model: every key the hero reads (per file header)."""
    return {
        "market_state": {
            "verdict": "RISK_ON",
            "color": "green",
            "score": 61,
            "raw_score": 85,
            "capped": True,
            "label_en": "Risk-on",
            "label_zh": "趋险",
            "headline_en": "Buyers are still showing up — but fewer stocks are carrying the move.",
            "headline_zh": "买盘仍在——但真正推动上涨的个股在减少。",
            "flip_en": "Watch the conditions holding the read.",
            "flip_zh": "留意维持该判读的条件。",
            "asof": "2026-09-19 16:02 ET",
            "alerts_count": 1,
            "mtf": {
                "stance_en": "Holding.",
                "stance_zh": "企稳。",
                "read_en": "Tape read pending — re-drawn nightly.",
                "read_zh": "盘面读数待更新——每晚重绘。",
            },
        },
        "stance": {"key": "run"},
        "alerts": [
            {"ts": "2026-09-19T15:30:00Z", "title_en": "Breadth narrowed again.",
             "title_zh": "广度再次收窄。"},
        ],
        "event_strip": [
            {"tip_en": "If six-in-ten big stocks re-cross their 50-day line, the read moves toward Act.",
             "tip_zh": "若六成大票重新站上 50 日线，判读将趋向「可行动」。"},
            {"tip_en": "If a fresh regime flip prints, the dial caps at Mixed until it settles.",
             "tip_zh": "若出现新一轮周期翻转，仪表将临时封顶为「混合」直至企稳。"},
            {"tip_en": "If the policy-rate landing spot widens, the policy lever tile updates first.",
             "tip_zh": "若利率落点拓宽，政策杠杆区块将先于评分更新。"},
        ],
        "risk_envelope": {
            "stance_en": "Cooling, slowly.",
            "stance_zh": "缓慢降温。",
            "read_en": "Three reads below — never a fused score.",
            "read_zh": "下方为三项读数——非融合评分。",
        },
        "fear_greed": {
            "stance_en": "Narrowing.",
            "stance_zh": "正在收窄。",
            "label_en": "Greed fear in the read",
            "label_zh": "情绪读数：贪婪。",
        },
        "latest": {"date": "2026-09-19 16:02 ET", "quad_name": "Risk-on"},
    }


def _render_macro_with_hero(vm: dict) -> str:
    """Render only the hero template against the synthetic vm."""
    template = _env().get_template("_unified_dashboard_hero.html.j2")
    return template.render(**vm)


# --------------------------------------------------------------------------- #
# One-integer law: regime score must print once in the gauge column.
# --------------------------------------------------------------------------- #

def test_score_prints_once_in_gauge_one_integer_law():
    """The single integer for the read lives in the gauge column. The spine
    row carries only the marker geometry + name + stance — no competing
    integer in the rendered text. Screen-reader bridges use aria-label."""
    html = _render_macro_with_hero(_base_vm())
    # The score number prints ONCE as visible text, in the gauge column.
    score_hits = re.findall(r'data-role="score"[^>]*>(\d+)', html)
    assert score_hits == ["61"], f"score integer must print once, got: {score_hits}"
    # No second integer 61 in any visible text node. The progress pin / arc
    # are GEOMETRY — `style="left:N%"` carries N as a CSS value, never as a
    # text node. Strip those before counting.
    text_only = re.sub(r"style=\"left:\d+%\"", "", html)
    text_only = re.sub(r"style=\"left:\d+%;width:\d+%\"", "", text_only)
    visible_61 = re.findall(r">\s*61\s*<", text_only)
    assert visible_61 == [">61<"], (
        f"regime score must print exactly once as visible text (gauge), "
        f"got {len(visible_61)} text-node occurrences: {visible_61}"
    )
    # The spine row US stocks must NOT carry a visible score integer; the
    # aria-label on a sr-only bridge is the only allowed re-mention.
    spine_row_int = re.search(
        r'data-subject="1"[\s\S]*?</div>\s*</div>\s*</div>',
        html,
    )
    assert spine_row_int
    visible_in_spine = re.findall(r">\s*\d+\s*<", spine_row_int.group(0))
    assert visible_in_spine == [], (
        f"spine subject row must not carry visible integers, got: {visible_in_spine}"
    )


# --------------------------------------------------------------------------- #
# Plain language: no machine-text "1 alert(s) fired" copy.
# --------------------------------------------------------------------------- #

def test_alerts_chip_uses_plain_language_not_machine_text():
    """The "N fired" chip must pluralize cleanly and never print "alert(s)"."""
    vm = _base_vm()
    vm["market_state"]["alerts_count"] = 1
    html = _render_macro_with_hero(vm)
    # Plain language: "1 fired" (singular), not "1 alert(s) fired"
    assert "1 fired" in html
    assert "alert(s)" not in html
    # Plural form
    vm["market_state"]["alerts_count"] = 3
    html = _render_macro_with_hero(vm)
    assert "3 fired" in html
    assert "3 alert(s) fired" not in html


# --------------------------------------------------------------------------- #
# Engine binding: hero reads REAL vm keys (no spec literals).
# --------------------------------------------------------------------------- #

def test_hero_binds_to_event_strip_not_hardcoded_watching_text():
    """Watching list must derive from vm['event_strip'], not hardcoded spec
    clauses. (Pre-fix shipped three identical hardcoded sentences.)"""
    custom = _base_vm()
    custom["event_strip"] = [
        {"tip_en": "CUSTOM-WATCH-A: a unique token signal A.",
         "tip_zh": "自定义观察 A：独特信号。"},
        {"tip_en": "CUSTOM-WATCH-B: a unique token signal B.",
         "tip_zh": "自定义观察 B：独特信号。"},
        {"tip_en": "CUSTOM-WATCH-C: a unique token signal C.",
         "tip_zh": "自定义观察 C：独特信号。"},
    ]
    html = _render_macro_with_hero(custom)
    assert "CUSTOM-WATCH-A" in html
    assert "CUSTOM-WATCH-B" in html
    assert "CUSTOM-WATCH-C" in html
    # Designed-null fallback surfaces the same shape with "Read being updated".
    null_vm = _base_vm()
    null_vm["event_strip"] = []
    null_html = _render_macro_with_hero(null_vm)
    assert null_html.count("Read being updated") >= 3
    assert "CUSTOM-WATCH" not in null_html


def test_hero_driver_heads_derive_from_vm_not_hardcoded():
    """Each driver's head verb comes from vm (mtf / risk_envelope / fear_greed),
    not hardcoded spec literals. Pre-fix always rendered Holding/Cooling/Narrowing."""
    custom = _base_vm()
    custom["market_state"]["mtf"]["stance_en"] = "CUSTOM-MTF-STANCE."
    custom["market_state"]["mtf"]["stance_zh"] = "自定义盘面。"
    html = _render_macro_with_hero(custom)
    assert "CUSTOM-MTF-STANCE." in html
    # The three pre-fix hardcoded heads must NOT be present when their
    # vm leg says something different.
    assert html.count("Holding.") == 0  # not the pre-fix fallback


def test_hero_verdict_qualifier_uses_class_modifier_not_inline_custom_property():
    """The qualifier ('narrowing' / 'deepening' / 'steady') lives on a class
    modifier (.ud-verdict-qualifier--{warn,down,muted}) — NEVER an inline
    style="--c: ..." custom property (which fails the design ratchet)."""
    html = _render_macro_with_hero(_base_vm())
    # RISK_ON + narrowing → qualifier--warn
    assert 'ud-verdict-qualifier--warn' in html
    assert 'class="l-en">narrowing<' in html or 'narrowing' in html
    # No inline `--c:` in the rendered hero (the rendered HTML passes through
    # the design-system check by virtue of the source template avoiding it).
    # We assert this on the SOURCE template, not the rendered output (Jinja
    # expands the value at render-time; the source is what the ratchet scans).
    src = (TEMPLATES / "_unified_dashboard_hero.html.j2").read_text()
    assert 'style="--c:' not in src, "hero template must not declare inline --c:"


# --------------------------------------------------------------------------- #
# ZH verdict word renders (was set but never printed pre-fix).
# --------------------------------------------------------------------------- #

def test_zh_verdict_word_renders_when_lang_zh():
    """Pre-fix set _verdict_word_zh but never printed it. The verdict
    headline must surface both the EN and the ZH word."""
    html = _render_macro_with_hero(_base_vm())
    assert "Risk-on" in html
    assert "趋险" in html


# --------------------------------------------------------------------------- #
# Design ratchet: hero template + theme.css land 0 blocking findings on
# the diff. Pre-fix had 27 (hex / rgba / inline --c: / radius literals).
# --------------------------------------------------------------------------- #

def test_design_system_ratchet_passes_on_added_code():
    """scripts/check_design_system.py --mode enforce-added must return 0
    blocking findings on the B1 diff."""
    import subprocess
    out = subprocess.run(
        ["git", "diff", "--unified=0", "origin/main", "HEAD",
         "--", "templates/theme.css", "templates/_unified_dashboard_hero.html.j2"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    diff_file = ROOT / ".tmp_ud_b1_review.diff"
    diff_file.write_text(out.stdout)
    try:
        result = subprocess.run(
            ["python3", "scripts/check_design_system.py",
             "--mode", "enforce-added", "--diff-file", str(diff_file)],
            cwd=ROOT, capture_output=True, text=True,
        )
        assert result.returncode == 0, (
            f"design-system blocking findings on added code:\n{result.stdout}"
        )
        assert "0 blocking finding" in result.stdout
    finally:
        diff_file.unlink(missing_ok=True)


# --------------------------------------------------------------------------- #
# No inline <style> in the hero template (lives in theme.css).
# --------------------------------------------------------------------------- #

def test_hero_template_has_no_inline_style_block():
    """All hero CSS lives in templates/theme.css; the template is markup-only."""
    src = (TEMPLATES / "_unified_dashboard_hero.html.j2").read_text()
    assert "<style" not in src.lower(), (
        "hero template must not carry an inline <style> block — "
        "all hero CSS lives in templates/theme.css per the design ratchet"
    )


# --------------------------------------------------------------------------- #
# Stance ink: modifier classes set --c via theme.css (the ratchet-friendly
# pattern), NOT inline `style="--c:var(...)"`.
# --------------------------------------------------------------------------- #

def test_hero_stance_uses_class_modifiers_not_inline_custom_property():
    """Every stance chip in the hero must use a `.mx-stance--{ok,warn,muted,down}`
    modifier — not an inline `style="--c:..."`. Inline --c: fails the design
    ratchet (literal-custom-property rule 4)."""
    src = (TEMPLATES / "_unified_dashboard_hero.html.j2").read_text()
    # The modifier classes exist in theme.css; the template uses them.
    assert "mx-stance--ok" in src
    assert "mx-stance--warn" in src
    assert "mx-stance--muted" in src
    assert "mx-stance mx-stance--" in src
    # No inline custom property declarations in the markup.
    assert 'style="--c:' not in src
    assert "style='--c:" not in src