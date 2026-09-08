"""Tests for scripts/build_market_reference.py (MOR-1 public Reference surface).

Verifies:
1. Registry validation fails closed on every DEC §3.3 / MOR1_CONTRACT.md rule,
   one red-fixture per rule (unknown owner ref, duplicate alias, superseded_by
   cycle, unsafe source URL, missing caveats on kind:indicator, missing either
   language, missing `_zh` sibling for a present unit_or_basis/interpretation_*
   field, schema mismatch, empty entries, invalid kind/family/authority_
   ceiling/status, non-kebab id, aliases presence parity, caveats length
   mismatch, superseded_by resolving to a real id, status:deprecated requiring
   superseded_by, and the B1 anchor-liveness rule) — each fixture violates
   exactly one rule so the failure message is attributable.
2. Happy-path build of the real committed registry: validates clean, the ZH
   supplement's coverage counts (46/38/38/46), and the rendered page carries
   the expected entry/family counts.
3. Anchor stability: every registry entry id appears as a real `id="..."`
   anchor in the rendered HTML (deep-link contract).
4. EN/ZH parity: every rendered entry carries both an `l-en` and an `l-zh`
   span (dual-language contract, build-time guaranteed per DEC §3.2), and the
   `l-zh` span for unit_or_basis/interpretation_* carries the REAL translated
   text from the MOR-1 ZH supplement, not an English-fallback echo.
"""
from __future__ import annotations

import copy
import re
import sys
from pathlib import Path

import pytest
import yaml
from jinja2 import Environment, FileSystemLoader

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.build_market_reference import (  # noqa: E402
    KNOWN_OWNER_PAGES,
    RegistryError,
    build_coverage_view_model,
    build_view_model,
    check_anchor_liveness,
    initial_of,
    search_key,
    validate,
    validate_coverage_exceptions,
)

REGISTRY_PATH = REPO / "config" / "market_reference.yml"
TEMPLATE_DIR = REPO / "templates"


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def _base_entry(**overrides) -> dict:
    """One minimal, otherwise-fully-valid registry entry. Tests override exactly
    the field(s) needed to trip one rule, so a fixture failure is attributable."""
    entry = {
        "id": "sample-term",
        "kind": "glossary",
        "family": "doctrine",
        "label_en": "Sample Term",
        "label_zh": "示例术语",
        "aliases_en": [],
        "aliases_zh": [],
        "short_definition_en": "A sample definition.",
        "short_definition_zh": "示例定义。",
        "why_it_matters_en": "It matters for the test.",
        "why_it_matters_zh": "对测试很重要。",
        "unit_or_basis": "Categorical",
        "unit_or_basis_zh": "分类",
        "interpretation_up": None,
        "interpretation_down": None,
        "interpretation_neutral": None,
        "caveats_en": [],
        "caveats_zh": [],
        "owner_ref": "aibrief.html",
        "public_source_refs": [],
        "related_ids": [],
        "authority_ceiling": "reference_only",
        "status": "active",
    }
    entry.update(overrides)
    return entry


def _registry(*entries) -> dict:
    return {"schema": "mastermind.market_reference/v1", "entries": list(entries)}


def _indicator_entry(**overrides) -> dict:
    base = _base_entry(
        id="sample-indicator",
        kind="indicator",
        family="regime",
        caveats_en=["One caveat."],
        caveats_zh=["一条注意事项。"],
    )
    base.update(overrides)
    return base


def _errors(exc: RegistryError) -> str:
    return "; ".join(exc.errors)


# ---------------------------------------------------------------------------
# 1 · one red-fixture per validation rule
# ---------------------------------------------------------------------------

def test_unknown_owner_ref_fails_closed():
    reg = _registry(_base_entry(owner_ref="not-a-real-page.html#nope"))
    with pytest.raises(RegistryError) as exc:
        validate(reg)
    assert "unknown owner page" in _errors(exc.value)


def test_unknown_owner_anchor_fails_closed():
    reg = _registry(_base_entry(owner_ref="macro.html#not-a-real-anchor"))
    with pytest.raises(RegistryError) as exc:
        validate(reg)
    assert "unknown owner anchor" in _errors(exc.value)


def test_duplicate_alias_fails_closed():
    reg = _registry(
        _base_entry(id="term-one", aliases_en=["shared alias"]),
        _base_entry(id="term-two", aliases_en=["Shared Alias"]),  # casefold+strip collision
    )
    with pytest.raises(RegistryError) as exc:
        validate(reg)
    assert "duplicates an alias already used" in _errors(exc.value)


def test_superseded_by_cycle_fails_closed():
    reg = _registry(
        _base_entry(id="term-a", status="deprecated", superseded_by="term-b"),
        _base_entry(id="term-b", status="deprecated", superseded_by="term-a"),
    )
    with pytest.raises(RegistryError) as exc:
        validate(reg)
    assert "superseded_by cycle" in _errors(exc.value)


def test_unsafe_source_url_fails_closed():
    reg = _registry(_base_entry(public_source_refs=["https://evil.example.com/not-allowlisted"]))
    with pytest.raises(RegistryError) as exc:
        validate(reg)
    assert "not on the allowlist" in _errors(exc.value)


def test_unsafe_source_scheme_fails_closed():
    reg = _registry(_base_entry(public_source_refs=["http://fred.stlouisfed.org"]))
    with pytest.raises(RegistryError) as exc:
        validate(reg)
    assert "not on the allowlist" in _errors(exc.value)


def test_missing_caveats_on_indicator_fails_closed():
    reg = _registry(_indicator_entry(caveats_en=[], caveats_zh=[]))
    with pytest.raises(RegistryError) as exc:
        validate(reg)
    assert "requires a non-empty caveats_en" in _errors(exc.value)


def test_missing_language_fails_closed():
    reg = _registry(_base_entry(label_zh=""))
    with pytest.raises(RegistryError) as exc:
        validate(reg)
    assert "label_en and label_zh must both be present" in _errors(exc.value)


def test_duplicate_id_fails_closed():
    reg = _registry(_base_entry(id="dupe-id"), _base_entry(id="dupe-id"))
    with pytest.raises(RegistryError) as exc:
        validate(reg)
    assert "duplicate id" in _errors(exc.value)


def test_unknown_related_id_fails_closed():
    reg = _registry(_base_entry(related_ids=["ghost-entry"]))
    with pytest.raises(RegistryError) as exc:
        validate(reg)
    assert "references unknown id" in _errors(exc.value)


# --- M6: the 9 basic-shape red fixtures the review found missing ----------

def test_schema_mismatch_fails_closed():
    reg = _registry(_base_entry())
    reg["schema"] = "not-the-right-schema/v1"
    with pytest.raises(RegistryError) as exc:
        validate(reg)
    assert "schema must be" in _errors(exc.value)


def test_empty_entries_fails_closed():
    with pytest.raises(RegistryError) as exc:
        validate({"schema": "mastermind.market_reference/v1", "entries": []})
    assert "entries must be a non-empty list" in _errors(exc.value)


def test_invalid_kind_fails_closed():
    reg = _registry(_base_entry(kind="not-a-real-kind"))
    with pytest.raises(RegistryError) as exc:
        validate(reg)
    assert "kind must be one of" in _errors(exc.value)


def test_invalid_family_fails_closed():
    reg = _registry(_base_entry(family="not-a-real-family"))
    with pytest.raises(RegistryError) as exc:
        validate(reg)
    assert "family must be one of" in _errors(exc.value)


def test_invalid_authority_ceiling_fails_closed():
    reg = _registry(_base_entry(authority_ceiling="advisory"))
    with pytest.raises(RegistryError) as exc:
        validate(reg)
    assert "authority_ceiling must be 'reference_only'" in _errors(exc.value)


def test_invalid_status_fails_closed():
    reg = _registry(_base_entry(status="archived"))
    with pytest.raises(RegistryError) as exc:
        validate(reg)
    assert "status must be one of" in _errors(exc.value)


def test_non_kebab_id_fails_closed():
    reg = _registry(_base_entry(id="Not_Kebab Case!"))
    with pytest.raises(RegistryError) as exc:
        validate(reg)
    assert "id must be a non-empty kebab-case slug" in _errors(exc.value)


def test_aliases_presence_parity_fails_closed():
    """aliases_en present without aliases_zh (or vice versa) fails closed —
    both must be present when either is, even if one is an empty list."""
    reg = _registry(_base_entry(aliases_en=["only-english-alias"]))
    del reg["entries"][0]["aliases_zh"]
    with pytest.raises(RegistryError) as exc:
        validate(reg)
    assert "aliases_en/aliases_zh must both be present" in _errors(exc.value)


def test_caveats_length_mismatch_fails_closed():
    reg = _registry(_indicator_entry(
        caveats_en=["one caveat", "two caveats"],
        caveats_zh=["一条注意事项"],
    ))
    with pytest.raises(RegistryError) as exc:
        validate(reg)
    assert "caveats_en and caveats_zh must have matching length" in _errors(exc.value)


# --- M6: 3 new rules, each with its own red fixture ------------------------

def test_superseded_by_unknown_id_fails_closed():
    reg = _registry(_base_entry(status="deprecated", superseded_by="ghost-entry"))
    with pytest.raises(RegistryError) as exc:
        validate(reg)
    assert "superseded_by references unknown id" in _errors(exc.value)


def test_deprecated_without_superseded_by_fails_closed():
    reg = _registry(_base_entry(status="deprecated"))
    with pytest.raises(RegistryError) as exc:
        validate(reg)
    assert "status:deprecated requires a superseded_by" in _errors(exc.value)


def test_anchor_liveness_fails_closed_on_display_none_id(tmp_path):
    """B1: the durable anchor-liveness rule. A synthetic site/<page>.html with a
    body.<classes> #<id>{display:none} rule matching the page's own rendered
    body class must be rejected — this is the exact selector shape every real
    anchor-hiding bug in this codebase used (mx4-grid / page-stocks toggles)."""
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "hiddenpage.html").write_text(
        '<html><body class="page-macro mx4-grid">'
        '<style>body.page-macro.mx4-grid #hidden-thing{display:none!important;}</style>'
        '<div id="hidden-thing">content</div>'
        "</body></html>",
        encoding="utf-8",
    )
    is_live, note = check_anchor_liveness(tmp_path, "hiddenpage.html", "hidden-thing")
    assert is_live is False
    assert "display:none" in note or "visibility:hidden" in note


def test_anchor_liveness_fails_closed_on_host_class_hide_in_linked_css(tmp_path):
    """R1 widening: the id's own element carries a class whose pure-class rule
    (in a LINKED local stylesheet, behind a CSS comment, with a ?v= cache
    buster) hides it — the .mx5-popover/.mx5-dlg shape behind 11 of the 16
    originally-broken entries, in the exact serving shape of site/macro.html
    (zero inline styles, external hashed CSS)."""
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "pop.css").write_text(
        "/* Popover panel */\n.pop-panel{display:none;position:absolute}",
        encoding="utf-8",
    )
    (site_dir / "poppage.html").write_text(
        '<html><head><link rel="stylesheet" href="pop.css?v=abc123"></head>'
        '<body class="page-x">'
        '<div class="pop-panel" id="pop-thing">content</div>'
        "</body></html>",
        encoding="utf-8",
    )
    is_live, note = check_anchor_liveness(tmp_path, "poppage.html", "pop-thing")
    assert is_live is False
    assert "own element is hidden" in note


def test_anchor_liveness_fails_closed_on_body_gated_hide_in_linked_css(tmp_path):
    """R1 widening: the body-gated shape must also be found when the rule
    lives in a linked stylesheet rather than an inline <style> block (real
    rendered pages here carry zero inline styles)."""
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "page.css").write_text(
        "body.page-y #tray-thing{visibility:hidden}",
        encoding="utf-8",
    )
    (site_dir / "traypage.html").write_text(
        '<html><head><link rel="stylesheet" href="page.css"></head>'
        '<body class="page-y"><div id="tray-thing">content</div></body></html>',
        encoding="utf-8",
    )
    is_live, note = check_anchor_liveness(tmp_path, "traypage.html", "tray-thing")
    assert is_live is False
    assert "visibility:hidden" in note or "display:none" in note


def test_anchor_liveness_accepts_a_visible_id(tmp_path):
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "visiblepage.html").write_text(
        '<html><body class="page-macro mx4-grid">'
        '<style>body.page-macro.mx4-grid #hidden-thing{display:none!important;}</style>'
        '<div id="visible-thing">content</div>'
        "</body></html>",
        encoding="utf-8",
    )
    is_live, note = check_anchor_liveness(tmp_path, "visiblepage.html", "visible-thing")
    assert is_live is True


def test_anchor_liveness_skips_when_site_page_absent(tmp_path):
    """Fail-open: this builder does not require every OTHER page's site
    output to exist (sparse checkouts, pages this builder does not produce)."""
    is_live, note = check_anchor_liveness(tmp_path, "never-built.html", "whatever")
    assert is_live is True
    assert "not built in this checkout" in note


def test_anchor_liveness_wired_into_validate_fails_closed(tmp_path):
    """End-to-end: validate() itself rejects a KNOWN_OWNER_PAGES anchor that
    resolves to a display:none-gated id in the committed site output."""
    from scripts import build_market_reference as bmr

    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "macro.html").write_text(
        '<html><body class="page-macro mx4-grid">'
        '<style>body.page-macro.mx4-grid #regime-radar-decoy{display:none!important;}</style>'
        '<div id="regime-radar-decoy">content</div>'
        "</body></html>",
        encoding="utf-8",
    )
    # temporarily widen the allowlist so this fixture's fragment is "known"
    # without touching the real KNOWN_OWNER_PAGES for every other test
    old = bmr.KNOWN_OWNER_PAGES["macro.html"]
    bmr.KNOWN_OWNER_PAGES["macro.html"] = old | {"regime-radar-decoy"}
    try:
        reg = _registry(_base_entry(owner_ref="macro.html#regime-radar-decoy"))
        with pytest.raises(RegistryError) as exc:
            validate(reg, repo_root=tmp_path)
        assert "not a live/visible anchor" in _errors(exc.value)
    finally:
        bmr.KNOWN_OWNER_PAGES["macro.html"] = old


def test_explicit_null_interpretation_is_accepted_same_as_omitted():
    """Contract note: explicit `null` interpretation values are equivalent to
    omitted — the validator must accept both without complaint (and, since a
    null value has nothing to translate, it needs no `_zh` sibling either)."""
    reg = _registry(_base_entry(interpretation_up=None, interpretation_down=None,
                                 interpretation_neutral=None))
    entries = validate(reg)  # must not raise
    assert len(entries) == 1


def test_missing_zh_for_present_unit_or_basis_fails_closed():
    """MOR-1 ZH supplement rule: once a field is present, its `_zh` sibling is
    required — the old graceful t(en, zh='') render fallback is retired as a
    validation matter (it may still exist as template-level defensive code,
    but a registry that relies on it must no longer validate)."""
    reg = _registry(_base_entry(unit_or_basis="Percent", unit_or_basis_zh=None))
    with pytest.raises(RegistryError) as exc:
        validate(reg)
    assert "unit_or_basis is present but unit_or_basis_zh is missing" in _errors(exc.value)


def test_missing_zh_for_present_interpretation_up_fails_closed():
    reg = _registry(_base_entry(interpretation_up="Rising."))
    with pytest.raises(RegistryError) as exc:
        validate(reg)
    assert "interpretation_up is present but interpretation_up_zh is missing" in _errors(exc.value)


def test_present_interpretation_with_zh_sibling_is_accepted():
    reg = _registry(_base_entry(
        interpretation_up="Rising.", interpretation_up_zh="上升。",
        interpretation_down="Falling.", interpretation_down_zh="下降。",
        interpretation_neutral="Flat.", interpretation_neutral_zh="持平。",
    ))
    entries = validate(reg)  # must not raise
    assert len(entries) == 1


# ---------------------------------------------------------------------------
# 2 · happy-path build of the real committed registry
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def real_raw():
    return yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def real_entries(real_raw):
    return validate(real_raw)


@pytest.fixture(scope="module")
def real_coverage(real_raw, real_entries):
    return build_coverage_view_model(
        validate_coverage_exceptions(real_raw, real_entries), real_entries
    )


def test_real_registry_validates_clean(real_entries):
    assert len(real_entries) == 46


def test_real_registry_zh_supplement_coverage(real_entries):
    """MOR-1 ZH supplement (2026-09-02): unit_or_basis_zh on all 46 entries;
    interpretation_up_zh/down_zh on the 38 entries that carry a directional
    up/down reading; interpretation_neutral_zh on all 46. Counts pinned so a
    future edit that silently drops a translation is caught here, not just by
    the (already fail-closed) validator."""
    has_basis_zh = sum(1 for e in real_entries if e.get("unit_or_basis_zh"))
    has_up_zh = sum(1 for e in real_entries if e.get("interpretation_up_zh"))
    has_down_zh = sum(1 for e in real_entries if e.get("interpretation_down_zh"))
    has_neutral_zh = sum(1 for e in real_entries if e.get("interpretation_neutral_zh"))
    assert has_basis_zh == 46
    assert has_up_zh == 38
    assert has_down_zh == 38
    assert has_neutral_zh == 46
    # and every _zh sibling implies a present _en value (no orphan translations)
    for e in real_entries:
        for base in ("unit_or_basis", "interpretation_up", "interpretation_down", "interpretation_neutral"):
            if e.get(f"{base}_zh"):
                assert e.get(base), f"{e['id']}: {base}_zh present without {base}"


def test_real_registry_builds_expected_families(real_entries):
    vm, families, letters = build_view_model(real_entries)
    assert len(vm) == 46
    assert sum(f["count"] for f in families) == 46
    assert [f["id"] for f in families] == [
        "regime", "liquidity", "volatility-stress", "rates-curve", "credit",
        "breadth-participation", "flows-positioning", "calendar-events",
        "doctrine", "cross-asset-basics",
    ]
    assert letters[0] == "A" and letters[-1] == "Z" and len(letters) == 26


def test_search_key_is_normalized():
    key = search_key({"label_en": "VIX", "label_zh": "", "id": "vix", "aliases_en": ["Fear Gauge!"]})
    assert " " not in key and "!" not in key
    assert key == key.lower()


def test_initial_of_handles_ascii_and_none():
    assert initial_of("VIX") == "V"
    assert initial_of("") == "#"


# ---------------------------------------------------------------------------
# 3 & 4 · rendered page: anchor stability + EN/ZH parity
# ---------------------------------------------------------------------------

def _render_page(entries_vm, families_vm, letters, coverage=None,
                 generated_at="2026-09-02 00:00 UTC"):
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)
    return env.get_template("reference.html.j2").render(
        entries=entries_vm, families=families_vm, letters=letters,
        generated_at=generated_at, coverage=coverage or [],
    )


@pytest.fixture(scope="module")
def rendered_html(real_entries, real_coverage):
    entries_vm, families_vm, letters = build_view_model(real_entries)
    return _render_page(entries_vm, families_vm, letters, coverage=real_coverage)


def test_every_entry_id_is_a_real_anchor(real_entries, rendered_html):
    for e in real_entries:
        assert re.search(r'id="%s"' % re.escape(e["id"]), rendered_html), (
            f"entry id {e['id']!r} has no id=\"...\" anchor in the rendered page"
        )


def test_every_entry_shows_both_languages(real_entries, rendered_html):
    # One <article id="{id}" ...>...</article> block per entry — check each
    # block individually so a single missing l-zh span is attributable.
    for e in real_entries:
        m = re.search(
            r'<article class="rf-e" id="%s".*?</article>' % re.escape(e["id"]),
            rendered_html, re.DOTALL,
        )
        assert m, f"no <article> block found for entry {e['id']!r}"
        block = m.group(0)
        assert 'class="l-en"' in block, f"{e['id']!r}: no l-en span in rendered block"
        assert 'class="l-zh"' in block, f"{e['id']!r}: no l-zh span in rendered block"


def test_zh_supplement_fields_render_real_translation(real_entries, rendered_html):
    """Turns the old graceful t(en, zh='') fallback into an actual parity
    requirement: wherever the registry carries unit_or_basis / interpretation_*
    in English, the rendered block must show the REAL Chinese translation from
    the ZH supplement (HTML-escaped substring match — the template is
    Environment(autoescape=True), so a straight `"` inside a zh value like
    risk-radar's 'the "scare" scenarios' legitimately renders as `&#34;`) —
    not the English text doing double duty as the l-zh span's content."""
    from markupsafe import escape

    fields = ("unit_or_basis", "interpretation_up", "interpretation_down", "interpretation_neutral")
    checked = 0
    for e in real_entries:
        m = re.search(
            r'<article class="rf-e" id="%s".*?</article>' % re.escape(e["id"]),
            rendered_html, re.DOTALL,
        )
        assert m, f"no <article> block found for entry {e['id']!r}"
        block = m.group(0)
        for base in fields:
            zh_val = e.get(f"{base}_zh")
            if not zh_val:
                continue
            checked += 1
            expected = str(escape(zh_val))
            assert expected in block, (
                f"{e['id']!r}: {base}_zh value {zh_val!r} not found (escaped: {expected!r}) in "
                "rendered block (falling back to English would mean this assertion fails)"
            )
    assert checked == 46 + 38 + 38 + 46  # matches test_real_registry_zh_supplement_coverage


def test_no_unrendered_jinja_braces(rendered_html):
    assert "{{" not in rendered_html and "{%" not in rendered_html


def test_footer_authority_ceiling_present(rendered_html):
    assert "Reference only" in rendered_html
    assert "仅供参考" in rendered_html


def test_unknown_anchor_state_and_search_input_are_server_rendered(rendered_html):
    # Both are hidden-by-default progressive-enhancement affordances (contract
    # §7): they must exist in the server-rendered markup even though JS reveals
    # them, so a JS-disabled reader never sees a blank page or a broken filter.
    assert 'class="rf-miss mx-empty"' in rendered_html
    assert 'id="rf-q"' in rendered_html


# ---------------------------------------------------------------------------
# 5 · A-MO-W2-1 coverage ledger + owner block + dashboard chips
# ---------------------------------------------------------------------------

# Frozen census of faces this wave accounted for. A silent drop (or an
# undeclared extra) fails the floor-pin rather than vanishing from the page.
DOCUMENTED_COVERAGE_ELEMENTS = (
    "Prophet Stock Signals Board",
    "Sector Act-Now Board",
    "Regime Badge",
    "Posture Chip",
)

DASHBOARD_LOOKUP_IDS = (
    "market-state-score",
    "regime-quadrant",
    "transition-state",
    "risk-radar",
    "evidence-matrix",
    "sector-heat",
)

US_STOCKS_OWNER_ANCHORS = (
    "action-board",
    "equity-scoreboard",
    "advanced-breadth",
    "dash-mtf-section",
)


def _coverage_exc(**overrides) -> dict:
    row = {
        "element_en": "Sample Face",
        "element_zh": "示例面板",
        "surface": "us_stocks.html",
        "state": "not_an_indicator",
        "reason_en": "A board, not a measure.",
        "reason_zh": "这是看板，不是指标。",
        "see_ids": [],
    }
    row.update(overrides)
    return row


def test_coverage_floor_pins_documented_elements(real_coverage):
    """Lead-line census: the committed ledger lists exactly the documented
    faces, so an undocumented drop cannot hide behind a shrinking count."""
    names = tuple(c["element_en"] for c in real_coverage)
    assert names == DOCUMENTED_COVERAGE_ELEMENTS
    assert len(real_coverage) == 4


def test_every_documented_element_is_accounted_for(real_raw, real_entries, real_coverage):
    """Every coverage_exceptions row is either not_an_indicator or covered_by
    a real registry id; no documented face is silently absent."""
    raw_list = real_raw["coverage_exceptions"]
    assert len(raw_list) == len(real_coverage) == 4
    known = {e["id"] for e in real_entries}
    for row in raw_list:
        assert row["element_en"] in DOCUMENTED_COVERAGE_ELEMENTS
        assert (row.get("element_zh") or "").strip()
        assert row["state"] in ("not_an_indicator", "covered_by")
        for sid in row.get("see_ids") or []:
            assert sid in known, f"{row['element_en']}: see_ids {sid!r} is not a registry id"


def test_wave_has_no_not_covered_exceptions_yet(real_coverage):
    """Documented reason the not_covered CSS is unused against committed data:
    this wave only enumerated faces that are not-a-measure or already covered.
    A future face with no library home must add a not_covered row, not omit it."""
    states = {c["state"] for c in real_coverage}
    assert "not_covered" not in states
    assert states == {"not_an_indicator", "covered_by"}


def test_coverage_exceptions_unknown_state_fails_closed():
    raw = _registry(_base_entry())
    raw["coverage_exceptions"] = [_coverage_exc(state="invented")]
    with pytest.raises(RegistryError) as exc:
        validate_coverage_exceptions(raw, raw["entries"])
    assert "state must be one of" in _errors(exc.value)


def test_coverage_exceptions_covered_by_requires_see_ids():
    raw = _registry(_base_entry())
    raw["coverage_exceptions"] = [_coverage_exc(state="covered_by", see_ids=[])]
    with pytest.raises(RegistryError) as exc:
        validate_coverage_exceptions(raw, raw["entries"])
    assert "state:covered_by requires non-empty see_ids" in _errors(exc.value)


def test_coverage_exceptions_not_covered_requires_both_reasons():
    raw = _registry(_base_entry())
    raw["coverage_exceptions"] = [_coverage_exc(
        state="not_covered", reason_en="", reason_zh="",
    )]
    with pytest.raises(RegistryError) as exc:
        validate_coverage_exceptions(raw, raw["entries"])
    assert "state:not_covered requires non-empty reason_en" in _errors(exc.value)
    assert "state:not_covered requires non-empty reason_zh" in _errors(exc.value)


def test_coverage_exceptions_reason_both_or_neither_for_every_state():
    """MAJOR 1: a covered_by row with only reason_en used to pass validation
    and print the literal string 'None' into the ZH page."""
    raw = _registry(_base_entry())
    raw["coverage_exceptions"] = [_coverage_exc(
        state="covered_by",
        see_ids=["sample-term"],
        reason_en="Explained under Sample Term.",
        reason_zh="",
    )]
    with pytest.raises(RegistryError) as exc:
        validate_coverage_exceptions(raw, raw["entries"])
    assert "reason_en and reason_zh must both be present or both empty" in _errors(exc.value)


def test_coverage_exceptions_see_ids_scalar_is_a_type_error():
    """MINOR 2: a string see_ids used to iterate per character and emit one
    'unknown id' error per letter. Fail-closed with a type error instead."""
    raw = _registry(_base_entry())
    raw["coverage_exceptions"] = [_coverage_exc(
        state="covered_by", see_ids="sample-term",
    )]
    with pytest.raises(RegistryError) as exc:
        validate_coverage_exceptions(raw, raw["entries"])
    msg = _errors(exc.value)
    assert "see_ids must be a list" in msg
    assert "unknown id 's'" not in msg


def test_coverage_exceptions_unknown_see_id_fails_closed():
    raw = _registry(_base_entry())
    raw["coverage_exceptions"] = [_coverage_exc(
        state="covered_by", see_ids=["ghost-entry"],
    )]
    with pytest.raises(RegistryError) as exc:
        validate_coverage_exceptions(raw, raw["entries"])
    assert "see_ids references unknown id 'ghost-entry'" in _errors(exc.value)


def test_coverage_ledger_renders_every_exception(real_coverage, rendered_html):
    from markupsafe import escape

    assert 'id="coverage"' in rendered_html
    assert f'<span class="tnum">{len(real_coverage)}</span>' in rendered_html
    assert "dashboard elements are listed here instead of above" in rendered_html
    assert "项看板元素列在此处而非上方" in rendered_html
    for c in real_coverage:
        assert str(escape(c["element_en"])) in rendered_html
        assert str(escape(c["element_zh"])) in rendered_html
        assert f'rf-cov-row--{c["state"]}' in rendered_html
        if c["state"] == "covered_by":
            assert "Explained under another name" in rendered_html
            assert "已在其他条目中说明" in rendered_html
        if c["state"] == "not_an_indicator":
            assert "Not a measure" in rendered_html
            assert "不是一项指标" in rendered_html
        for ref in c["see"]:
            assert f'href="#{ref["id"]}"' in rendered_html


def test_not_covered_ledger_row_renders_still_missing_state():
    """The not_covered branch (and its only theme-divergent CSS class) is
    dead against committed data; this fixture is the live proof it executes."""
    entries = [_base_entry()]
    raw = _registry(*entries)
    raw["coverage_exceptions"] = [_coverage_exc(
        state="not_covered",
        element_en="Future Face",
        element_zh="未来面板",
        reason_en="This face is not in the library yet.",
        reason_zh="该面板尚未收入词库。",
    )]
    coverage = build_coverage_view_model(
        validate_coverage_exceptions(raw, entries), entries,
    )
    vm, families, letters = build_view_model(entries)
    html = _render_page(vm, families, letters, coverage=coverage)
    assert "rf-cov-row--not_covered" in html
    assert "Not in the library yet" in html
    assert "尚未收录" in html
    assert "This face is not in the library yet." in html
    assert "该面板尚未收入词库。" in html
    assert ">None<" not in html


def test_coverage_reason_zh_none_does_not_print_literal_none():
    """Template guard: a malformed VM with reason_en and reason_zh=None
    must not print the machine string 'None' into the ZH span."""
    entries = [_base_entry()]
    vm, families, letters = build_view_model(entries)
    coverage = [{
        "state": "covered_by",
        "element_en": "Regime Badge",
        "element_zh": "市场状态徽标",
        "reason_en": "Explained under Market Regime.",
        "reason_zh": None,
        "surface_label_en": "US Stocks",
        "surface_label_zh": "美股",
        "see": [{"id": "sample-term", "label_en": "Sample Term", "label_zh": "示例术语"}],
    }]
    html = _render_page(vm, families, letters, coverage=coverage)
    assert "Explained under Market Regime." in html
    assert ">None<" not in html
    assert "None</span>" not in html


def test_owner_block_always_renders_and_unlinked_note_matches_page_level_refs(
        real_entries, rendered_html):
    unlinked = 0
    linked = 0
    for e in real_entries:
        m = re.search(
            r'<article class="rf-e" id="%s".*?</article>' % re.escape(e["id"]),
            rendered_html, re.DOTALL,
        )
        assert m, f"no <article> block found for entry {e['id']!r}"
        block = m.group(0)
        assert "Where you’ll see this" in block or "Where you'll see this" in block
        assert "在哪里出现" in block
        if "#" in e["owner_ref"]:
            assert f'href="{e["owner_ref"]}"' in block
            assert "We can’t link straight to it on that page yet" not in block
            linked += 1
        else:
            assert f'href="{e["owner_ref"]}"' in block
            assert "We can’t link straight to it on that page yet" in block
            assert "暂时无法直接跳转到该页面上的位置" in block
            unlinked += 1
    assert unlinked == 4  # the four page-level aibrief.html owner_refs
    assert linked == 42
    assert "Not on a page we can link to yet." not in rendered_html


def test_no_owner_branch_renders_printed_null():
    """The empty-owner_refs branch never fires against committed data
    (owner_ref is required). Fixture proves the printed-null copy exists."""
    entries = [_base_entry()]
    vm, families, letters = build_view_model(entries)
    vm[0]["owner_refs"] = []
    html = _render_page(vm, families, letters, coverage=[])
    assert "Not on a page we can link to yet." in html
    assert "暂时还没有可跳转的页面。" in html
    assert "Where you’ll see this" in html or "Where you'll see this" in html


def test_owner_unlinked_flag_is_true_iff_owner_ref_has_no_fragment(real_entries):
    vm, _, _ = build_view_model(real_entries)
    by_id = {row["id"]: row for row in vm}
    for e in real_entries:
        row = by_id[e["id"]]
        assert row["owner_unlinked"] == ("#" not in e["owner_ref"])
        assert row["owner_refs"], f"{e['id']}: owner_refs must be non-empty"


def test_dashboard_lookup_chip_ids_resolve(real_entries):
    text = (REPO / "templates" / "dashboard.html.j2").read_text(encoding="utf-8")
    ids = re.findall(r'class="mx5-deep-chip mx5-ref-chip" href="reference\.html#([a-z0-9-]+)"', text)
    known = {e["id"] for e in real_entries}
    assert tuple(ids) == DASHBOARD_LOOKUP_IDS
    missing = [i for i in ids if i not in known]
    assert missing == [], f"Look-up chips point at unknown registry ids: {missing}"


def test_us_stocks_owner_anchors_are_allowlisted_and_live():
    assert set(US_STOCKS_OWNER_ANCHORS) == KNOWN_OWNER_PAGES["us_stocks.html"]
    site_page = REPO / "site" / "us_stocks.html"
    if not site_page.exists():
        pytest.skip("site/us_stocks.html not materialized in this checkout")
    html = site_page.read_text(encoding="utf-8", errors="replace")
    for frag in US_STOCKS_OWNER_ANCHORS:
        assert f'id="{frag}"' in html, f"us_stocks.html missing id={frag!r}"
        is_live, note = check_anchor_liveness(REPO, "us_stocks.html", frag)
        assert is_live, f"us_stocks.html#{frag} is not live: {note}"


def test_sue_label_leads_with_plain_words(real_entries, rendered_html):
    """MINOR 3: the quant acronym no longer leads the customer-facing label."""
    sue = next(e for e in real_entries if e["id"] == "sue-earnings-surprise")
    assert sue["label_en"] == "Earnings Surprise (SUE)"
    assert sue["label_zh"] == "盈余惊喜 (SUE)"
    assert "SUE Earnings Surprise" not in rendered_html
    assert "Earnings Surprise (SUE)" in rendered_html
    assert "盈余惊喜 (SUE)" in rendered_html
