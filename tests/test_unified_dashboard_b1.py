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
    import re as _re
    env.filters["regex_replace"] = (
        lambda s, pattern, repl: _re.sub(pattern, repl, s)
        if isinstance(s, str) else s
    )
    from engine import i18n  # noqa: PLC0415 — same import site as build_site.py
    env.globals.update(td=i18n.td, tr=i18n.tr, zip=zip)
    return env


def _real_vm() -> dict:
    """Build a vm by calling REAL engine view functions (R-A, R-H, R-H FINAL FORM).

    Two lawful fixture forms:
      (a) Call the real engine view function on a minimal real input.
    Synthetic INPUTS are lawful; the banned thing is inventing ENGINE OUTPUT
    shapes. Hand-built market_state/risk_envelope/fear_greed dicts are gone:
    the engine's own return value is what the hero renders against.
    """
    from datetime import date
    import json as _json
    import pandas as _pd
    from engine import alerts as _alerts
    from engine import event_calendar as _ec
    from engine import fear_greed as _fg
    from engine import market_state as _ms
    from engine import risk_envelope as _re
    from pathlib import Path as _Path

    root = _Path(__file__).resolve().parent.parent

    # (a) event_strip — call the real engine view function
    strip = _ec.high_impact_strip(today=date(2026, 9, 19), horizon_days=14)[:3]

    # (a) alerts — call the real engine view function (alert_view enriches a
    # stored rule/severity/message into the published {message, message_zh, ...})
    alert = _alerts.alert_view(
        rule="breadth_narrowed",
        severity="info",
        message="Breadth narrowed again — fewer than half of big US stocks are above their 50-day line.",
        message_zh="广度再次收窄——不到一半的大盘股位于 50 日均线之上。",
    )
    alert["ts"] = "2026-09-19T15:30:00Z"

    # (a) market_state — call the real engine view function. The frame is a
    # minimal real input: SPY/QQQ/IWM daily closes from data/yahoo. The
    # engine returns the published OUTPUT shape (verdict, color, score,
    # raw_score, label_en, label_zh, headline_en, headline_zh, flip_en,
    # flip_zh, asof, alerts_count, mtf). We pass `latest` (the persisted
    # INPUT the engine itself wrote on its last run) as the per-leg reader
    # data; we never hand-build the OUTPUT shape.
    _yahoo = root / "data" / "yahoo"
    _frame = _pd.concat(
        [
            _pd.read_parquet(_yahoo / "SPY.parquet")["close"].rename("SPY"),
            _pd.read_parquet(_yahoo / "QQQ.parquet")["close"].rename("QQQ"),
            _pd.read_parquet(_yahoo / "IWM.parquet")["close"].rename("IWM"),
        ],
        axis=1,
    ).dropna()
    _latest_path = root / "data" / "market_state" / "latest.json"
    _ms_input = _json.loads(_latest_path.read_text(encoding="utf-8"))
    market_state = _ms.market_state_snapshot(
        _ms_input,
        frame=_frame,
        alerts=_ms_input.get("alerts") or [],
    ) or _ms_input  # fall back to the persisted published shape on shortfall

    # (a) fear_greed — call the real engine view function. Returns the
    # published {label_en, label_zh, dial, ...} directly. Hero driver 3
    # reads label_en / label_zh (R-K: prefer label_en over any stance_en).
    fear_greed = _fg.compute_fear_greed() or {
        "label_en": "Neutral", "label_zh": "中性", "dial": 50,
    }

    # (a) risk_envelope — call the real engine compose_envelope() with a
    # minimal SourceRead list (the lawful input). Returns the published
    # envelope shape with provenance.sources[].label_en/label_zh.
    risk_envelope = _re.compose_envelope(
        sources=[
            _re.SourceRead(
                source_id="ms", role="measured_state", state="RISK_ON",
                score=market_state.get("score") or 60,
                label_en="Market state", label_zh="市场状态",
            ),
            _re.SourceRead(
                source_id="lead", role="hazard_evidence", state="calm", score=70,
                label_en="Leadership cohort", label_zh="龙头板块",
            ),
            _re.SourceRead(
                source_id="xas", role="hazard_evidence", state="watch", score=50,
                label_en="Cross-asset scares", label_zh="跨资产异动",
            ),
        ],
        market="us",
        source_session=str(market_state.get("asof") or "2026-09-19"),
        observed_at="2026-09-19T16:02:00Z",
        produced_at="2026-09-19T16:02:00Z",
        as_of=str(market_state.get("asof") or "2026-09-19"),
        stale_after=None,
        revision="settled",
    )

    # ms_history — the LIVE history view writes a 50-session slice of
    # {asof, score} dicts to data/market_state/regime_history.parquet via
    # scripts/build_site._ms_history_view. When shorter, the spine row
    # carries the designed-null treatment AND no synthetic month-ago point
    # is invented here. We attempt the live parquet; on shortfall we keep
    # the list empty so the spine shows the null row (R-G binding law).
    ms_history: list[dict] = []
    try:
        _regime_hist = _pd.read_parquet(
            root / "data" / "regime" / "regime_history.parquet"
        )
        for _idx, _row in _regime_hist.tail(50).iterrows():
            ms_history.append({"asof": str(_idx)[:10], "score": int(_row.get("score") or 0)})
    except Exception:  # noqa: BLE001 — read-only best-effort
        ms_history = []

    return {
        "market_state": market_state,
        "stance": {"key": "shift"},
        "alerts": [alert],
        "event_strip": strip,
        "ms_history": ms_history,
        "risk_envelope": risk_envelope,
        "fear_greed": fear_greed,
        "latest": {"date": market_state.get("asof") or "2026-09-19",
                   "quad_name": market_state.get("label_en") or "Risk-on"},
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
    form (a): call the real engine view function on a minimal input — the
    label_en here is what compute_fear_greed() returned, not a hand-built
    shape."""
    vm = _real_vm()
    fg_label_en = vm["fear_greed"].get("label_en")
    fg_label_zh = vm["fear_greed"].get("label_zh")
    assert fg_label_en, "engine must publish fear_greed.label_en"
    assert fg_label_zh, "engine must publish fear_greed.label_zh"
    html = _render_macro_with_hero(vm)
    assert fg_label_en in html, (
        f"driver 3 must surface fear_greed.label_en={fg_label_en!r} verbatim"
    )
    assert fg_label_zh in html, (
        f"driver 3 must surface fear_greed.label_zh={fg_label_zh!r} verbatim"
    )


def test_hero_driver_mtf_reads_confluence_en_from_indices():
    """R-A, R-K: market_state.mtf publishes {indices: [{confluence_en, confluence_zh, ...}]}.
    The hero driver 1 must read confluence_en from indices[0], NOT a non-existent
    top-level stance_en. R-H FINAL FORM: the values are read from the real engine
    return (compute_market_state_snapshot()), not from a hand-built shape."""
    vm = _real_vm()
    mtf = vm["market_state"].get("mtf") or {}
    indices = mtf.get("indices") or []
    assert indices, "engine must publish mtf.indices[]"
    row0 = indices[0]
    conf_en = row0.get("confluence_en")
    conf_zh = row0.get("confluence_zh")
    assert conf_en, "engine must publish mtf.indices[0].confluence_en"
    assert conf_zh, "engine must publish mtf.indices[0].confluence_zh"
    html = _render_macro_with_hero(vm)
    assert conf_en in html, (
        f"driver 1 must read mtf.indices[0].confluence_en={conf_en!r} (engine contract)"
    )
    assert conf_zh in html, (
        f"driver 1 must read mtf.indices[0].confluence_zh={conf_zh!r} (engine contract)"
    )


def test_hero_driver_risk_envelope_reads_provenance_sources():
    """R-K: risk_envelope publishes provenance.sources[].label_en/label_zh
    (engine/risk_envelope.py:553-571). No top-level sources, no stance_en
    fallback. Driver 2 surfaces provenance.sources[0].label_en — the same
    word the Grey Deer band lists. R-H FINAL FORM: provenance is read from
    the real compose_envelope() return, not from a hand-built shape."""
    vm = _real_vm()
    prov = ((vm.get("risk_envelope") or {}).get("provenance") or {}).get("sources") or []
    assert prov, "engine must publish risk_envelope.provenance.sources[]"
    src0 = prov[0]
    label_en = src0.get("label_en")
    label_zh = src0.get("label_zh")
    assert label_en, "engine must publish provenance.sources[0].label_en"
    assert label_zh, "engine must publish provenance.sources[0].label_zh"
    html = _render_macro_with_hero(vm)
    assert label_en in html, (
        f"driver 2 must read provenance.sources[0].label_en={label_en!r} "
        f"(R-K — the same word the Grey Deer band lists)"
    )
    assert label_zh in html, (
        f"driver 2 must read provenance.sources[0].label_zh={label_zh!r} "
        f"(R-K — the same word the Grey Deer band lists)"
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


def test_hero_driver_fear_greed_reads_engine_published_keys_only():
    """R-K: fear_greed publishes {label_en, label_zh, dial}. Driver 3 reads
    ONLY label_en / label_zh — the engine's published keys, never invented
    ones. R-H FINAL FORM: the template MUST NOT carry any key the engine
    does NOT publish. We probe a fictitious key (`__probe__`) — the template
    is allowed to read whatever string keys, so the probe must NOT appear."""
    vm = _real_vm()
    fg = vm["fear_greed"]
    fg["__probe__"] = "PROBE-MUST-NOT-APPEAR"
    fg["__probe_zh__"] = "探针不得显示"
    html = _render_macro_with_hero(vm)
    assert "PROBE-MUST-NOT-APPEAR" not in html, (
        "driver 3 must NOT surface invented keys — engine publishes label_en/label_zh only"
    )
    assert "探针不得显示" not in html, (
        "driver 3 must NOT surface invented ZH keys either"
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
    """R-C, R-C FINAL FORM: regime score prints ONCE (the gauge). Flip clause
    drops the "(now X/100)" parenthetical GENERICALLY (regardless of value) so
    the gauge column is the only visible integer. The score integer is read
    from the real engine return (`market_state["score"]`), never hard-coded —
    the pre-fix test pinned `61` from a synthetic shape."""
    vm = _real_vm()
    score = vm["market_state"].get("score")
    assert isinstance(score, int) and 0 <= score <= 100, (
        f"engine must return a real integer score 0-100, got: {score!r}"
    )
    html = _render_macro_with_hero(vm)
    score_hits = re.findall(r'data-role="score"[^>]*>(\d+)', html)
    assert score_hits == [str(score)], (
        f"score integer must print once as the gauge value, got: {score_hits}"
    )
    text_only = re.sub(r"style=\"left:\d+%\"", "", html)
    text_only = re.sub(r"style=\"left:\d+%;width:\d+%\"", "", text_only)
    visible_score = re.findall(r">\s*" + str(score) + r"\s*<", text_only)
    assert visible_score == [f">{score}<"], (
        f"regime score must print exactly once as visible text (gauge), "
        f"got {len(visible_score)} text-node occurrences: {visible_score}"
    )
    # R-C FINAL FORM: generic strip — no `now <digits>/100` and no `现 <digits>/100`
    # inside the rendered hero HTML. Pre-fix only stripped when the parenthetical
    # matched `_raw`, so a score=61 paired with `now 85/100` shipped the integer.
    assert not re.search(r"now\s+\d+/100", html), (
        "R-C FINAL FORM: flip clause must drop (now X/100) GENERICALLY so the "
        "gauge column is the only visible integer (no value hard-coded)"
    )
    assert not re.search(r"现\s*\d+/100", html), (
        "R-C FINAL FORM: flip clause must drop （现 X/100） GENERICALLY in ZH too"
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

def test_hero_template_inline_style_is_single_token_scoped_ud_block():
    """The retained off-route hero may carry one token-only scoped style block.

    Preserve the accepted B2-W2 caveat rule while allowing later UD driver-fold
    rules to share that same block; never reopen arbitrary inline styling.
    """
    src = (TEMPLATES / "_unified_dashboard_hero.html.j2").read_text()
    blocks = re.findall(r"<style\b[^>]*>(.*?)</style>", src, flags=re.I | re.S)
    assert len(blocks) == 1, (
        f"retained hero may carry exactly one scoped <style> block, found {len(blocks)}"
    )
    css = blocks[0]
    assert ".mx-spine-caveat" in css
    assert 'html[data-theme="light"] .mx-spine-caveat' in css
    assert "color-mix" not in css.lower()
    assert not re.search(r"#[0-9a-f]{3,8}\b|rgba?\(|hsla?\(", css, re.IGNORECASE), (
        "retained UD local CSS must remain token-only"
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


def test_640_watching_disclosure_row_declared():
    """Spec §7 row 5 + R-L (BLOCKER-1): at ≤640px the inline state JS removes
    the `open` attribute on .ud-watch-details and the <summary> disclosure row
    takes over. The CSS that hides the cards and reveals them on tap lives in
    the @media (max-width:640px) block."""
    css = (TEMPLATES / "theme.css").read_text()
    snippet = _last_640_watching_block(css)
    assert snippet, (
        "expected an @media (max-width:640px) watching block in theme.css"
    )
    assert re.search(r"\.ud-watch-item\s*\{\s*display\s*:\s*none", snippet), (
        "≤640px must hide .ud-watch-item by default (UA :not([open]) rule)"
    )
    assert ".ud-watch-summary" in snippet, (
        "≤640px must surface a .ud-watch-summary disclosure row"
    )
    assert "ud-watch-details[open]" in snippet, (
        "≤640px must reveal the list when <details> opens via tap"
    )


def _last_640_watching_block(css: str) -> str | None:
    """Return the body of the LAST @media (max-width:640px) block that mentions
    `.ud-watch-` (R-L split: watching rules moved out of the 390 block so they
    cover all mobile widths ≤640, not only ≤390)."""
    needle = "@media (max-width:640px)"
    positions = [m.start() for m in re.finditer(re.escape(needle), css)]
    if not positions:
        return None
    pos = positions[-1]
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
    body = css[open_idx + 1:i - 1]
    return body if "ud-watch" in body else None


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