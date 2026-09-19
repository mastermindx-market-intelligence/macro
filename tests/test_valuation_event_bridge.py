"""Tests for engine/valuation_event_bridge.py (B-F07-3).

The bridge is the plain-word link between the latest classified event on
file and one of the three B-F07-2 valuation inputs (growth, margin,
multiple). Pure module, no IO, no clock. Every test asserts the closed-map
invariant + a non-fallback fixture per event class + the typed-null paths.
"""
from __future__ import annotations

import json
import ast
import logging
from pathlib import Path
import re
import sys
import pytest
from importlib import import_module

import jinja2

from engine import valuation_event_bridge as veb
from engine.capital_structure import event_spine
from engine.capital_structure import spine_paths
from engine.capital_structure.event_versions_io import spine_ticker_row_count
from engine import valuation_assumptions as va
from engine import valuation_scenario as vs
from engine import i18n as i18n
from tests.test_valuation_scenario import _rows

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def issuer_spines(tmp_path, monkeypatch):
    """Use the owners' paths, with no dependency on live issuer coverage."""
    chronicle = import_module("engine.chronicle.spine")
    from lib import config
    path = tmp_path / "events.jsonl"
    monkeypatch.setattr(chronicle, "EVENTS_REL", path)
    monkeypatch.setattr(spine_paths, "capital_data_root", lambda: tmp_path)
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    compiler = sys.modules.get("scripts.compile_capital_structure_events")
    if compiler is not None:
        monkeypatch.setattr(compiler, "_data_root", lambda: tmp_path)
    return path

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
    """Map keys are exactly the union of the two issuer-filing vocabularies.

    Spine subtypes are exactly the keys emitted by engine/capital_structure/event_spine.py
    route_form(). Federal Register stages and entity-list themes are not issuer
    filings and are excluded from the issuer map.
    """
    from engine.special_situations import MATURE_CATEGORIES

    form_sets = (
        value
        for name, value in vars(event_spine).items()
        if name.endswith("_FORMS") and isinstance(value, frozenset)
    )
    route_source = ast.get_source_segment(
        Path(event_spine.__file__).read_text(),
        next(
            node
            for node in ast.parse(Path(event_spine.__file__).read_text()).body
            if isinstance(node, ast.FunctionDef) and node.name == "route_form"
        ),
    )
    route_tokens = {
        node.value
        for node in ast.walk(ast.parse(route_source))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    spine_forms = set().union(*form_sets, route_tokens)
    spine_subtypes = {
        event_spine.route_form(form, items).subtype
        for form in spine_forms
        for items in (None, *sorted(route_tokens))
    }
    expected = set(MATURE_CATEGORIES) | spine_subtypes
    assert set(veb.classified_event_domain()) == expected


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
# Tender Offers / Going-Private / Issuer Tenders → multiple (takeout premium).
# Delistings → typed null (Form 25 delisting is a regulatory exit, not a takeout premium).
# Rights Offerings → multiple (dilutive; presses per-share value).
MULTIPLE_HITS = ["Tender Offers", "Going-Private", "Issuer Tenders", "Rights Offerings"]
NULL_HITS = ["Other", "Delistings"]


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


def test_bridge_returns_typed_null_for_delistings():
    """Delistings (Form 25 style) is a regulatory exit, not a takeout premium
    → honest read is typed null."""
    out = veb.bridge("Delistings")
    assert out is None, f"'Delistings' must be typed null, got {out!r}"


def test_federal_register_policy_events_are_not_issuer_filings():
    """Federal Register stages and entity-list themes cannot be labelled as the
    issuer's latest filing, even though their policy mapping remains explicit."""
    from collectors.federal_register import _STAGE_WEIGHTS
    from engine.policy_calendar import _ENTITY_LIST_THEMES

    issuer_domain = set(veb.classified_event_domain())
    policy_domain = set(veb.POLICY_EVENT_TO_ASSUMPTION)
    stages = {row[2] for row in _STAGE_WEIGHTS}
    assert policy_domain == stages | set(_ENTITY_LIST_THEMES)
    assert issuer_domain.isdisjoint(policy_domain)
    assert veb.bridge_for_issuer("executive_order") is None
    assert veb.bridge_for_issuer("ai_semiconductors") is None


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
    assert "No filing on file yet for this company." in html, (
        "EN typed-null copy missing"
    )
    # ZH typed-null copy
    assert "该公司暂无备案。" in html, "ZH typed-null copy missing"
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
        ("Rights Offerings",  "usually presses the multiple people pay", "通常压缩市盈率倍数", "配股发行"),
    ]
    for cls, en_dw, zh_dw, zh_label in cases:
        controls["latest_event_bridge"] = veb.bridge(cls)
        html = _render(controls)
        # EN copy — event_class_en label + EN direction word inside the target span.
        en_label = veb._EVENT_CLASS_NAMES.get(cls, (cls, zh_label))[0]
        assert f"({en_label})" in html, f"{cls!r}: EN class label {en_label!r} not rendered"
        assert en_dw in html, f"{cls!r}: EN direction word {en_dw!r} not rendered"
        # ZH copy — event_class_zh label + ZH direction word.
        assert f"（{zh_label}）" in html, f"{cls!r}: ZH class label {zh_label!r} not rendered"
        assert zh_dw in html, f"{cls!r}: ZH direction word {zh_dw!r} not rendered"
        # The target emphasis span wraps the direction word, not the class label.
        assert '<span class="va-event-target">' in html, f"{cls!r}: target span missing"
        # The typed-null copy must NOT appear alongside a populated bridge.
        assert "No filing on file yet for this company." not in html, (
            f"{cls!r}: typed-null copy leaked into a populated render"
        )


def test_panel_renders_every_member_without_machine_slugs():
    """Every issuer vocabulary member has bilingual plain-word labels."""
    v1 = vs.compute(_rows(), ticker="AAPL")
    controls = va.controls_blob(v1)
    assert controls is not None
    slug_pattern = re.compile(r"\b[a-z]+(?:_[a-z_]+)+\b")
    for cls in veb.classified_event_domain():
        bridge = veb.bridge(cls)
        controls["latest_event_bridge"] = bridge
        html = _render(controls)
        event_line = re.search(r'<p[^>]*id="va-event-bridge"[^>]*>(.*?)</p>', html, re.DOTALL)[1]
        sentence = " ".join(re.sub(r"<[^>]+>", "", event_line).split())
        assert slug_pattern.search(sentence) is None
        if bridge is None:
            assert cls in veb._EVENT_CLASS_NAMES
            assert "No filing on file yet for this company." in sentence
            assert "该公司暂无备案。" in sentence
            continue
        assert slug_pattern.search(bridge["event_class_en"]) is None
        assert slug_pattern.search(bridge["event_class_zh"]) is None
        assert bridge["event_class_en"] in " ".join(html.split())
        assert bridge["event_class_zh"] in " ".join(html.split())


def test_panel_renders_typed_null_for_other_class():
    """The 'Other' catch-all class has no directional read; the panel must
    render the typed-null copy."""
    v1 = vs.compute(_rows(), ticker="AAPL")
    controls = va.controls_blob(v1)
    assert controls is not None
    controls["latest_event_bridge"] = veb.bridge("Other")
    assert controls["latest_event_bridge"] is None
    html = _render(controls)
    assert "No filing on file yet for this company." in html
    assert "该公司暂无备案。" in html


def test_template_does_not_nest_i18n_twins():
    """The event line owns one language span per language."""
    v1 = vs.compute(_rows(), ticker="AAPL")
    controls = va.controls_blob(v1)
    assert controls is not None
    controls["latest_event_bridge"] = veb.bridge("Tender Offers")
    html = _render(controls)
    bridge = html.split('id="va-event-bridge"', 1)[1].split("</p>", 1)[0]
    assert bridge.count('class="l-en"') == 1
    assert bridge.count('class="l-zh"') == 1
    template = (ROOT / "templates" / "_valuation_assumptions.html.j2").read_text()
    start = template.index("{% set _va_event_bridge")
    source = template[start:template.index("</p>", start)]
    assert "{{ t(" in source
    assert 'class="l-en"' not in source
    assert 'class="l-zh"' not in source


def test_evidence_hosts_match_final_template_sentences_and_typography():
    """Static evidence hosts carry the production event line, not a stale copy."""
    event_pattern = re.compile(
        r'<p[^>]*id="va-event-bridge"[^>]*>(.*?)</p>', re.DOTALL
    )

    def event_html(html):
        match = event_pattern.search(html)
        assert match is not None
        return " ".join(match.group(1).split())

    v1 = vs.compute(_rows(), ticker="AAPL")
    controls = va.controls_blob(v1)
    assert controls is not None
    cases = {
        "tender-offer": veb.bridge("Tender Offers"),
        "restructuring": veb.bridge("Restructuring"),
        "null": None,
    }
    for host_name, bridge_value in cases.items():
        host_path = (
            ROOT
            / "mockups"
            / "evidence"
            / "b-f07-3-event-bridge"
            / "hosts"
            / f"valuation-event-bridge-{host_name}.html"
        )
        controls["latest_event_bridge"] = bridge_value
        assert event_html(host_path.read_text()) == event_html(_render(controls))
        assert ".va-event-bridge .va-event-target{color:var(--muted);}" in host_path.read_text()


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
# existing spine readers, using the same controls_blob(v1) call as the builder.
# ---------------------------------------------------------------------------

def test_controls_blob_populates_latest_event_bridge_from_spine(issuer_spines):
    """The production controls call reads the canonical issuer event spine."""
    v1 = vs.compute(_rows(), ticker="AAPL")
    assert v1 is not None
    assert "special_situation" not in v1

    spine_events = [
            {
                "id": "newer-prospectus",
                "tickers": ["aapl"],
                "kind": event_spine.route_form("424B5").subtype,
                "ts": "2026-03-01T00:00:00Z",
            },
            {
                "id": "new-tender-offer",
                "tickers": ["AAPL"],
                "kind": "Tender Offers",
                "ts": "2026-02-01T00:00:00Z",
            },
            {
                "id": "other-issuer",
                "tickers": ["MSFT"],
                "kind": "registration_statement",
                "ts": "2026-03-01T00:00:00Z",
            },
    ]
    issuer_spines.write_text(
        "".join(json.dumps(event, sort_keys=True) + "\n" for event in spine_events),
        encoding="utf-8",
    )

    controls = va.controls_blob(v1)
    assert controls is not None
    bridge = controls["latest_event_bridge"]
    assert bridge is not None
    assert bridge["event_class"] == "Tender Offers"
    assert bridge["target"] == "multiple"
    html = " ".join(_render(controls).split())
    assert "Latest filing on file (Tender Offers)" in html
    assert "最新备案（要约收购）" in html
    assert "No filing on file yet" not in html
    assert "special_situation" not in v1


def test_controls_blob_reads_validated_capital_spine(issuer_spines):
    """The production Parquet reader supplies real SEC event subtypes."""
    compiler = import_module("scripts.compile_capital_structure_events")
    from tests.test_capital_structure_event_spine import _observation, _span

    events = [
        event_spine.build_event_version(_observation(ticker="AAPL"), [_span()]),
        event_spine.build_event_version(
            _observation(
                ticker="AAPL", form="424B5", accession="0000000001-26-000002",
                accepted_at="2026-08-02T10:00:00Z",
                first_seen_at="2026-08-02T10:00:03Z",
            ), [_span()],
        ),
    ]
    compiler._event_frame(events).to_parquet(
        issuer_spines.parent / "event_versions.parquet", index=False
    )
    controls = va.controls_blob(vs.compute(_rows(), ticker="AAPL"))
    assert controls["latest_event_bridge"]["event_class"] == "registration_statement"
    assert "Latest filing on file (Registration Statement)" in " ".join(_render(controls).split())


def test_controls_blob_ignores_nonfilings_and_selects_latest_classified(issuer_spines):
    events = [
        {"id": "old", "tickers": ["AAPL"], "kind": "Tender Offers", "ts": "2026-01-01T00:00:00Z"},
        {"id": "latest", "tickers": ["aapl"], "kind": "Restructuring", "ts": "2026-02-01T00:00:00Z"},
        {"id": "policy", "tickers": ["AAPL"], "kind": "final_rule", "ts": "2026-03-01T00:00:00Z"},
        {"id": "earnings", "tickers": ["AAPL"], "kind": "earnings", "ts": "2026-04-01T00:00:00Z"},
    ]
    issuer_spines.write_text("\n".join(json.dumps(e) for e in reversed(events)))
    controls = va.controls_blob(vs.compute(_rows(), ticker="AAPL"))
    assert controls["latest_event_bridge"]["event_class"] == "Restructuring"
    issuer_spines.write_text("\n".join(json.dumps(e) for e in events[2:]))
    assert va.controls_blob(vs.compute(_rows(), ticker="AAPL"))["latest_event_bridge"] is None


def _event_bridge_sentence(html):
    event_line = re.search(
        r'<p[^>]*id="va-event-bridge"[^>]*>(.*?)</p>', html, re.DOTALL
    )[1]
    return " ".join(re.sub(r"<[^>]+>", "", event_line).split())


COMMITTED_CAPITAL_ROOT = ROOT / "data" / "capital_structure"


def _use_committed_capital_spine(monkeypatch):
    """Point the shared spine resolver at the in-repo capital-structure ledger."""
    monkeypatch.setattr(spine_paths, "capital_data_root", lambda: COMMITTED_CAPITAL_ROOT)
    # Round-4 producer (57cfa8d9) still reads compiler._data_root; keep that
    # name aimed at the same committed ledger so the RED replay is a collector
    # import failure, not an empty tmp path.
    compiler = import_module("scripts.compile_capital_structure_events")
    monkeypatch.setattr(compiler, "_data_root", lambda: COMMITTED_CAPITAL_ROOT)
    return spine_paths.event_versions_path()


def test_production_path_renders_committed_nsa_post_effective_amendment(
    issuer_spines, monkeypatch
):
    """controls_blob(v1) plus the ticker-page renderer on committed NSA fixtures.

    The live valuation cohort stays AAPL-only. This test uses the same producer
    and template as the generated ticker page, against NSA rows already in
    data/capital_structure/event_versions.parquet.
    """
    _use_committed_capital_spine(monkeypatch)
    v1 = vs.compute(_rows(), ticker="NSA")
    controls = va.controls_blob(v1)
    assert controls is not None
    bridge = controls["latest_event_bridge"]
    assert bridge is not None
    assert bridge["event_class"] == "post_effective_amendment"
    html = _render(controls)
    sentence = _event_bridge_sentence(html)
    assert "post_effective_amendment" in json.dumps(bridge)
    assert "Latest filing on file (Post-Effective Amendment)" in sentence
    assert "usually presses margin" in sentence
    assert "最新备案（生效后修正）" in sentence
    assert "No filing on file yet for this company." not in sentence
    assert "该公司暂无备案。" not in sentence


def test_production_path_renders_aapl_typed_null_from_committed_spine(
    issuer_spines, monkeypatch
):
    """AAPL's generated page paints the typed-null line; it never fabricates an event."""
    path = _use_committed_capital_spine(monkeypatch)
    assert path == COMMITTED_CAPITAL_ROOT / "event_versions.parquet"
    assert path.exists()
    # Prove the resolver opened the committed ledger: NSA is present in that
    # file and AAPL is honestly absent (0 rows), not skipped by an empty tmp.
    assert spine_ticker_row_count("NSA") >= 1
    assert spine_ticker_row_count("AAPL") == 0
    v1 = vs.compute(_rows(), ticker="AAPL")
    controls = va.controls_blob(v1)
    assert controls is not None
    assert controls["latest_event_bridge"] is None
    html = _render(controls)
    sentence = _event_bridge_sentence(html)
    assert "No filing on file yet for this company." in sentence
    assert "该公司暂无备案。" in sentence
    for phrase in ("usually lifts", "usually presses", "通常推升", "通常压缩"):
        assert phrase not in sentence
    assert "Post-Effective Amendment" not in sentence
    assert "post_effective_amendment" not in sentence


# ---------------------------------------------------------------------------
# RED-first: no collector imports at call time (requests / collectors.*).
# ---------------------------------------------------------------------------

def test_controls_blob_no_collector_import_at_call_time(
    issuer_spines, monkeypatch
):
    """Pop the compiler and block collector modules, then reload the producer.

    At 57cfa8d9 the producer imported scripts.compile_capital_structure_events
    at call time, so this test is RED there. At head it must match the
    unblocked NSA post_effective_amendment line and the AAPL typed null.
    """
    import importlib

    _use_committed_capital_spine(monkeypatch)
    v1_nsa = vs.compute(_rows(), ticker="NSA")
    v1_aapl = vs.compute(_rows(), ticker="AAPL")
    baseline_nsa = va.controls_blob(v1_nsa)
    baseline_aapl = va.controls_blob(v1_aapl)
    assert baseline_nsa is not None
    assert baseline_nsa["latest_event_bridge"] is not None
    assert baseline_nsa["latest_event_bridge"]["event_class"] == "post_effective_amendment"
    assert baseline_aapl is not None
    assert baseline_aapl["latest_event_bridge"] is None

    sys.modules.pop("scripts.compile_capital_structure_events", None)
    sys.modules.pop("collectors.sec_capital_structure", None)
    sys.modules.pop("requests", None)
    monkeypatch.setitem(sys.modules, "collectors.sec_capital_structure", None)
    monkeypatch.setitem(sys.modules, "requests", None)

    va_module = importlib.reload(import_module("engine.valuation_assumptions"))
    blocked_nsa = va_module.controls_blob(v1_nsa)
    blocked_aapl = va_module.controls_blob(v1_aapl)

    assert blocked_nsa is not None, "NSA controls_blob must not return None"
    assert blocked_aapl is not None, "AAPL controls_blob must not return None"
    assert (
        blocked_nsa.get("latest_event_bridge")
        == baseline_nsa.get("latest_event_bridge")
    ), "NSA latest_event_bridge must match baseline"
    assert (
        blocked_aapl.get("latest_event_bridge")
        == baseline_aapl.get("latest_event_bridge")
    ), "AAPL latest_event_bridge must match baseline"


def test_issuer_event_lookup_failure_returns_typed_null_and_warns(
    issuer_spines, monkeypatch, caplog
):
    """A raising bridge_for_issuer must not break the panel: typed null + warning."""
    caplog.set_level(logging.WARNING)
    issuer_spines.write_text(
        json.dumps({
            "id": "e1",
            "tickers": ["AAPL"],
            "kind": "Tender Offers",
            "ts": "2026-01-01T00:00:00Z",
        })
        + "\n",
        encoding="utf-8",
    )
    real = veb.bridge_for_issuer

    def boom(event_class):
        if event_class:
            raise RuntimeError("bridge boom")
        return real(event_class)

    monkeypatch.setattr(veb, "bridge_for_issuer", boom)
    with caplog.at_level(logging.WARNING, logger="engine.valuation_assumptions"):
        controls = va.controls_blob(vs.compute(_rows(), ticker="AAPL"))
    assert controls is not None
    assert controls["latest_event_bridge"] is None
    assert any(
        "valuation: issuer event lookup failed:" in record.getMessage()
        for record in caplog.records
    )


def test_engine_valuation_modules_do_not_import_scripts_or_collectors():
    """Producer, bridge, and the parquet reader never import scripts or collectors."""
    banned = (
        "import scripts",
        "from scripts",
        "import collectors",
        "from collectors",
        'import_module("scripts',
        "import_module('scripts",
        'import_module("collectors',
        "import_module('collectors",
    )
    paths = (
        ROOT / "engine" / "valuation_assumptions.py",
        ROOT / "engine" / "valuation_event_bridge.py",
        ROOT / "engine" / "capital_structure" / "event_versions_io.py",
        ROOT / "engine" / "capital_structure" / "spine_paths.py",
    )
    for path in paths:
        src = path.read_text(encoding="utf-8")
        for line in src.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for token in banned:
                assert token not in stripped, f"{path.name} contains {token!r}: {stripped}"


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
