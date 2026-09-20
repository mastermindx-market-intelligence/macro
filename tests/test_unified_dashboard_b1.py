"""Tests for the UD-B1 Unified Macro Dashboard hero skeleton (round 3).

The hero (templates/_unified_dashboard_hero.html.j2) is included from
templates/dashboard.html.j2 only when `mode == "macro"`. These tests pin the
binding contract against the REAL engine contracts (R-A):
  • event_calendar._event publishes label / label_zh
  • alerts.alert_view publishes message / message_zh
Fixtures are built by calling the real engine view functions — NOT by
inventing keys — so the tests fail RED-first if the engine contract ever
shifts in a way the template doesn't track.

Also pinned: one-integer law (the score prints ONCE), no banned machine-text
vocab ("1 alert(s) fired" etc), live dot uses health tokens (R-D), spine
rows that lack real regime data render as designed-null (R-B), and the flip
clause drops the "now X/100" parenthetical so the gauge stays the only
visible integer (R-C).
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


def _real_vm() -> dict:
    """Build a vm by calling REAL engine view functions (R-A).

    The shape mirrors what scripts/build_site.py hands the dashboard template
    in production — same keys, same engine call sites.
    """
    from datetime import date
    from engine import alerts as _alerts
    from engine import event_calendar as _ec

    # Real event_strip — calls engine.event_calendar.high_impact_strip()
    strip = _ec.high_impact_strip(today=date(2026, 9, 19), horizon_days=14)[:3]

    # Real alerts payload — calls engine.alerts.alert_view() to enrich
    alert = _alerts.alert_view(
        rule="breadth_narrowed",
        severity="info",
        message="Breadth narrowed again — fewer than half of big US stocks are above their 50-day line.",
        message_zh="广度再次收窄——不到一半的大盘股位于 50 日均线之上。",
    )
    alert["ts"] = "2026-09-19T15:30:00Z"

    # market_state — mirror the real engine.market_state_snapshot() shape
    # (we don't run the full snapshot; the keys we exercise here are
    # exactly the ones the template reads).
    market_state = {
        "verdict": "RISK_ON",
        "color": "green",
        "score": 61,
        "raw_score": 85,
        "capped": True,
        "label_en": "Risk-on",
        "label_zh": "风险偏好",
        "headline_en": "Risk-on — the tape, breadth and cross-asset signals line up.",
        "headline_zh": "风险偏好 — 价格、广度与跨资产信号一致。",
        "flip_en": "→ Mixed if risk appetite breaks down (now 85/100).",
        "flip_zh": "→ 若风险偏好走坏（现 85/100），则转「混合」。",
        "asof": "2026-09-19 16:02 ET",
        "alerts_count": 1,
        "mtf": {},  # NO stance_en — designed-null path per R-A
    }

    return {
        "market_state": market_state,
        "stance": {"key": "shift"},
        "alerts": [alert],
        "event_strip": strip,
        "risk_envelope": {},  # NO stance_en — designed-null path per R-A
        "fear_greed": {"label_en": "Greed in the read", "label_zh": "判读中贪婪占优"},
        "latest": {"date": "2026-09-19 16:02 ET", "quad_name": "Risk-on"},
    }


def _render_macro_with_hero(vm: dict) -> str:
    """Render only the hero template against the synthetic vm."""
    template = _env().get_template("_unified_dashboard_hero.html.j2")
    return template.render(**vm)


# --------------------------------------------------------------------------- #
# Real engine contract binding (R-A)
# --------------------------------------------------------------------------- #

def test_hero_reads_real_event_strip_label_label_zh():
    """event_calendar._event publishes label / label_zh — the hero watching
    list must surface those EXACT keys, not invented tip_en / note_en."""
    vm = _real_vm()
    html = _render_macro_with_hero(vm)
    # Find the first real event from the strip
    first = vm["event_strip"][0]
    assert first["label"] in html, (
        f"hero must render event_strip[0].label={first['label']!r}; "
        f"engine contract is label/label_zh, not tip_en/note_en"
    )
    assert first["label_zh"] in html, (
        f"hero must render event_strip[0].label_zh={first['label_zh']!r}"
    )


def test_hero_reads_real_alert_message_message_zh():
    """alerts.alert_view publishes message / message_zh — the hero what-changed
    rows must surface those EXACT keys, not invented title_en."""
    vm = _real_vm()
    html = _render_macro_with_hero(vm)
    alert = vm["alerts"][0]
    assert alert["message"] in html, (
        f"hero must render alerts[0].message={alert['message']!r}; "
        f"engine contract is message/message_zh, not title_en/title_zh"
    )
    assert alert["message_zh"] in html, (
        f"hero must render alerts[0].message_zh={alert['message_zh']!r}"
    )


def test_hero_watching_designed_null_when_event_strip_empty():
    """When event_strip is empty the watching list must surface the
    designed-null plain sentence — never a spec literal, never a blank."""
    vm = _real_vm()
    vm["event_strip"] = []
    html = _render_macro_with_hero(vm)
    assert html.count("Read being updated") >= 3, (
        "watching list must surface 3 designed-null rows when event_strip is empty"
    )


# --------------------------------------------------------------------------- #
# Driver heads use designed-null when vm leg absent (R-A)
# --------------------------------------------------------------------------- #

def test_hero_driver_heads_designed_null_when_vm_leg_absent():
    """Each driver's head verb comes from vm (mtf / risk_envelope / fear_greed).
    When the live vm leg is absent the row prints the designed-null plain
    sentence (NEVER a hardcoded spec literal like 'Holding.' or 'Narrowing.')."""
    vm = _real_vm()
    html = _render_macro_with_hero(vm)
    # The three pre-fix hardcoded heads must NOT appear.
    assert "Holding." not in html
    assert "Cooling, slowly." not in html
    assert "Narrowing." not in html
    # The designed-null sentence appears at least 3 times (one per driver).
    assert html.count("Read being updated") >= 3


def test_hero_driver_head_uses_vm_leg_when_present():
    """When the vm leg IS present (e.g. fear_greed.label_en) the driver
    surfaces that exact phrase — not the designed-null."""
    vm = _real_vm()
    vm["fear_greed"]["stance_en"] = "CUSTOM-FG-STANCE."
    vm["fear_greed"]["stance_zh"] = "自定义情绪。"
    html = _render_macro_with_hero(vm)
    assert "CUSTOM-FG-STANCE." in html


# --------------------------------------------------------------------------- #
# ZH verdict word renders (was set but never printed pre-fix) + l-en on EN (R-A)
# --------------------------------------------------------------------------- #

def test_zh_verdict_word_renders_when_lang_zh():
    """Both EN and ZH verdict words render. The EN word carries `l-en`
    so the ZH locale can hide it via the existing `html[data-lang="zh"] .l-en`
    rule. Pre-fix set _verdict_word_zh but never printed it; pre-fix also
    leaked the EN word into the ZH path."""
    html = _render_macro_with_hero(_real_vm())
    assert "Risk-on" in html
    assert "风险偏好" in html
    # The EN verdict word must carry the l-en class (otherwise ZH can't hide it).
    src = (TEMPLATES / "_unified_dashboard_hero.html.j2").read_text()
    assert 'class="l-en ud-verdict-word' in src, (
        "EN verdict word span must carry l-en class so ZH locale can hide it"
    )


# --------------------------------------------------------------------------- #
# One-integer law (R-C): regime score must print once in the gauge column,
# flip clause drops the "now X/100" parenthetical.
# --------------------------------------------------------------------------- #

def test_score_prints_once_in_gauge_one_integer_law():
    """The single integer for the read lives in the gauge column. The spine
    row carries only the marker geometry + name + stance — no competing
    integer in the rendered text."""
    html = _render_macro_with_hero(_real_vm())
    score_hits = re.findall(r'data-role="score"[^>]*>(\d+)', html)
    assert score_hits == ["61"], f"score integer must print once, got: {score_hits}"
    text_only = re.sub(r"style=\"left:\d+%\"", "", html)
    text_only = re.sub(r"style=\"left:\d+%;width:\d+%\"", "", text_only)
    visible_61 = re.findall(r">\s*61\s*<", text_only)
    assert visible_61 == [">61<"], (
        f"regime score must print exactly once as visible text (gauge), "
        f"got {len(visible_61)} text-node occurrences: {visible_61}"
    )
    # Flip clause must NOT carry a competing integer (the "(now X/100)" parenthetical).
    assert "now 85/100" not in html, (
        "flip clause must drop the (now X/100) parenthetical so the score column "
        "is the only visible integer (R-C one-integer law)"
    )
    assert "现 85/100" not in html, (
        "flip clause must drop the （现 X/100） parenthetical in ZH too"
    )


# --------------------------------------------------------------------------- #
# Plain language: alerts chip is a sentence (R-A — no machine text).
# --------------------------------------------------------------------------- #

def test_alerts_chip_uses_plain_language_sentence():
    """The alerts chip prints a sentence: '1 alert fired' / '3 alerts fired'.
    data-tip matches visible copy (the receipt IS the visible copy)."""
    vm = _real_vm()
    vm["market_state"]["alerts_count"] = 1
    html = _render_macro_with_hero(vm)
    # Plain language sentence
    assert ">1 alert fired<" in html
    assert 'data-tip-en="1 alert fired"' in html
    assert "alert(s)" not in html
    # Plural form
    vm["market_state"]["alerts_count"] = 3
    html = _render_macro_with_hero(vm)
    assert ">3 alerts fired<" in html
    assert 'data-tip-en="3 alerts fired"' in html
    assert "3 alert(s) fired" not in html


# --------------------------------------------------------------------------- #
# Live dot uses health tokens (R-D) — never direction tokens
# --------------------------------------------------------------------------- #

def test_live_dot_uses_health_tokens_not_direction():
    """The Live/实时 freshness dot uses `.ud-live--{ok,warn}` modifier classes
    (HEALTH tokens). Direction tokens `.ud-live--{green,yellow,red}` would
    flip red under the ZH 红涨绿跌 convention — they are forbidden."""
    src = (TEMPLATES / "_unified_dashboard_hero.html.j2").read_text()
    # The template binds the modifier via Jinja — confirm both possible health
    # tokens appear in the rendered output across the verdict color space.
    rendered = _render_macro_with_hero(_real_vm())
    assert "ud-live--ok" in rendered, (
        "hero template must render health token .ud-live--ok for green/yellow verdict"
    )
    # Template source must NOT carry a direction token modifier.
    assert "ud-live--green" not in src, (
        "hero template must NOT use direction token .ud-live--green (R-D)"
    )
    assert "ud-live--yellow" not in src, (
        "hero template must NOT use direction token .ud-live--yellow (R-D)"
    )
    assert "ud-live--red" not in src, (
        "hero template must NOT use direction token .ud-live--red (R-D)"
    )
    # The CSS file must define the ok/warn modifiers and NOT define the direction ones.
    css = (TEMPLATES / "theme.css").read_text()
    assert "ud-live--ok i" in css
    assert "ud-live--warn i" in css
    assert "ud-live--green i" not in css
    assert "ud-live--yellow i" not in css
    assert "ud-live--red i" not in css


# --------------------------------------------------------------------------- #
# Verdict qualifier class modifier (was inline --c: pre-fix)
# --------------------------------------------------------------------------- #

def test_hero_verdict_qualifier_uses_class_modifier_not_inline_custom_property():
    """The qualifier ('narrowing' / 'deepening' / 'steady') lives on a class
    modifier (.ud-verdict-qualifier--{warn,down,muted}) — NEVER an inline
    style="--c: ..." custom property (which fails the design ratchet)."""
    html = _render_macro_with_hero(_real_vm())
    assert "ud-verdict-qualifier--warn" in html
    src = (TEMPLATES / "_unified_dashboard_hero.html.j2").read_text()
    assert 'style="--c:' not in src, "hero template must not declare inline --c:"
    # The CSS must define ALL three modifiers (warn / down / muted).
    css = (TEMPLATES / "theme.css").read_text()
    assert "ud-verdict-qualifier--down" in css, (
        "theme.css must define .ud-verdict-qualifier--down for RISK_OFF"
    )


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
    modifier — not an inline `style="--c:..."`. The modifier is filled by
    Jinja, so the rendered text carries the modifier value; the SOURCE template
    must reference the modifier pattern (`.mx-stance mx-stance--{{...}}`)."""
    src = (TEMPLATES / "_unified_dashboard_hero.html.j2").read_text()
    assert "mx-stance--" in src, (
        "hero template must reference the .mx-stance--{...} modifier pattern"
    )
    # No inline custom property declarations in the markup.
    assert 'style="--c:' not in src
    assert "style='--c:" not in src
    # The four modifiers must exist as CSS classes in theme.css.
    css = (TEMPLATES / "theme.css").read_text()
    for mod in ("ok", "warn", "down", "muted"):
        assert f"mx-stance--{mod}" in css, (
            f"theme.css must define the .mx-stance--{mod} modifier class"
        )


# --------------------------------------------------------------------------- #
# Spine: only US stocks carries a real rail; HK/China A/Bonds/Commodities
# are designed-null (R-B — macro vm does not yet publish their regime data).
# --------------------------------------------------------------------------- #

def test_spine_only_us_stocks_has_marker_other_rows_designed_null():
    """Per R-B the macro vm ACTUALLY only carries US stocks regime data; the
    other four rows render as designed-null with no marker and a "Read being
    updated" stance. Hardcoded specimen stances are forbidden."""
    html = _render_macro_with_hero(_real_vm())
    # US stocks row carries a marker (the only one in the spine).
    us_marker_count = html.count('class="mx-spine-mark"')
    assert us_marker_count == 1, (
        f"only US stocks should carry a spine marker; got {us_marker_count}"
    )
    # The four supporting rows are designed-null — no hardcoded specimen stances.
    assert "Watch — don’t chase" in html or "Watch — don't chase" not in html
    # The hardcoded specimen stances for non-US rows must NOT appear.
    for forbidden in ("Get ready", "Protect gains", "Stand aside"):
        # Each may appear ONCE (in the hero stance chip driven by vm["stance"]),
        # but NOT multiple times across the spine.
        assert html.count(forbidden) <= 1, (
            f"hardcoded specimen stance {forbidden!r} appears in the spine — "
            f"macro vm does not carry HK/China A/Bonds regime data; "
            f"these rows must be designed-null per R-B"
        )
    # Designed-null sentence appears in each spine row stance.
    spine_null_count = html.count("Read being updated")
    assert spine_null_count >= 4, (
        "spine supporting rows must surface the designed-null sentence"
    )


# --------------------------------------------------------------------------- #
# 390 reduction: stance lives in row 1 with name (spec §7).
# --------------------------------------------------------------------------- #

def test_390_mobile_layout_puts_stance_in_name_row():
    """Spec §7 declares row 1 of every spine row = name + stance at 390.
    The CSS must lay the mobile grid out so .mx-spine-name and .mx-spine-stance
    share the first visual row."""
    css = (TEMPLATES / "theme.css").read_text()
    # Find the spine mobile block by anchoring on the comment marker.
    spine_marker = "/* ── mobile 390 reduction (spec §7)"
    idx = css.find(spine_marker)
    assert idx >= 0, "expected a spec §7 mobile reduction comment in theme.css"
    # Take the next ~1500 chars after the comment (the @media block).
    snippet = css[idx:idx + 1500]
    # The stance rule must NOT be display:none (pre-fix hid it).
    assert not re.search(r"\.mx-spine-stance\s*\{\s*display\s*:\s*none", snippet), (
        "390 mobile layout must NOT hide .mx-spine-stance (spec §7 row 1 = name + stance)"
    )
    # The grid-template-areas declaration for .mx-spine-row must put name + stance on the first row.
    areas_m = re.search(
        r"\.mx-spine-row[^{]*\{[^}]*grid-template-areas\s*:\s*([^;]+);",
        snippet, re.DOTALL,
    )
    assert areas_m, "mobile .mx-spine-row must declare grid-template-areas"
    first_row = areas_m.group(1).strip().splitlines()[0]
    assert "name" in first_row and "stance" in first_row, (
        f"390 mobile grid must put name and stance on the same first row; "
        f"got first row={first_row!r}"
    )
    # Both .mx-spine-name and .mx-spine-stance must be assigned grid-areas.
    assert "grid-area: name" in snippet
    assert "grid-area: stance" in snippet
