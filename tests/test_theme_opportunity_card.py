from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from lib.theme_opportunity_card import (
    AXES,
    CardPresentationError,
    COMPONENT_VERSION,
    OWNER_CONTRACT_SCHEMA,
    compose_from_owner_context,
    render_card,
    validate_presentation,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "theme_opportunity_owner_envelopes.json"
JS_PATH = ROOT / "templates" / "theme_opportunity_card.js"


def envelopes() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def envelope(theme_id: str = "ai_semiconductors") -> dict:
    return copy.deepcopy(next(
        item for item in envelopes()
        if item["theme_context"]["identity"]["theme_id"] == theme_id
    ))


def model(theme_id: str = "ai_semiconductors") -> dict:
    return compose_from_owner_context(envelope(theme_id))


def visible_text(html: str) -> str:
    return BeautifulSoup(html, "html.parser").get_text(" ", strip=True)


def run_js(method: str, value: dict) -> subprocess.CompletedProcess[str]:
    script = f"""
const fs = require('fs');
const vm = require('vm');
const sandbox = {{ window: {{}} }};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync({json.dumps(str(JS_PATH))}, 'utf8'), sandbox);
try {{
  const out = sandbox.window.ThemeOpportunityCard[{json.dumps(method)}]({json.dumps(value)});
  process.stdout.write(typeof out === 'string' ? out : JSON.stringify(out));
}} catch (error) {{
  process.stderr.write(String(error.message || error));
  process.exit(7);
}}
"""
    return subprocess.run(["node", "-e", script], capture_output=True, text=True)


def test_component_consumes_exact_owner_contract_without_inventing_wire_contract() -> None:
    value = model()
    assert value["source_contract"] == OWNER_CONTRACT_SCHEMA
    assert value["component_version"] == COMPONENT_VERSION
    assert tuple(value["axis_order"]) == AXES
    assert set(value["axes"]) == set(AXES)
    assert "opportunity" not in value["axes"]
    assert "evidence" not in value["axes"]
    assert "overall_verdict" not in value
    assert "contract_version" not in value


def test_independent_axes_survive_without_one_overall_verdict() -> None:
    html = render_card(model())
    soup = BeautifulSoup(html, "html.parser")
    assert len(soup.select(".toc-axis")) == 5
    assert soup.select_one('[data-axis="leadership"][data-owner-state="DETECTED"]')
    assert soup.select_one('[data-axis="thesis"][data-owner-state="NOT_DETECTED"]')
    assert soup.select_one('[data-axis="entry"][data-owner-state="UNAVAILABLE"]')
    assert soup.select_one('[data-axis="health"][data-owner-state="STALE"]')
    assert not soup.select("[data-display-state]")
    assert "Stock qualification is independent" in visible_text(html)


def test_owner_state_is_opaque_but_presentation_tone_is_bounded() -> None:
    value = envelope()
    value["theme_context"]["dimensions"]["leadership"]["state"] = "OWNER_DEFINED_STATE"
    assert compose_from_owner_context(value)["axes"]["leadership"]["state"] == "OWNER_DEFINED_STATE"
    value = envelope()
    value["display"]["dimensions"]["leadership"]["tone"] = "bullish_magic"
    with pytest.raises(CardPresentationError, match="tone"):
        compose_from_owner_context(value)


def test_lane_a_authority_is_closed_in_python_and_javascript() -> None:
    for key in ("may_rank", "may_gate", "may_size", "may_escalate", "may_trade"):
        value = envelope()
        value["theme_context"]["authority"][key] = True
        with pytest.raises(CardPresentationError, match=key):
            compose_from_owner_context(value)
        result = run_js("fromOwnerContext", value)
        assert result.returncode == 7
        assert key in result.stderr


def test_safe_existing_routes_are_preserved_and_external_routes_refused() -> None:
    html = render_card(model())
    soup = BeautifulSoup(html, "html.parser")
    assert {a["href"] for a in soup.select(".toc-routes a")} == {
        "state_of_themes.html#theme-ai_semiconductors",
        "foresight.html#theme-ai_semiconductors",
        "radar.html#theme-ai_semiconductors",
        "sector_central.html#confluence",
    }
    for bad in ("https://evil.example/x", "../radar.html", "%2e%2e/radar.html", "/radar.html"):
        value = envelope()
        value["display"]["routes"]["radar"] = bad
        with pytest.raises(CardPresentationError, match="safe relative route|preserve radar"):
            compose_from_owner_context(value)
        result = run_js("fromOwnerContext", value)
        assert result.returncode == 7
        assert "route" in result.stderr.lower()


def test_clocks_nulls_watermarks_and_correction_lineage_remain_visible() -> None:
    html = render_card(model())
    text = visible_text(html)
    assert "2026-09-18" in text
    assert "foresight" in text and "leadership" in text
    assert "first_observed=2026-09-18" in text
    assert "publication —" in text or "P —" in text
    assert "1970" not in html
    assert "0 min" not in html


def test_untrusted_copy_and_receipts_are_escaped() -> None:
    value = envelope()
    value["display"]["summary"]["what_changed_en"] = '<img src=x onerror="alert(1)">'
    value["theme_context"]["source_records"] = ["<script>alert(1)</script>"]
    html = render_card(compose_from_owner_context(value))
    assert "<img" not in html
    assert "<script>alert" not in html
    assert "&lt;img" in html
    assert "&lt;script&gt;" in html


def test_fixture_is_unmistakably_labeled_and_component_version_is_ui_only() -> None:
    html = render_card(model())
    assert "Fixture — not live data" in visible_text(html)
    assert f'data-component-version="{COMPONENT_VERSION}"' in html
    assert f'data-source-contract="{OWNER_CONTRACT_SCHEMA}"' in html
    assert 'data-source-record-ref="site/basketdata/theme_lanes.json#/theme_context/ai_semiconductors"' in html


def test_css_has_distinct_dark_light_and_entry_scope_treatments() -> None:
    css = (ROOT / "templates" / "theme_opportunity_card.css").read_text(encoding="utf-8")
    assert 'html[data-theme="dark"] .toc-card' in css
    assert 'html[data-theme="light"] .toc-card' in css
    assert '.toc-setup[data-qualified="true"]' in css
    assert '.toc-setup[data-headwind-warning="true"]' in css
    assert ".toc-axes" in css and ".toc-setups" in css
    assert "box-shadow" in css


def test_javascript_has_no_runtime_stylesheet_and_renders_exact_semantic_axes() -> None:
    js = JS_PATH.read_text(encoding="utf-8")
    assert 'createElement("style")' not in js
    assert "style.textContent" not in js
    result = run_js("fromOwnerContext", envelope())
    assert result.returncode == 0, result.stderr
    owner_model = json.loads(result.stdout)
    rendered = run_js("render", owner_model)
    assert rendered.returncode == 0, rendered.stderr
    html = rendered.stdout
    for axis, state in (
        ("leadership", "DETECTED"),
        ("thesis", "NOT_DETECTED"),
        ("crowding", "NOT_DETECTED"),
        ("entry", "UNAVAILABLE"),
        ("health", "STALE"),
    ):
        assert f'data-axis="{axis}"' in html
        assert f'data-owner-state="{state}"' in html
    assert 'data-axis="opportunity"' not in html
    assert 'data-axis="evidence"' not in html
    assert "Fixture — not live data" in html


def test_template_and_site_assets_are_byte_identical() -> None:
    for name in ("theme_opportunity_card.css", "theme_opportunity_card.js"):
        assert (ROOT / "templates" / name).read_bytes() == (ROOT / "site" / name).read_bytes()


def test_display_copy_cannot_override_owner_state_or_authority() -> None:
    for key in (
        "state", "reason_code", "source_records", "clocks", "watermarks",
        "authority", "permissions", "display_state", "rank", "quality_score",
        "confidence_pct", "buyable", "price_target", "may_rank", "may_trade",
    ):
        value = envelope()
        value["display"]["summary"][key] = 1
        with pytest.raises(CardPresentationError, match=key):
            compose_from_owner_context(value)
        result = run_js("fromOwnerContext", value)
        assert result.returncode == 7
        assert key in result.stderr


def test_required_dimensions_and_clock_fields_fail_closed() -> None:
    value = envelope()
    del value["theme_context"]["dimensions"]["health"]
    with pytest.raises(CardPresentationError, match="five Lane A dimensions"):
        compose_from_owner_context(value)
    value = envelope()
    del value["theme_context"]["clocks"]["publication"]
    with pytest.raises(CardPresentationError, match="observation/availability/computation/publication"):
        compose_from_owner_context(value)


def test_lane_d_qualified_entry_preserves_exact_route_receipt_and_levels() -> None:
    value = model()
    setup = value["entry_setups"][0]
    assert setup["routing_state"] == "QUALIFIED_PENDING_CONFIRMATION_EXTENDED"
    assert setup["qualified"] is True
    assert setup["href"] == "stock.html#NVDA"
    assert setup["group_href"] == "subsector/semiconductors.html"
    assert setup["record_ref"] == "site/factordata/us_standouts.json#/buy/0"
    assert setup["record_id"] == "setup-nvda-20260918"
    assert setup["levels"] == {
        "trigger": "hold above 105",
        "zone": {"low": 100.0, "high": 105.0},
        "invalidation": 95.0,
        "chase_above": 110.0,
    }
    html = render_card(value)
    assert 'href="stock.html#NVDA"' in html
    assert 'data-entry-record-ref="site/factordata/us_standouts.json#/buy/0"' in html
    assert "group extended" in visible_text(html).lower()
    assert value["axes"]["entry"]["state"] == "UNAVAILABLE"


def test_proxy_stale_expired_and_headwind_context_never_become_qualified_setup() -> None:
    cases = {
        "data_center_power": ("QUALIFIED_GROUP_HEADWIND", False, True),
        "memory_storage": ("DESCRIPTIVE_ONLY_SETUP_STALE", False, False),
        "nuclear_power": ("DESCRIPTIVE_ONLY_PROXY", False, False),
    }
    for theme_id, (state, qualified, headwind) in cases.items():
        setup = model(theme_id)["entry_setups"][0]
        assert setup["routing_state"] == state
        assert setup["qualified"] is qualified
        assert setup["headwind_warning"] is headwind
    assert model("solar")["entry_setups"] == []


def test_encoded_external_entry_route_is_refused_by_both_adapters() -> None:
    value = envelope()
    value["entry_contexts"][0]["routes"]["instrument"] = "https%3A%2F%2Fevil.example%2Fsetup"
    with pytest.raises(CardPresentationError, match="safe relative route"):
        compose_from_owner_context(value)
    result = run_js("fromOwnerContext", value)
    assert result.returncode == 7
    assert "safe relative route" in result.stderr


def test_source_failure_cannot_silently_render_as_quiet() -> None:
    value = envelope()
    value["theme_context"]["dimensions"]["health"] = {
        "state": "UNAVAILABLE", "reason_code": "SOURCE_FAILED",
    }
    value["display"]["dimensions"]["health"] = {
        "label_en": "Quiet for now", "label_zh": "暂时平静",
        "reason_en": "Nothing notable yet.", "reason_zh": "暂无值得关注之处。",
        "tone": "neutral",
    }
    with pytest.raises(CardPresentationError, match="source failure|health"):
        compose_from_owner_context(value)
    result = run_js("fromOwnerContext", value)
    assert result.returncode == 7
    assert "source failure" in result.stderr or "health" in result.stderr


def test_sanitized_model_cannot_mutate_proxy_or_stale_context_into_qualified_entry() -> None:
    for mutation in ("proxy", "stale"):
        value = model()
        setup = value["entry_setups"][0]
        if mutation == "proxy":
            setup["relationship_kind"] = "PROXY"
            setup["instrument_kind"] = "PROXY_INSTRUMENT"
        else:
            setup["availability"] = "STALE"
        setup["qualified"] = True
        with pytest.raises(CardPresentationError, match="qualified|available|DIRECT"):
            validate_presentation(value)
        result = run_js("validate", value)
        assert result.returncode == 7
        assert "qualified" in result.stderr.lower()


def test_javascript_validates_names_receipts_and_null_semantics_like_python() -> None:
    value = model()
    del value["names"][0]["membership_as_of"]
    with pytest.raises(CardPresentationError, match="membership_as_of"):
        validate_presentation(value)
    result = run_js("validate", value)
    assert result.returncode == 7
    assert "membership_as_of" in result.stderr

    value = model()
    del value["receipts"]["clocks"]["availability"]
    with pytest.raises(CardPresentationError, match="observation/availability/computation/publication"):
        validate_presentation(value)
    result = run_js("validate", value)
    assert result.returncode == 7
    assert "observation/availability/computation/publication" in result.stderr


def test_all_owner_envelopes_render_with_five_axes_and_distinct_negative_states() -> None:
    expected = {
        "ai_semiconductors": ("STALE", "QUALIFIED_PENDING_CONFIRMATION_EXTENDED"),
        "data_center_power": ("UNCONFIRMED", "QUALIFIED_GROUP_HEADWIND"),
        "memory_storage": ("STALE", "DESCRIPTIVE_ONLY_SETUP_STALE"),
        "nuclear_power": ("UNCONFIRMED", "DESCRIPTIVE_ONLY_PROXY"),
        "solar": ("UNCONFIRMED", None),
    }
    for raw in envelopes():
        theme_id = raw["theme_context"]["identity"]["theme_id"]
        value = compose_from_owner_context(raw)
        html = render_card(value)
        soup = BeautifulSoup(html, "html.parser")
        assert len(soup.select(".toc-axis")) == 5
        assert value["axes"]["health"]["state"] == expected[theme_id][0]
        routing = value["entry_setups"][0]["routing_state"] if value["entry_setups"] else None
        assert routing == expected[theme_id][1]
        assert soup.select_one(f'#theme-{theme_id}')
        assert "rank=off" in visible_text(html)


def test_javascript_sanitized_model_validates_surface_summary_and_axis_watermarks() -> None:
    value = model()
    value["surface"]["current_route"] = "https://evil.example/theme"
    with pytest.raises(CardPresentationError, match="safe relative route"):
        validate_presentation(value)
    result = run_js("validate", value)
    assert result.returncode == 7
    assert "safe relative route" in result.stderr

    value = model()
    value["summary"]["may_trade"] = False
    with pytest.raises(CardPresentationError, match="may_trade"):
        validate_presentation(value)
    result = run_js("validate", value)
    assert result.returncode == 7
    assert "may_trade" in result.stderr

    value = model()
    value["axes"]["health"]["watermarks"] = []
    with pytest.raises(CardPresentationError, match="watermarks"):
        validate_presentation(value)
    result = run_js("validate", value)
    assert result.returncode == 7
    assert "watermarks" in result.stderr


def test_component_identity_marks_the_owner_contract_bound_revision() -> None:
    assert COMPONENT_VERSION == "theme-opportunity-card.presentation.v5"
    assert 'var COMPONENT_VERSION = "theme-opportunity-card.presentation.v5"' in JS_PATH.read_text(encoding="utf-8")


def test_lane_a_owner_label_value_band_are_preserved_and_owner_state_is_primary() -> None:
    value = envelope()
    leadership = value["theme_context"]["dimensions"]["leadership"]
    leadership.update({"label": "Dominant", "value": 66, "band": "LEADING"})

    card = compose_from_owner_context(value)
    axis = card["axes"]["leadership"]
    assert axis["state"] == "DETECTED"
    assert axis["owner_details"] == {
        "label": "Dominant",
        "value": 66,
        "band": "LEADING",
    }

    html = render_card(card)
    soup = BeautifulSoup(html, "html.parser")
    leadership_axis = soup.select_one('[data-axis="leadership"]')
    assert leadership_axis is not None
    assert leadership_axis.select_one(".toc-owner-state").get_text(strip=True) == "DETECTED"
    assert {
        item.get("data-owner-field"): item.get_text(" ", strip=True)
        for item in leadership_axis.select(".toc-owner-detail")
    } == {
        "label": "label Dominant",
        "value": "value 66",
        "band": "band LEADING",
    }


def test_lane_d_setup_clocks_and_correction_lineage_are_visible() -> None:
    card = model()
    html = render_card(card)
    soup = BeautifulSoup(html, "html.parser")
    setup = soup.select_one('[data-routing-state="QUALIFIED_PENDING_CONFIRMATION_EXTENDED"]')
    assert setup is not None

    clock_rows = {
        row.get("data-clock-owner"): row.get_text(" ", strip=True)
        for row in setup.select(".toc-setup-clock-row")
    }
    assert "2026-09-18" in clock_rows["stock_setup"]
    assert "2026-09-19T00:15:00Z" in clock_rows["stock_setup"]
    assert "owner_artifact_has_no_publication_clock" in clock_rows["stock_setup"]
    assert "2026-09-19T00:20:00Z" in clock_rows["group"]
    assert "2026-09-19T15:00:00Z" in clock_rows["live_entry_radar"]

    lineage = setup.select_one(".toc-setup-lineage")
    assert lineage is not None
    lineage_text = lineage.get_text(" ", strip=True)
    assert "source_revision=4" in lineage_text
    assert "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" in lineage_text


def test_lane_d_clock_receipt_shape_fails_closed() -> None:
    value = envelope()
    del value["entry_contexts"][0]["clocks"]["stock_setup"]["publication"]
    with pytest.raises(CardPresentationError, match="stock_setup.*observation/availability/computation/publication"):
        compose_from_owner_context(value)
    result = run_js("fromOwnerContext", value)
    assert result.returncode == 7
    assert "stock_setup" in result.stderr


def test_javascript_renderer_preserves_owner_details_and_setup_receipts() -> None:
    value = envelope()
    value["theme_context"]["dimensions"]["entry"].update({
        "label": "T1 pending",
        "value": "T1",
        "band": "EXTENDED",
    })
    built = run_js("fromOwnerContext", value)
    assert built.returncode == 0, built.stderr
    card = json.loads(built.stdout)
    assert card["axes"]["entry"]["owner_details"] == {
        "label": "T1 pending",
        "value": "T1",
        "band": "EXTENDED",
    }

    rendered = run_js("render", card)
    assert rendered.returncode == 0, rendered.stderr
    html = rendered.stdout
    assert '<strong class="toc-owner-state">UNAVAILABLE</strong>' in html
    assert 'data-owner-field="value"><b>value</b> T1' in html
    assert 'data-clock-owner="stock_setup"' in html
    assert "2026-09-19T00:15:00Z" in html
    assert "source_revision=4" in html
