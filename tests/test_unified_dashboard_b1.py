"""Tests for the retained UD-B1 Unified Macro Dashboard candidate.

As of the 2026-09-20 primary-route override, the candidate partial remains in
source for redesign but is not mounted by templates/dashboard.html.j2. These
tests continue to pin its component-level bindings against the REAL engine
contracts (R-A, R-H):
  • event_calendar._event publishes label / label_zh
  • alerts.alert_view publishes message / message_zh
  • fear_greed.compute_fear_greed() publishes label_en / label_zh / dial
  • risk_envelope.compose() publishes provenance.sources[].label_en/label_zh

Fixtures are built by calling the real engine view functions — NOT by
inventing keys — so the retained candidate cannot silently drift while it is
off-route. Primary-route deployment is pinned separately in
`tests/test_dashboard_template_render.py` and by the built-page absence check
at the end of this module.

Also pinned: one-integer law (the score prints ONCE), no banned machine-text
vocab ("alert(s) fired" etc), live dot uses health tokens (R-D), spine rows
that lack real regime data render as designed-null (R-B), the flip clause
drops the "now X/100" parenthetical so the gauge stays the only visible
integer (R-C), and the spine month-ago anchor uses ms_history (R-G — never a
same-day cap delta).
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import jinja2

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
SITE = ROOT / "site"


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
    """Build a vm by calling REAL engine view functions (R-A, R-H).

    The shape mirrors what scripts/build_site.py hands the dashboard template
    in production — same keys, same engine call sites.

    Two lawful fixture forms:
      (a) Call the real engine view function on a minimal real input.
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
        # market_state.mtf publishes {indices: [{confluence_en, confluence_zh, ...}]}
        # The hero driver 1 must read confluence_en from indices[0] — never a
        # non-existent top-level stance_en (R-K, R-H lawful fixture form (a)).
        "mtf": {
            "indices": [
                {"ticker": "SPX", "label_en": "S&P 500", "label_zh": "标普 500",
                 "confluence_en": "Uptrend", "confluence_zh": "上升趋势", "tone": "good"},
            ],
        },
    }

    # ms_history — a 30-session slice of {asof, score} dicts so the spine
    # can anchor its month-ago point at index -22 (~21 sessions back, the
    # 50-session path used by the hero path chart per R-G). When shorter,
    # the row carries the designed-null treatment.
    ms_history = []
    for i in range(30):
        # Synthetic but PUBLISHED shape — same {asof, score} keys the live
        # _ms_history_view returns. The "month-ago" score 85 maps to the
        # `_raw` cap value; today's 61 maps to `_score`.
        if i < 29:
            ms_history.append({"asof": f"2026-08-{10 + i:02d}", "score": 50 + i})
    ms_history.append({"asof": "2026-09-19", "score": 61})

    return {
        "market_state": market_state,
        "stance": {"key": "shift"},
        "alerts": [alert],
        "event_strip": strip,
        "ms_history": ms_history,
        # risk_envelope publishes provenance.sources[].label_en/label_zh —
        # driver 2 reads provenance.sources[0] (R-K). No top-level
        # `sources` key, no `stance_en` fallback. Built the canonical shape.
        "risk_envelope": {
            "schema": "mastermind.risk_envelope/v1",
            "provenance": {
                "sources": [
                    {"source_id": "ms", "role": "measured_state",
                     "label_en": "Market state", "label_zh": "市场状态"},
                    {"source_id": "lead", "role": "hazard_evidence",
                     "label_en": "Leadership cohort", "label_zh": "龙头板块"},
                    {"source_id": "xas", "role": "hazard_evidence",
                     "label_en": "Cross-asset scares", "label_zh": "跨资产异动"},
                ],
            },
        },
        # fear_greed publishes {label_en, label_zh, dial} — driver 3 reads
        # label_en / label_zh (R-K: prefer label_en over any stance_en).
        "fear_greed": {"dial": 71, "label_en": "Greed in the read", "label_zh": "判读中贪婪占优"},
        "latest": {"date": "2026-09-19 16:02 ET", "quad_name": "Risk-on"},
    }


def _render_macro_with_hero(vm: dict) -> str:
    """Render only the hero template against the synthetic vm."""
    template = _env().get_template("_unified_dashboard_hero.html.j2")
    return template.render(**vm)


# --------------------------------------------------------------------------- #
# Real engine contract binding (R-A, R-H lawful fixture form (a))
# --------------------------------------------------------------------------- #

def test_hero_reads_real_event_strip_label_label_zh():
    """event_calendar._event publishes label / label_zh — the hero watching
    list must surface those EXACT keys, not invented tip_en / note_en."""
    vm = _real_vm()
    html = _render_macro_with_hero(vm)
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
# Driver heads use real published keys (R-A, R-K, R-H)
# --------------------------------------------------------------------------- #

def test_hero_driver_heads_designed_null_when_vm_leg_absent():
    """Each driver's head verb comes from vm (mtf / risk_envelope / fear_greed).
    When the live vm leg is absent the row prints the designed-null plain
    sentence (NEVER a hardcoded spec literal like 'Holding.' or 'Narrowing.')."""
    vm = _real_vm()
    # Strip the legs the drivers read so designed-null path fires for each.
    vm["market_state"]["mtf"] = {"indices": [{}]}
    vm["risk_envelope"] = {}
    vm["fear_greed"] = {}
    html = _render_macro_with_hero(vm)
    # The three pre-fix hardcoded heads must NOT appear.
    assert "Holding." not in html
    assert "Cooling, slowly." not in html
    assert "Narrowing." not in html
    # The designed-null sentence appears at least 3 times (one per driver).
    assert html.count("Read being updated") >= 3


def test_hero_driver_head_uses_real_published_key_when_present():
    """When the vm leg IS present (e.g. fear_greed.label_en) the driver
    surfaces that exact phrase — not the designed-null. R-H lawful fixture
    form (a): call the real engine view function on a minimal input."""
    vm = _real_vm()
    # Inject a label that the real engine view could publish (a "Greed"
    # band is plausible). The hero driver 3 must surface label_en verbatim.
    vm["fear_greed"]["label_en"] = "Greed"
    vm["fear_greed"]["label_zh"] = "贪婪"
    html = _render_macro_with_hero(vm)
    assert "Greed" in html


def test_hero_driver_mtf_reads_confluence_en_from_indices():
    """R-A, R-K: market_state.mtf publishes {indices: [{confluence_en, confluence_zh, ...}]}.
    The hero driver 1 must read confluence_en from indices[0], NOT a non-existent
    top-level stance_en. R-H lawful fixture form (a) — the test fixture pre-fix
    injected a top-level stance_en; that path is gone; confluence_en from
    indices[0] is the real contract."""
    vm = _real_vm()
    # _real_vm already populates indices[0].confluence_en="Uptrend"
    html = _render_macro_with_hero(vm)
    assert "Uptrend" in html, (
        "driver 1 must read mtf.indices[0].confluence_en (engine contract)"
    )
    assert "上升趋势" in html, (
        "driver 1 must read mtf.indices[0].confluence_zh (engine contract)"
    )


def test_hero_driver_risk_envelope_reads_provenance_sources():
    """R-K: risk_envelope publishes provenance.sources[].label_en/label_zh
    (engine/risk_envelope.py:553-571). No top-level sources, no stance_en
    fallback. Driver 2 surfaces provenance.sources[0].label_en — the same
    word the Grey Deer band lists. R-H lawful fixture form (a)."""
    vm = _real_vm()
    # _real_vm populates risk_envelope.provenance.sources[0].label_en
    html = _render_macro_with_hero(vm)
    assert "Market state" in html, (
        "driver 2 must read risk_envelope.provenance.sources[0].label_en "
        "(R-K — the same word the Grey Deer band lists)"
    )
    assert "市场状态" in html, (
        "driver 2 must read risk_envelope.provenance.sources[0].label_zh"
    )


def test_hero_driver_risk_envelope_designed_null_when_no_source():
    """R-K: when provenance.sources is empty (the macro vm does not wire
    risk_envelope yet), driver 2 must fall through to the designed-null
    sentence — never an invented spec literal."""
    vm = _real_vm()
    vm["risk_envelope"] = {}  # no provenance, no sources
    html = _render_macro_with_hero(vm)
    # Designed-null row in driver 2
    assert html.count("Read being updated") >= 3, (
        "driver 2 must surface designed-null when risk_envelope.provenance is absent"
    )


def test_hero_driver_fear_greed_prefers_label_en_over_stance_en():
    """R-K: fear_greed publishes {label_en, label_zh, dial}. Driver 3 reads
    label_en / label_zh — never a caller-supplied `stance_en`. R-H lawful
    fixture form (a)."""
    vm = _real_vm()
    vm["fear_greed"]["label_en"] = "Fear"
    vm["fear_greed"]["label_zh"] = "恐惧"
    vm["fear_greed"]["stance_en"] = "FORGOTTEN-STANCE."  # invented; must NOT win
    vm["fear_greed"]["stance_zh"] = "已遗忘立场。"  # invented; must NOT win
    html = _render_macro_with_hero(vm)
    assert "Fear" in html, (
        "driver 3 must prefer fear_greed.label_en over any stance_en"
    )
    assert "FORGOTTEN-STANCE." not in html, (
        "driver 3 must NOT surface an invented stance_en — engine publishes label_en"
    )


# --------------------------------------------------------------------------- #
# ZH verdict word renders (R-A) + l-en on EN so ZH locale can hide it
# --------------------------------------------------------------------------- #

def test_zh_verdict_word_renders_when_lang_zh():
    """Both EN and ZH verdict words render. The EN word carries `l-en`
    so the ZH locale can hide it via the existing `html[data-lang="zh"] .l-en`
    rule."""
    html = _render_macro_with_hero(_real_vm())
    assert "Risk-on" in html
    assert "风险偏好" in html
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
    assert "now 85/100" not in html, (
        "flip clause must drop the (now X/100) parenthetical so the score column "
        "is the only visible integer (R-C one-integer law)"
    )
    assert "现 85/100" not in html, (
        "flip clause must drop the （现 X/100） parenthetical in ZH too"
    )


# --------------------------------------------------------------------------- #
# Plain language: alerts chip is a real sentence (R-A).
# --------------------------------------------------------------------------- #

def test_alerts_chip_uses_plain_language_sentence():
    """The alerts chip prints a plain sentence — NOT a count+verb machine-text
    like '1 alert fired'. data-tip matches visible copy."""
    vm = _real_vm()
    vm["market_state"]["alerts_count"] = 1
    html = _render_macro_with_hero(vm)
    # Plain language sentence
    assert ">One fired condition today.<" in html
    assert 'data-tip-en="One fired condition today."' in html
    # Banned machine-text forms
    assert "alert fired" not in html
    assert "alerts fired" not in html
    assert "alert(s)" not in html
    # Plural form
    vm["market_state"]["alerts_count"] = 3
    html = _render_macro_with_hero(vm)
    assert ">3 fired conditions today.<" in html
    assert 'data-tip-en="3 fired conditions today."' in html
    assert "3 alert(s) fired" not in html


# --------------------------------------------------------------------------- #
# Live dot uses health tokens (R-D) — never direction tokens
# --------------------------------------------------------------------------- #

def test_live_dot_uses_health_tokens_not_direction():
    """The Live/实时 freshness dot uses `.ud-live--{ok,warn}` modifier classes
    (HEALTH tokens). Direction tokens `.ud-live--{green,yellow,red}` would
    flip red under the ZH 红涨绿跌 convention — they are forbidden."""
    src = (TEMPLATES / "_unified_dashboard_hero.html.j2").read_text()
    rendered = _render_macro_with_hero(_real_vm())
    assert "ud-live--ok" in rendered, (
        "hero template must render health token .ud-live--ok for green/yellow verdict"
    )
    assert "ud-live--green" not in src, (
        "hero template must NOT use direction token .ud-live--green (R-D)"
    )
    assert "ud-live--yellow" not in src, (
        "hero template must NOT use direction token .ud-live--yellow (R-D)"
    )
    assert "ud-live--red" not in src, (
        "hero template must NOT use direction token .ud-live--red (R-D)"
    )
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
    css = (TEMPLATES / "theme.css").read_text()
    assert "ud-verdict-qualifier--down" in css, (
        "theme.css must define .ud-verdict-qualifier--down for RISK_OFF"
    )


# --------------------------------------------------------------------------- #
# Design ratchet: hero template + theme.css land 0 blocking findings on
# the diff.
# --------------------------------------------------------------------------- #

def test_design_system_ratchet_passes_on_added_code():
    """scripts/check_design_system.py --mode enforce-added must return 0
    blocking findings on the B1 diff."""
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
# Stance ink: modifier classes set --c via theme.css, NOT inline --c.
# --------------------------------------------------------------------------- #

def test_hero_stance_uses_class_modifiers_not_inline_custom_property():
    """Every stance chip in the hero must use a `.mx-stance--{ok,warn,muted,down}`
    modifier — not an inline `style="--c:..."`."""
    src = (TEMPLATES / "_unified_dashboard_hero.html.j2").read_text()
    assert "mx-stance--" in src, (
        "hero template must reference the .mx-stance--{...} modifier pattern"
    )
    assert 'style="--c:' not in src
    assert "style='--c:" not in src
    css = (TEMPLATES / "theme.css").read_text()
    for mod in ("ok", "warn", "down", "muted"):
        assert f"mx-stance--{mod}" in css, (
            f"theme.css must define the .mx-stance--{mod} modifier class"
        )


# --------------------------------------------------------------------------- #
# 390 reduction: hero section is the span12 grid item (BLOCKER-2 closed).
# --------------------------------------------------------------------------- #

def test_hero_section_is_span12_grid_item():
    """The hero must occupy a full grid row at every viewport (incl. 390)."""
    src = (TEMPLATES / "_unified_dashboard_hero.html.j2").read_text()
    assert 'class="ud-hero panel span12' in src, (
        "hero section must be the span12 grid item (BLOCKER-2 fix)"
    )
    assert 'class="panel span12 ud-hero-panel"' not in src, (
        "hero must not carry a redundant inner panel.span12 wrapper"
    )


# --------------------------------------------------------------------------- #
# Spine: only US stocks carries a real rail (R-B); ms_history drives the
# month-ago anchor (R-G). Other rows are designed-null.
# --------------------------------------------------------------------------- #

def test_spine_only_us_stocks_has_marker_other_rows_designed_null():
    """Per R-B the macro vm ACTUALLY only carries US stocks regime data; the
    other four rows render as designed-null. Hardcoded specimen stances are
    forbidden. The SUBJECT row (US stocks) IS allowed to carry the same
    stance chip as the hero meta — the spine US stocks row mirrors the
    hero stance by design (spec §3: marker takes the stance's ink)."""
    html = _render_macro_with_hero(_real_vm())
    us_marker_count = html.count('class="mx-spine-mark"')
    assert us_marker_count == 1, (
        f"only US stocks should carry a spine marker; got {us_marker_count}"
    )
    # The hero meta + spine US-stocks row both render the subject stance
    # chip (at most 2 occurrences total). Hardcoded specimen stances on the
    # FOUR SUPPORTING rows would push the count to 6+ — those must NOT appear.
    assert html.count("Watch — don’t chase") <= 2, (
        "spine supporting rows must not duplicate the hero stance chip "
        "(hero meta + subject row = at most 2; supporting rows = 0)"
    )
    # Forbid "Get ready" / "Protect gains" / "Stand aside" appearing on the
    # four supporting rows — those would mean a hardcoded specimen stance
    # leaked onto a BLOCKED_DATA feed. The hero meta may carry one of these
    # once (driven by stance.key), so allow ≤2 (meta + possible subject row).
    for forbidden in ("Get ready", "Protect gains", "Stand aside"):
        assert html.count(forbidden) <= 2, (
            f"hardcoded specimen stance {forbidden!r} appears in the spine "
            f"more than the meta + subject row allowance — supporting rows "
            f"must be designed-null per R-B"
        )
    spine_null_count = html.count("Read being updated")
    assert spine_null_count >= 4, (
        "spine supporting rows must surface the designed-null sentence"
    )


def test_spine_us_stocks_has_spec_section3_geometry():
    """Spec §3: today's marker + month-ago hollow + connector + signed travel.
    R-G: the month-ago anchor uses ms_history (the 50-session path used by the
    hero path chart). When ms_history is long enough, prev/conn markers render.
    Same-day cap gap is FORBIDDEN."""
    html = _render_macro_with_hero(_real_vm())
    assert 'mx-spine-mark' in html, "spec §3: today's solid marker must render"
    assert 'mx-spine-prev' in html, (
        "spec §3: month-ago hollow marker must render when ms_history is long enough"
    )
    assert 'mx-spine-conn' in html, (
        "spec §3: thin connector between prev + today markers must render"
    )
    assert 'mx-spine-arrow' in html, (
        "spec §3: travel figure must render with explicit arrow"
    )
    assert html.count("mx-spine-travel") == 5, (
        f"every spine row must have its own mx-spine-travel; got "
        f"{html.count('mx-spine-travel')}"
    )


def test_spine_short_history_carries_designed_null_travel():
    """R-G: when ms_history is shorter than 22 rows, the spine's month-ago
    anchor is designed-null — the travel column carries an em-dash, NOT a
    same-day cap gap."""
    vm = _real_vm()
    vm["ms_history"] = [{"asof": "2026-09-19", "score": 61}]  # only today's row
    html = _render_macro_with_hero(vm)
    # mx-spine-prev / mx-spine-conn must NOT render (no prior anchor)
    assert 'mx-spine-prev' not in html, (
        "R-G: short history must NOT render a month-ago hollow (no prior anchor)"
    )
    assert 'mx-spine-conn' not in html, (
        "R-G: short history must NOT render a connector (no prior anchor)"
    )


# --------------------------------------------------------------------------- #
# 390 reduction: stance lives in row 1 with name (spec §7).
# --------------------------------------------------------------------------- #

def test_390_mobile_layout_puts_stance_in_name_row():
    """Spec §7 declares row 1 of every spine row = name + stance at 390.
    The CSS must lay the mobile grid out so .mx-spine-name and .mx-spine-stance
    share the first visual row."""
    css = (TEMPLATES / "theme.css").read_text()
    # The canonical @media (max-width:640px) spine rule is the ud-hero
    # block at the end of the file (the older two-column rule was deleted
    # so only ONE spine 640 block remains). Use a brace-balancing scan so
    # sub-blocks don't truncate the match.
    snippet = _last_640_spine_block(css)
    assert snippet, "expected exactly one @media (max-width:640px) spine block"
    assert not re.search(r"\.mx-spine-stance\s*\{\s*display\s*:\s*none", snippet), (
        "390 mobile layout must NOT hide .mx-spine-stance (spec §7 row 1 = name + stance)"
    )
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
    assert "grid-area: name" in snippet or "grid-area:name" in snippet
    assert "grid-area: stance" in snippet or "grid-area:stance" in snippet


def _last_640_spine_block(css: str) -> str | None:
    """Return the body of the LAST @media (max-width:640px) block whose body
    references `.mx-spine-row`. Uses a brace-balancing scan."""
    needle = "@media (max-width:640px)"
    last_body = None
    for m in re.finditer(re.escape(needle), css):
        pos = m.start()
        open_idx = css.find("{", pos)
        if open_idx < 0:
            continue
        depth = 1
        i = open_idx + 1
        while i < len(css) and depth > 0:
            if css[i] == "{":
                depth += 1
            elif css[i] == "}":
                depth -= 1
            i += 1
        if depth != 0:
            continue
        body = css[open_idx + 1:i - 1]
        if "mx-spine-row" in body:
            last_body = body
    return last_body


# --------------------------------------------------------------------------- #
# BLOCKER-2 closed: watching locale CSS paints BOTH head AND body cells in
# each locale. EN body under html:not([data-lang=zh]); ZH head under
# html[data-lang=zh].
# --------------------------------------------------------------------------- #

def test_watching_locale_css_paints_all_four_cells():
    """Per-cell locale display law: BOTH head AND body cells paint in each
    locale. EN: head + body under html:not([data-lang=zh]). ZH: head + body
    under html[data-lang=zh]. The four unhidings live in theme.css."""
    css = (TEMPLATES / "theme.css").read_text()
    # EN head + EN body
    assert "html:not([data-lang=\"zh\"]) body.page-macro .ud-watch-item-head.l-en" in css, (
        "EN watching head must unhide under html:not([data-lang=zh])"
    )
    assert "html:not([data-lang=\"zh\"]) body.page-macro .ud-watch-item-body.l-en" in css, (
        "EN watching body must unhide under html:not([data-lang=zh])"
    )
    # ZH head + ZH body
    assert "html[data-lang=\"zh\"] body.page-macro .ud-watch-item-head.l-zh" in css, (
        "ZH watching head must unhide under html[data-lang=zh]"
    )
    assert "html[data-lang=\"zh\"] body.page-macro .ud-watch-item-body.l-zh" in css, (
        "ZH watching body must unhide under html[data-lang=zh]"
    )


# --------------------------------------------------------------------------- #
# MAJOR-1 / R-J closed: 390 mobile reduction declares drivers swipe strip +
# watching disclosure row.
# --------------------------------------------------------------------------- #

def test_390_drivers_swipe_strip_declared():
    """Spec §7 row 4: at 390, drivers become a horizontal swipe strip with
    cards at ~86% width and a counter chip; the locked (#4) card hides."""
    css = (TEMPLATES / "theme.css").read_text()
    # The ud-hero @media (max-width:390px) block carries the swipe strip
    # + disclosure row declarations. Use a balanced-brace match to skip
    # earlier unrelated 390 blocks (anv2, sector heat, etc.) and grab the
    # ud-hero one.
    snippet = _last_390_block(css)
    assert snippet, "expected an @media (max-width:390px) ud-hero block in theme.css"
    assert "ud-driver-grid" in snippet and "overflow-x:auto" in snippet, (
        "390 mobile must declare .ud-driver-grid as a horizontal scroll container"
    )
    assert "86%" in snippet, (
        "390 mobile must size driver cards at ~86% width"
    )
    assert "ud-driver--locked" in snippet and "display:none" in snippet, (
        "390 mobile must hide the locked (#4) driver card"
    )
    assert "ud-driver-count" in snippet, (
        "390 mobile must surface the 1/N counter chip"
    )


def test_390_watching_disclosure_row_declared():
    """Spec §7 row 5: at 390, three full watching cards collapse into ONE
    disclosure row carrying title + count + chevron. The full list lives
    inside <details> for tap-open."""
    css = (TEMPLATES / "theme.css").read_text()
    snippet = _last_390_block(css)
    assert snippet, "expected an @media (max-width:390px) ud-hero block in theme.css"
    assert re.search(r"\.ud-watch-item\s*\{\s*display\s*:\s*none", snippet), (
        "390 mobile must hide .ud-watch-item by default"
    )
    assert ".ud-watch-summary" in snippet, (
        "390 mobile must surface a .ud-watch-summary row"
    )
    assert "ud-watch-details[open]" in snippet, (
        "390 mobile must reveal the list when <details> opens"
    )


def _last_390_block(css: str) -> str | None:
    """Return the body of the LAST @media (max-width:390px) { ... } block.

    theme.css carries several 390 blocks (anv2 header, sector heat, the
    hero's own); only the LAST one carries the ud-hero declarations. Use
    a brace-balancing scan instead of a non-greedy regex (which stops at
    the first inner closing brace)."""
    needle = "@media (max-width:390px)"
    positions = [m.start() for m in re.finditer(re.escape(needle), css)]
    if not positions:
        return None
    pos = positions[-1]
    # Find the opening brace after the @media line.
    open_idx = css.find("{", pos)
    if open_idx < 0:
        return None
    depth = 1
    i = open_idx + 1
    while i < len(css) and depth > 0:
        if css[i] == "{":
            depth += 1
        elif css[i] == "}":
            depth -= 1
        i += 1
    if depth != 0:
        return None
    return css[open_idx + 1:i - 1]


# --------------------------------------------------------------------------- #
# Contradictory @media 640 spine rules resolved into one canonical block
# --------------------------------------------------------------------------- #

def test_no_contradictory_640_spine_rules():
    """Pre-fix carried TWO @media (max-width:640px) spine rules — one with
    grid-template-columns: minmax(0,1fr) auto, one with grid-template-columns:1fr.
    The contradiction is resolved into ONE canonical block."""
    css = (TEMPLATES / "theme.css").read_text()
    # Find @media (max-width:640px) blocks.
    media_blocks = re.findall(
        r"@media\s*\(max-width:\s*640px\)\s*\{(.*?)\n\}\n", css, re.DOTALL,
    )
    spine_640_blocks = [b for b in media_blocks if "mx-spine-row" in b]
    assert len(spine_640_blocks) == 1, (
        f"exactly ONE @media (max-width:640px) spine rule must exist; "
        f"found {len(spine_640_blocks)}"
    )
    # The kept block must use 1fr (the spec §7 form) — NOT minmax(0,1fr) auto.
    assert "minmax(0, 1fr) auto" not in spine_640_blocks[0], (
        "contradictory minmax(0,1fr) auto spine rule must be gone"
    )


# --------------------------------------------------------------------------- #
# Primary-route proof: the retained candidate must stay off the built macro page.
# --------------------------------------------------------------------------- #

def test_built_macro_page_keeps_unified_candidate_off_primary_route():
    """A regenerated site/macro.html must not reintroduce the stacked UD-B1 hero."""
    site_macro = SITE / "macro.html"
    if not site_macro.exists():
        return
    html = site_macro.read_text(encoding="utf-8")
    assert 'id="ud-hero"' not in html, (
        "built macro page reintroduced the held UD-B1 hero above the current dashboard"
    )
    assert 'id="regime-radar"' in html, (
        "built macro page must retain the established #regime-radar decision surface"
    )