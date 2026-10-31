"""Render-level guards for the Options Pulse section on aibrief.html.

Renders the REAL templates/aibrief.html.j2 through the REAL builder environment
(same Jinja env, same autoescape=False, same i18n globals as
scripts/build_aibrief.main()) and, for the end-to-end case, runs the REAL
build_aibrief.main() with its site_dir redirected to a tmp_path so the committed
site/ tree is never touched.

These tests exist to catch the failure modes the projector cannot see on its own:
a section that silently breaks a sibling panel, an escaping hole opened by the
page's autoescape=False, a new third-party runtime, or an absent source taking
the rest of the page down with it.
"""
from __future__ import annotations

import copy
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

import jinja2
import pytest

from engine import i18n
from engine import options_pulse as op
from lib import config
from scripts import build_aibrief

NOW = datetime(2026, 10, 22, 18, 30, tzinfo=timezone.utc)
ASOF = "2026-10-21"

GATE = {"scored": False, "direction_reliable": False, "asof": "2026-06-21"}
INTEL = {"schema": "options.intel_brief/v1", "model_version": "intel_brief_heuristic/v1.2",
         "as_of_session": ASOF, "board_state": "INSUFFICIENT_COVERAGE",
         "pending_reason": "OI_NOT_YET_SETTLED"}


def _profile(spot=100.0, sign=-1.0, n=81):
    xs = [round(spot * (0.85 + 0.30 * i / (n - 1)), 2) for i in range(n)]
    ys = [round(sign * (5.0 - abs(i - n // 2) * 0.1), 4) for i in range(n)]
    return {"spots": xs, "gamma_bn": ys, "flip": round(spot * 1.037, 2), "spot": spot}


def _payload(**meta):
    p = {
        "meta": {"key": "QQQ", "en": "Nasdaq 100 ETF", "zh": "纳指100 ETF",
                 "grp": "ETF", "src": "core", "asof": ASOF},
        "summary": {"spot": 100.0, "tier": "full", "n_strikes": 5032,
                    "net_gex_bn": -5.0, "gamma_flip": 103.5, "gamma_regime": "short",
                    "regime_passport": {"basis": "assumption", "verdict": "display-only",
                                        "is_index_product": True}},
        "profile": _profile(),
        "walls": {"by_strike": [{"K": 110.0, "net_mn": 574.91, "pct": 57.7},
                                {"K": 90.0, "net_mn": -120.5, "pct": 10.0}],
                  "call_wall": 110.0, "put_wall": 90.0, "max_abs_mn": 574.91},
    }
    p["meta"].update(meta)
    return p


_MISSING = object()


def _pulse(payload=_MISSING, *, symbol="QQQ", gate=None, intel=None, now=NOW):
    return op.build_pulse(
        symbol=symbol,
        gex=_payload() if payload is _MISSING else payload,
        gex_file="site/gex/QQQ.json", gex_digest="sha256:aa",
        intel=INTEL if intel is None else intel,
        intel_file="site/options_intel_brief.json", intel_digest="sha256:bb",
        gate=GATE if gate is None else gate,
        gate_file="data/options_flow/signing_gate.json", gate_digest="sha256:cc",
        now=now, reference_session=date(2026, 10, 21),
    )


def _env() -> jinja2.Environment:
    """Mirror scripts/build_aibrief.main()'s template environment EXACTLY —
    including autoescape=False, which is why the section escapes explicitly."""
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(config.ROOT / "templates"), autoescape=False)
    env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    return env


def _render(pulse, **overrides):
    panels = {
        "ctx_strip": {"absent": True},
        "fwd_panel": {"absent": True, "events": [], "rebal_note_en": None},
        "record_panel": {"absent": True},
        "am_edition": {"absent": True},
        "options_pulse": pulse,
        "master_brief": None, "china_brief": None, "btc_brief": None,
    }
    panels.update(overrides)
    as_of = overrides.pop("as_of", "2026-10-22 18:30 UTC") if panels is overrides \
        else panels.pop("as_of", "2026-10-22 18:30 UTC")
    return _env().get_template("aibrief.html.j2").render(as_of=as_of, **panels)


# ─────────────────────────── structure ───────────────────────────────────────
def test_section_renders_inside_the_existing_macro_lens():
    html = _render(_pulse())
    assert 'class="opulse"' in html
    macro_at = html.index('<div class="panel ai-brief brief-tab active" data-lens="macro">')
    china_at = html.index('<div class="panel ai-brief brief-tab" data-lens="china">')
    pulse_at = html.index('<section class="opulse"')
    assert macro_at < pulse_at < china_at, "the card must live INSIDE the macro lens"


def test_no_new_page_or_tab_is_introduced():
    html = _render(_pulse())
    assert html.count('class="brief-tab-btn') == 3, "still exactly the three existing lens tabs"
    assert html.count('class="panel ai-brief brief-tab') == 3
    for lens in ("macro", "china", "btc"):
        assert f'data-lens="{lens}"' in html


def test_other_panels_survive_the_section():
    html = _render(_pulse())
    for marker in ("Morning Orientation", "cortex-panel", "site-footer",
                   "site-nav", "theme.css", "aibrief.js"):
        assert marker in html, f"{marker} must survive the Options Pulse section"


def test_absent_briefs_still_render_their_honest_note():
    html = _render(_pulse())
    assert "This brief has not generated yet" in html


def test_missing_source_renders_an_explicit_unavailable_section():
    html = _render(_pulse(payload=None, symbol="QQQ"))
    assert 'class="opulse"' in html
    assert "unavailable for this symbol" in html
    assert "source_missing" in html
    # and the rest of the page is intact
    assert html.count('class="brief-tab-btn') == 3
    assert "cortex-panel" in html


def test_no_pulse_context_renders_nothing_and_does_not_break():
    html = _render(_pulse(), options_pulse=None)
    assert 'class="opulse"' not in html
    assert html.count('class="brief-tab-btn') == 3
    assert "cortex-panel" in html


def test_malformed_source_renders_the_unavailable_state_not_a_crash():
    html = _render(_pulse(_payload(asof="garbage")))
    assert 'class="opulse"' in html
    assert "session_missing" in html


# ─────────────────────────── escaping ────────────────────────────────────────
def test_page_env_really_is_autoescape_false():
    """The whole reason the section escapes by hand. Pin it so a future
    autoescape flip does not silently hide a missing |e."""
    assert _env().autoescape is False


@pytest.mark.parametrize("hostile", [
    "<script>alert('xss')</script>",
    '"><img src=x onerror=alert(1)>',
    "</dd><script>alert(2)</script><dd>",
    "javascript:alert(3)",
    "\"><svg onload=alert(4)>",
])
def test_hostile_external_strings_are_escaped_in_the_rendered_html(hostile):
    """This page's env is autoescape=False, so the section escapes by hand. The
    contract is INERTNESS: a payload string may never appear verbatim in a
    position that lets it become markup, and may never reach an attribute."""
    payload = _payload()
    payload["meta"]["en"] = hostile
    payload["meta"]["zh"] = hostile
    html = _render(_pulse(payload))
    start = html.index('<section class="opulse"')
    card = html[start:html.index("</section>", start)]

    if any(ch in hostile for ch in ('<', '>', '"', "'", '&')):
        # every HTML-special character is entity-encoded, so the payload can never
        # re-enter the parse as a tag
        assert hostile not in card, "hostile payload reached the DOM verbatim"
        assert ("&lt;" in card) or ("&#34;" in card) or ("&gt;" in card)

    # the card never forges a script or an image out of payload text
    assert "<script" not in card.lower()
    assert "<img" not in card.lower()
    # exactly one <svg> — the chart this section itself renders
    assert card.lower().count("<svg") == 1
    assert 'class="opulse-chart"' in card

    # no hostile text may land in an attribute position
    for attr in re.findall(r'(?:href|src|aria-label|data-tip-en|data-tip-zh)\s*=\s*"([^"]*)"', card):
        for banned in ("javascript:", "onerror", "onload", "<script", "<img"):
            assert banned not in attr.lower()


def test_hostile_reasons_and_narrative_values_are_escaped():
    payload = _payload()
    payload["meta"]["asof"] = "2026-10-21"     # keep the session valid
    payload["identity_poison"] = "<b>x</b>"     # ignored by the projector
    html = _render(_pulse(payload))
    assert "<b>x</b>" not in html


# ─────────────────────────── honesty in the DOM ──────────────────────────────
def test_probability_and_signed_flow_are_withheld_in_the_dom():
    html = _render(_pulse())
    assert "Closing probability — unavailable" in html
    assert "Signed flow & bullish expiry share — unavailable" in html
    assert "direction_reliable" in html            # the reason is shown
    assert "RESEARCH_ONLY" in html


def test_no_trade_authority_language_anywhere_in_the_card():
    html = _render(_pulse())
    card = html[html.index('class="opulse"'):]
    card = card[:card.index("</section>")]
    for banned in ("should buy", "should sell", "we recommend", "price target",
                   "guaranteed floor", "guaranteed cap", "trade this"):
        assert banned.lower() not in card.lower()


def test_concentrations_are_labelled_never_a_target():
    html = _render(_pulse())
    assert "never a floor, cap or target" in html


def test_hedging_bars_are_labelled_linear_and_assumption_based():
    html = _render(_pulse())
    assert "linear, assumption-based" in html
    assert "not an exact nonlinear hedge trade" in html
    assert "reference notional" in html


def test_display_only_disclaimer_is_present():
    html = _render(_pulse())
    assert "Display-only" in html
    assert "no trade, rank, size or alert authority" in html


# ─────────────────────────── bilingual + theme ───────────────────────────────
def test_card_is_bilingual_en_and_zh():
    html = _render(_pulse())
    card = html[html.index('class="opulse"'):]
    assert 'class="l-en"' in card and 'class="l-zh"' in card
    assert "期权脉搏" in card          # ZH eyebrow
    assert "Options pulse" in card    # EN eyebrow


def test_probability_alternatives_are_bilingual():
    """Every l-en string in the card needs an l-zh twin; an English-only
    alternative list reads as a translation bug in ZH."""
    html = _render(_pulse())
    start = html.index('<section class="opulse"')
    card = html[start:html.index("</section>", start)]
    prob = card[card.index("Closing probability"):card.index("Signed flow")]
    assert prob.count('class="l-en"') == prob.count('class="l-zh"') >= 3


def test_sensitivity_unit_line_is_bilingual():
    html = _render(_pulse())
    start = html.index('<section class="opulse"')
    card = html[start:html.index("</section>", start)]
    line = card[card.index("reference notional"):card.index("reference notional") + 400]
    assert 'class="l-en"' in line and 'class="l-zh"' in line


def test_card_uses_only_existing_theme_tokens():
    css = (config.ROOT / "templates" / "_options_pulse_css.j2").read_text()
    tokens = set(re.findall(r"var\(--([a-z0-9-]+)\)", css))
    assert tokens, "the card must style from theme tokens"
    assert tokens <= {"bg", "panel", "panel2", "text", "muted", "line", "link",
                      "up", "down", "warn", "ok", "orange", "act"}
    # no hardcoded hex, and no invented palette family
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b", css)


def test_no_container_carries_a_coloured_edge_accent():
    """Chairman design rule: no coloured left/right edge or accent stripe."""
    css = (config.ROOT / "templates" / "_options_pulse_css.j2").read_text()
    for banned in ("border-left", "border-right", "border-inline-start",
                   "border-inline-end"):
        assert banned not in css, f"{banned} is a banned accent stripe"


def test_dark_and_light_are_both_served_from_the_same_token_names():
    theme = (config.ROOT / "templates" / "theme.css").read_text()
    for token in ("--panel", "--panel2", "--line", "--muted"):
        dark = theme.split('html[data-theme="dark"]')[-1] if 'html[data-theme="dark"]' in theme else theme
        assert theme.count(token + ":") >= 2, f"{token} must exist in BOTH themes"


def test_chart_is_svg_from_validated_numbers_with_a_text_fallback():
    html = _render(_pulse())
    assert '<svg class="opulse-chart"' in html
    assert 'role="img"' in html
    assert 'aria-label=' in html
    assert re.search(r'<path class="opulse-curve[^"]*"\s+d="M -?[\d.]+,-?[\d.]+', html)
    # the deterministic table IS the fallback
    assert '<table class="opulse-table">' in html
    assert '<th scope="col">' in html and '<th scope="row">' in html


def test_viewport_and_responsive_breakpoint_present():
    html = _render(_pulse())
    assert 'name="viewport"' in html
    css = (config.ROOT / "templates" / "_options_pulse_css.j2").read_text()
    assert "@media (max-width:480px)" in css


# ─────────────────────────── no new runtime ──────────────────────────────────
def test_card_adds_no_third_party_script_telemetry_fetch_auth_or_storage():
    html = _render(_pulse())
    card_start = html.index('class="opulse"')
    card = html[card_start:html.index("</section>", card_start)]
    for banned in ("<script", "fetch(", "XMLHttpRequest", "localStorage",
                   "sessionStorage", "document.cookie", "gtag", "dataLayer",
                   "sendBeacon", "WebSocket", "navigator.sendBeacon"):
        assert banned not in card, f"the card must not carry {banned!r}"


def test_no_new_script_tag_is_added_to_the_page():
    with_card = _render(_pulse())
    without_card = _render(_pulse(), options_pulse=None)
    assert with_card.count("<script") == without_card.count("<script")


def test_detail_link_is_local_only():
    html = _render(_pulse())
    assert 'href="gex.html"' in html
    for banned in ("http://", "https://", "//cdn"):
        assert banned not in html[html.index('class="opulse"'):html.index("</section>")]


# ─────────────────────────── determinism / zero-AI ───────────────────────────
def test_zero_ai_deterministic_path_renders_identical_html():
    """No AI is reachable from this card: two renders at different build clocks
    differ ONLY in the page's own as_of stamp, never in the section."""
    a = _render(_pulse(), as_of=None)
    b = _render(_pulse(), as_of=None)
    assert a == b
    assert _pulse()["content_hash"] == _pulse(
        now=datetime(2026, 10, 22, 23, 0, tzinfo=timezone.utc))["content_hash"]


def test_section_numbers_are_stable_across_a_different_build_clock():
    """The clock is environment: it may move the FRESHNESS LABEL, never a number.
    Every projected value and the content hash must be byte-identical."""
    a = _pulse(now=datetime(2026, 10, 22, 18, 30, tzinfo=timezone.utc))
    b = _pulse(now=datetime(2026, 10, 23, 9, 0, tzinfo=timezone.utc))
    for key in ("net_gamma_bn_per_1pct", "regime", "spot", "crossing", "profile_points"):
        assert a["gamma"][key] == b["gamma"][key]
    assert a["hedge"]["up_1pct_bn"] == b["hedge"]["up_1pct_bn"]
    assert a["hedge"]["down_1pct_bn"] == b["hedge"]["down_1pct_bn"]
    assert a["concentrations"]["rows"] == b["concentrations"]["rows"]
    assert a["chart"]["path"] == b["chart"]["path"]
    assert a["content_hash"] == b["content_hash"]
    # the label is allowed to differ, and does
    assert a["assessment"]["evaluated_utc"] != b["assessment"]["evaluated_utc"]


def test_context_hash_is_printed_as_a_receipt():
    html = _render(_pulse())
    assert re.search(r"sha256:[0-9a-f]{64}", html)


# ─────────────────────────── real builder, end to end ────────────────────────
def _seed_site(site_dir: Path, *, with_gex=True):
    (site_dir / "gex").mkdir(parents=True, exist_ok=True)
    if with_gex:
        (site_dir / "gex" / "QQQ.json").write_text(json.dumps(_payload()))
    (site_dir / "options_intel_brief.json").write_text(json.dumps(INTEL))
    for name in ("master_brief.json", "china_brief.json", "btc_brief.json"):
        (site_dir / name).write_text(json.dumps({"summary": "ok", "tldr": "ok"}))
    (site_dir / "am_edition.json").write_text(json.dumps(
        {"session_state": "CLOSED", "generated_at": "2026-10-21T20:00:00",
         "blocks": [{"key": "tape_since_prior_close",
                     "rows": [{"symbol": "QQQ", "label_en": "Nasdaq 100",
                               "change_pct": 1.2}]}]}))


def _run_builder(tmp_path: Path, monkeypatch, *, with_gex=True) -> Path:
    site_dir = tmp_path / "site"
    _seed_site(site_dir, with_gex=with_gex)
    real_load = config.load

    def _patched_load():
        cfg = copy.deepcopy(real_load())
        cfg["storage"]["site_dir"] = str(site_dir)
        return cfg

    monkeypatch.setattr(config, "load", _patched_load)
    assert build_aibrief.main() == 0, "the builder must always return 0 (fail-open)"
    return site_dir / "aibrief.html"


def test_real_builder_renders_the_section_end_to_end(tmp_path, monkeypatch):
    out = _run_builder(tmp_path, monkeypatch)
    html = out.read_text()
    assert 'class="opulse"' in html
    assert "QQQ" in html
    assert "Directional" not in html          # never labelled live/directional
    assert html.count('class="brief-tab-btn') == 3
    assert "cortex-panel" in html


def test_real_builder_survives_a_missing_options_source(tmp_path, monkeypatch):
    out = _run_builder(tmp_path, monkeypatch, with_gex=False)
    html = out.read_text()
    assert "unavailable for this symbol" in html
    assert "source_missing" in html
    # every other panel still made it to the page
    assert html.count('class="brief-tab-btn') == 3
    assert "Morning Orientation" in html
    assert "cortex-panel" in html
    assert "site-footer" in html


def test_real_builder_gather_matches_the_projector_directly(tmp_path, monkeypatch):
    """The builder must not reinterpret the payload: its card and a direct
    projector call agree on the content hash."""
    site_dir = tmp_path / "site"
    _seed_site(site_dir)
    real_load = config.load

    def _patched_load():
        cfg = copy.deepcopy(real_load())
        cfg["storage"]["site_dir"] = str(site_dir)
        return cfg

    monkeypatch.setattr(config, "load", _patched_load)
    gathered = build_aibrief._gather_options_pulse(site_dir, config.ROOT / "data")
    direct = _pulse()
    assert gathered is not None
    assert gathered["gamma"]["net_gamma_bn_per_1pct"] == direct["gamma"]["net_gamma_bn_per_1pct"]
    assert gathered["concentrations"]["call_wall"] == direct["concentrations"]["call_wall"]
    assert gathered["authority"] == direct["authority"]


def test_builder_never_refuses_to_build_over_bad_options_bytes(tmp_path, monkeypatch):
    site_dir = tmp_path / "site"
    _seed_site(site_dir)
    (site_dir / "gex" / "QQQ.json").write_text("{ this is not json")
    real_load = config.load

    def _patched_load():
        cfg = copy.deepcopy(real_load())
        cfg["storage"]["site_dir"] = str(site_dir)
        return cfg

    monkeypatch.setattr(config, "load", _patched_load)
    assert build_aibrief.main() == 0
    html = (site_dir / "aibrief.html").read_text()
    assert "source_missing" in html
    assert html.count('class="brief-tab-btn') == 3


# ─────────────────────────── shared projector ────────────────────────────────
def test_display_and_model_context_share_one_projector():
    """The page card and the master_brain context must be the SAME projection,
    never two interpretations of one payload."""
    from engine import master_brain

    raw = (config.ROOT / "site" / "gex" / "QQQ.json").read_bytes()
    direct = op.build_pulse(
        symbol="QQQ", gex=json.loads(raw), gex_file="site/gex/QQQ.json",
        gex_digest=op.digest_bytes(raw), now=NOW,
        reference_session=date(2026, 10, 21))
    ctx = master_brain.gather_state(config.ROOT).get("options_pulse")
    assert ctx is not None
    assert ctx["symbol"] == direct["symbol"]
    assert ctx["call_wall"] == direct["concentrations"]["call_wall"]
    assert ctx["put_wall"] == direct["concentrations"]["put_wall"]
    assert ctx["net_gamma_bn_per_1pct"] == direct["gamma"]["net_gamma_bn_per_1pct"]
    assert ctx["authority"] == direct["authority"]
    assert ctx["display_only"] is True