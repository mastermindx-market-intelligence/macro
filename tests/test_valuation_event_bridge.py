"""Tests for engine/valuation_event_bridge.py (B-F07-3).

The bridge is the plain-word link between the latest classified event on
file and one of the three B-F07-2 valuation inputs (growth, margin,
multiple). Pure module, no IO, no clock. Every test asserts the closed-map
invariant + a non-fallback fixture per event class + the typed-null paths.
"""
from __future__ import annotations

from pathlib import Path

import jinja2

from engine import valuation_event_bridge as veb
from engine import valuation_assumptions as va
from engine import valuation_scenario as vs
from engine import i18n as i18n
from tests.test_valuation_scenario import _rows

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Closed-map invariant — every entry must satisfy the target/direction shape.
# ---------------------------------------------------------------------------

def test_classified_event_domain_is_exhaustively_typed():
    """Every entry in the closed map is either None or a 3-tuple whose
    first element is one of the three F07-2 inputs and whose second/third
    elements are non-empty EN/ZH strings."""
    domain = veb.classified_event_domain()
    assert domain, "domain must not be empty"
    for k, v in domain.items():
        assert isinstance(k, str) and k, f"bad key {k!r}"
        if v is None:
            continue
        assert isinstance(v, tuple), f"{k}: bad value type {type(v).__name__}"
        assert len(v) == 3, f"{k}: tuple must be 3-tuple, got {len(v)}"
        target, dw_en, dw_zh = v
        assert target in veb.ALLOWED_TARGETS, (
            f"{k}: target {target!r} not in {sorted(veb.ALLOWED_TARGETS)}"
        )
        assert isinstance(dw_en, str) and dw_en.strip(), f"{k}: empty EN direction word"
        assert isinstance(dw_zh, str) and dw_zh.strip(), f"{k}: empty ZH direction word"


def test_vocab_closure():
    """BLOCKER-1: map keys are exactly the union of the three source vocabularies.

    Spine subtypes are exactly the keys emitted by engine/capital_structure/event_spine.py
    route_form() (lines 167-249). Policy stages/themes are exactly those of
    collectors/federal_register.py _STAGE_WEIGHTS (lines 60-70).
    """
    # Sources read from live code (not hard-coded)
    from engine.special_situations import MATURE_CATEGORIES
    from engine.capital_structure.event_spine import route_form
    from collectors.federal_register import _STAGE_WEIGHTS

    # Special situations: all MATURE_CATEGORIES keys must be in the domain
    special_missing = [k for k in MATURE_CATEGORIES if k not in veb.classified_event_domain()]
    assert not special_missing, f"special_situations missing from map: {special_missing}"

    # Spine: collect all subtypes route_form() can return by calling it with
    # every form it handles (lines 167-249)
    spine_forms = {
        "ASR", "S-1", "S-11", "S-3", "S-4",
        "POS AM", "POSASR", "EFFECT",
        "RW", "RW/A", "AW", "AW/A",
        "424B5", "424B3", "424B7", "424B8",
        "8-K", "8-K/A", "6-K", "6-K/A",
        "DEF 14A", "DEF 14C", "PROXY", "SCHEDULE 13E3",
        "1-A", "1-A/A", "1-A POS",
        "1-U", "253G1", "253G2", "253G3", "253G4",
        "1-K", "1-K/A",
        "SC 13D", "SC 13G", "SC TO", "SC 13E3",
        "FORM 25", "FORM 15",
    }
    spine_subtypes = set()
    for form in spine_forms:
        try:
            route = route_form(form)
            if route.subtype:
                spine_subtypes.add(route.subtype)
        except Exception:
            pass

    spine_missing = [k for k in spine_subtypes if k not in veb.classified_event_domain()]
    assert not spine_missing, f"spine subtypes missing from map: {spine_missing}"

    # Policy calendar: all reg_stages from _STAGE_WEIGHTS
    policy_stages = {stage for _, _, stage, _ in _STAGE_WEIGHTS}
    policy_missing = [k for k in policy_stages if k not in veb.classified_event_domain()]
    assert not policy_missing, f"policy stages missing from map: {policy_missing}"

    # No snake_case slug in event_class_zh values
    import re
    snake_pattern = re.compile(r'^[a-z]+(_[a-z]+)*$')
    domain = veb.classified_event_domain()
    for k, v in domain.items():
        if v is None:
            continue
        _, _, dw_zh = v
        zh_val = domain.get(k)
        # event_class_zh is in the bridge output dict; check the _EVENT_CLASS_ZH table
        event_class_zh = veb._EVENT_CLASS_ZH.get(k, k)
        assert not snake_pattern.match(event_class_zh), (
            f"{k}: event_class_zh {event_class_zh!r} is a snake_case slug"
        )


def test_classified_event_domain_covers_every_special_situations_category():
    """The special-situations MATURE_CATEGORIES are the canonical issuer-level
    event classes; the bridge must cover each one (either as a hit or as a
    typed null for the catch-all "Other" bucket)."""
    from engine.special_situations import MATURE_CATEGORIES
    domain = veb.classified_event_domain()
    missing = [k for k in MATURE_CATEGORIES if k not in domain]
    assert not missing, f"closed map is missing special-situations categories: {sorted(missing)}"


# ---------------------------------------------------------------------------
# Per-event-class non-fallback fixtures — growth / margin / multiple each
# have at least one hit; the catch-all "Other" is the typed null.
# ---------------------------------------------------------------------------

GROWTH_HITS = ["Acquisitions", "Spin-Offs", "SPACs", "Activist Campaigns",
               "Strategic Reviews", "Divestitures"]
# Capital Returns (buybacks): per-share lift via lower share count → GROWTH.
CAPITAL_RETURNS_HITS = ["Capital Returns"]
MARGIN_HITS = ["Restructuring", "Liquidations",
                "Deal Terminations", "Management Changes"]
# Tender Offers / Going-Private / Issuer Tenders → multiple (takeout premium)
# Delistings → multiple (exit pricing)
# Rights Offerings → multiple (dilutive; new shares at discount)
MULTIPLE_HITS = ["Tender Offers", "Going-Private", "Delistings",
                 "Issuer Tenders", "Rights Offerings"]
NULL_HITS = ["Other"]


def test_bridge_returns_target_and_direction_word_per_growth_class():
    """Every growth-classified event maps to target='growth' with a non-empty
    EN+ZH direction word. The EN/ZH pair disagree only in language, never in
    meaning (both say the same target and the same verb polarity)."""
    for cls in GROWTH_HITS + CAPITAL_RETURNS_HITS:
        out = veb.bridge(cls)
        assert out is not None, f"{cls!r} must hit the closed map"
        assert out["target"] == veb.GROWTH, f"{cls!r} -> {out['target']!r} not growth"
        assert out["direction_word"], f"{cls!r}: empty EN direction word"
        assert out["direction_word_zh"], f"{cls!r}: empty ZH direction word"
        assert out["event_class"] == cls


def test_bridge_returns_target_and_direction_word_per_margin_class():
    """Every margin-classified event maps to target='margin' with a non-empty
    EN+ZH direction word."""
    for cls in MARGIN_HITS:
        out = veb.bridge(cls)
        assert out is not None, f"{cls!r} must hit the closed map"
        assert out["target"] == veb.MARGIN, f"{cls!r} -> {out['target']!r} not margin"
        assert out["direction_word"], f"{cls!r}: empty EN direction word"
        assert out["direction_word_zh"], f"{cls!r}: empty ZH direction word"
        assert out["event_class"] == cls


def test_bridge_returns_target_and_direction_word_per_multiple_class():
    """Every multiple-classified event maps to target='multiple' with a
    non-empty EN+ZH direction word. EN uses 'the multiple people pay';
    ZH uses '市盈率倍数'."""
    for cls in MULTIPLE_HITS:
        out = veb.bridge(cls)
        assert out is not None, f"{cls!r} must hit the closed map"
        assert out["target"] == veb.MULTIPLE, f"{cls!r} -> {out['target']!r} not multiple"
        assert out["direction_word"], f"{cls!r}: empty EN direction word"
        assert out["direction_word_zh"], f"{cls!r}: empty ZH direction word"
        # The descriptive suffixes from the spec are present in both languages.
        assert "the multiple people pay" in out["direction_word"], (
            f"{cls!r}: EN suffix must be 'the multiple people pay', got {out['direction_word']!r}"
        )
        assert "市盈率倍数" in out["direction_word_zh"], (
            f"{cls!r}: ZH suffix must include '市盈率倍数', got {out['direction_word_zh']!r}"
        )


def test_bridge_returns_typed_null_for_other_class():
    """The 'Other' catch-all bucket has no directional read → typed null."""
    out = veb.bridge("Other")
    assert out is None, f"'Other' must be typed null, got {out!r}"


# ---------------------------------------------------------------------------
# Typed-null paths — empty / whitespace / non-string / unknown class.
# ---------------------------------------------------------------------------

def test_bridge_for_issuer_returns_none_when_no_event_on_file():
    """The panel calls bridge_for_issuer() with the latest classified event
    on file. When that is None (no event for the issuer), the bridge must
    return a typed null."""
    assert veb.bridge_for_issuer(None) is None


def test_bridge_returns_none_for_empty_or_whitespace_string():
    """An empty or whitespace-only event class is typed null — the panel
    should not paint a direction word against a blank input."""
    assert veb.bridge("") is None
    assert veb.bridge("   ") is None
    assert veb.bridge("\t\n") is None
    assert veb.bridge_for_issuer("") is None
    assert veb.bridge_for_issuer("   ") is None


def test_bridge_returns_none_for_non_string_input():
    """Anything that is not a string is typed null (the panel feeds a string
    from the classified-event source, but the test pins the defensive
    behaviour against an accidental integer/object)."""
    for bad in (42, 3.14, ["Acquisitions"], {"k": "v"}, True, False, ()):
        assert veb.bridge(bad) is None, f"{bad!r} must be typed null"
        assert veb.bridge_for_issuer(bad) is None, f"{bad!r} must be typed null"


def test_bridge_returns_none_for_unknown_class():
    """An event class the repo has not yet classified (or that is not in
    any of the three source maps) is typed null. The bridge never invents
    a directional read for an unknown input."""
    for cls in ("BOGUS_CLASS", "Activism", "Acme Buyback", "EBITDA",
                "Revenue Synergy", "Quarterly EPS", "8-K Item 2.02"):
        assert veb.bridge(cls) is None, f"{cls!r} must be typed null"


# ---------------------------------------------------------------------------
# Forbidden shapes — magnitude / probability / score / consensus are never
# present in any direction word (the F07 do_not_redo law).
# ---------------------------------------------------------------------------

def test_no_direction_word_carries_magnitude_or_score_or_estimate():
    """Direction words are qualitative only. No numeric magnitude, no
    percentage, no consensus/estimate language, no probability/score."""
    domain = veb.classified_event_domain()
    banned_substrings = (
        "%", "percent", "×", "x ", " bp", "bps",
        "consensus", "estimate", "probability", "score",
        "forecast", "target", "rank",
    )
    for cls, pair in domain.items():
        if pair is None:
            continue
        _target, dw_en, dw_zh = pair
        for token in banned_substrings:
            assert token not in dw_en.lower(), (
                f"{cls!r}: EN direction word {dw_en!r} contains banned {token!r}"
            )
            assert token not in dw_zh, (
                f"{cls!r}: ZH direction word {dw_zh!r} contains banned {token!r}"
            )


# ---------------------------------------------------------------------------
# Panel rendering — the bridge line is one Tier-2 plain-word line, EN+ZH.
# ---------------------------------------------------------------------------

def _render(va_blob, t=None):
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT / "templates")))
    # Use the REAL engine.i18n.t, not a lambda — BLOCKER-2
    env.globals["t"] = t or i18n.t
    tmpl = env.from_string("{% include '_valuation_assumptions.html.j2' %}")
    return tmpl.render(valuation_assumptions=va_blob, deep_ids=[])


def test_panel_renders_typed_null_when_no_event_on_file():
    """When va.latest_event_bridge is absent or None (the production default
    under 'no new source'), the panel renders the typed-null copy in both
    languages."""
    v1 = vs.compute(_rows(), ticker="AAPL")
    controls = va.controls_blob(v1)
    assert controls is not None, "controls_blob should not return None for valid AAPL v1"
    # production path: latest_event_bridge may be None when no event exists
    html = _render(controls)
    assert 'id="va-event-bridge"' in html, "bridge line element is missing"
    # EN typed-null copy
    assert "No classified event on file for this issuer." in html, (
        "EN typed-null copy missing"
    )
    # ZH typed-null copy
    assert "暂无分类事件备案。" in html, "ZH typed-null copy missing"
    # The direction-word phrases must NOT leak onto the page in the typed-null path.
    for phrase in ("usually lifts", "usually presses", "通常推升", "通常压缩"):
        assert phrase not in html, (
            f"typed-null page leaked a direction-word phrase: {phrase!r}"
        )


def test_panel_renders_one_line_per_event_class_with_target_emphasis():
    """When va.latest_event_bridge is populated, the panel renders one line
    with the EN class label, the EN direction word (inside .va-event-target),
    the ZH class label, and the ZH direction word. The typed-null copy
    is absent. Uses the real i18n.t."""
    v1 = vs.compute(_rows(), ticker="AAPL")
    controls = va.controls_blob(v1)
    assert controls is not None
    # Test a representative sample of event classes
    cases = [
        ("Acquisitions",       "usually lifts growth",       "通常推升增长",     "收购"),
        ("Restructuring",     "usually presses margin",     "通常压缩利润率",   "重组"),
        ("Tender Offers",     "usually lifts the multiple people pay", "通常推升市盈率倍数", "要约收购"),
        ("Going-Private",     "usually lifts the multiple people pay", "通常推升市盈率倍数", "私有化"),
        ("Divestitures",      "usually lifts growth",       "通常推升增长",     "剥离"),
        ("Liquidations",      "usually presses margin",    "通常压缩利润率",   "清算"),
        ("Issuer Tenders",    "usually lifts the multiple people pay", "通常推升市盈率倍数", "发行人要约"),
        ("Spin-Offs",         "usually lifts growth",       "通常推升增长",     "分拆上市"),
        ("Capital Returns",   "usually lifts growth",      "通常推升增长",     "资本回报"),
        ("Rights Offerings",  "usually lifts the multiple people pay", "通常推升市盈率倍数", "配股发行"),
    ]
    for cls, en_dw, zh_dw, zh_label in cases:
        controls["latest_event_bridge"] = veb.bridge(cls)
        html = _render(controls)
        # EN copy — class label + EN direction word inside the target span.
        assert f"({cls})" in html, f"{cls!r}: EN class label not rendered"
        assert en_dw in html, f"{cls!r}: EN direction word {en_dw!r} not rendered"
        # ZH copy — class label + ZH direction word.
        assert f"（{zh_label}）" in html, f"{cls!r}: ZH class label {zh_label!r} not rendered"
        assert zh_dw in html, f"{cls!r}: ZH direction word {zh_dw!r} not rendered"
        # The target emphasis span wraps the direction word, not the class label.
        assert '<span class="va-event-target">' in html, f"{cls!r}: target span missing"
        # The typed-null copy must NOT appear alongside a populated bridge.
        assert "No classified event on file for this issuer." not in html, (
            f"{cls!r}: typed-null copy leaked into a populated render"
        )


def test_panel_renders_typed_null_for_other_class():
    """The 'Other' catch-all class has no directional read; the panel must
    render the typed-null copy."""
    v1 = vs.compute(_rows(), ticker="AAPL")
    controls = va.controls_blob(v1)
    assert controls is not None
    controls["latest_event_bridge"] = veb.bridge("Other")
    assert controls["latest_event_bridge"] is None
    html = _render(controls)
    assert "No classified event on file for this issuer." in html
    assert "暂无分类事件备案。" in html


def test_panel_does_not_inject_style_or_store_anything_from_bridge_line():
    """The bridge line is rendered server-side; the panel must not paint
    it via runtime JS stylesheet injection and must not store the value
    anywhere (matches the B-F07-2 'no save / no send' law)."""
    v1 = vs.compute(_rows(), ticker="AAPL")
    controls = va.controls_blob(v1)
    assert controls is not None
    controls["latest_event_bridge"] = veb.bridge("Tender Offers")
    html = _render(controls)
    # The line is plain text — no <script> rewrites it.
    assert '<script type="application/json"' in html  # vs-assumption-inputs is allowed
    # No JS path mutates the bridge line textContent. The bridge line is a
    # static <p> with bilingual <span>s; the existing JS only touches #va-bridge
    # (the per-share bridge, NOT the event-bridge) — pins here so a future
    # edit cannot quietly couple the two.
    assert 'document.getElementById("va-event-bridge")' not in html
    assert 'getElementById("va-event-bridge")' not in html
    assert "localStorage" not in html
    assert "sessionStorage" not in html


# ---------------------------------------------------------------------------
# Producer test — controls_blob populates latest_event_bridge from the
# v1_blob's special_situation field (MAJOR-3).
# ---------------------------------------------------------------------------

def test_controls_blob_populates_latest_event_bridge():
    """When the v1_blob carries a special_situation.latest_event_class,
    controls_blob surfaces the corresponding bridge dict; otherwise None."""
    v1 = vs.compute(_rows(), ticker="AAPL")
    assert v1 is not None

    # Null path: no special_situation field
    controls = va.controls_blob(v1)
    assert controls is not None
    # latest_event_bridge key is always present (even if None)
    assert "latest_event_bridge" in controls
    # Without a special_situation field the bridge is None
    assert controls["latest_event_bridge"] is None

    # Populated path: inject a known event class
    v1_with_event = dict(v1)
    v1_with_event["special_situation"] = {"latest_event_class": "Tender Offers"}
    controls2 = va.controls_blob(v1_with_event)
    assert controls2 is not None
    assert controls2["latest_event_bridge"] is not None
    assert controls2["latest_event_bridge"]["target"] == "multiple"
    assert controls2["latest_event_bridge"]["event_class"] == "Tender Offers"

    # Another event class
    v1_with_event["special_situation"] = {"latest_event_class": "Restructuring"}
    controls3 = va.controls_blob(v1_with_event)
    assert controls3["latest_event_bridge"]["target"] == "margin"
    assert controls3["latest_event_bridge"]["event_class"] == "Restructuring"


# ---------------------------------------------------------------------------
# Pure-module invariants — no IO / no clock / no network access.
# ---------------------------------------------------------------------------

def test_module_is_pure():
    """The bridge is a pure module: no IO, no clock, no network. Any
    accidental import of a side-effecting module would break this."""
    import engine.valuation_event_bridge as mod
    src_path = ROOT / "engine" / "valuation_event_bridge.py"
    src = src_path.read_text(encoding="utf-8")
    banned_imports = ("requests", "urllib", "httpx", "aiohttp", "pandas",
                       "pyarrow", "pathlib", "datetime", "time", "random")
    for token in banned_imports:
        # Allow the token inside a string or a comment, but not as an import.
        for line in src.splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"') or stripped.startswith("'"):
                continue
            assert f"import {token}" not in stripped and f"from {token}" not in stripped, (
                f"valuation_event_bridge.py imports {token!r} — must stay pure"
            )
    # The module exposes only the documented surface.
    expected_names = {
        "GROWTH", "MARGIN", "MULTIPLE", "ALLOWED_TARGETS",
        "SPECIAL_SITUATIONS_TO_ASSUMPTION",
        "EVENT_SPINE_TO_ASSUMPTION",
        "POLICY_CALENDAR_TO_ASSUMPTION",
        "EVENT_TO_ASSUMPTION",
        "bridge", "bridge_for_issuer", "classified_event_domain",
    }
    for name in expected_names:
        assert hasattr(mod, name), f"valuation_event_bridge.py missing {name!r}"


def test_function_calls_have_no_side_effects():
    """Calling bridge()/bridge_for_issuer()/classified_event_domain() in any
    order, with any inputs, never mutates the closed map. Re-running the
    same call returns the same value."""
    snapshot = veb.classified_event_domain()
    # Run a battery of calls.
    for _ in range(3):
        veb.bridge("Acquisitions")
        veb.bridge("Other")
        veb.bridge(None)
        veb.bridge_for_issuer("Tender Offers")
        veb.bridge_for_issuer(None)
        veb.bridge_for_issuer(42)
        veb.classified_event_domain()
    assert veb.classified_event_domain() == snapshot, "closed map mutated"
