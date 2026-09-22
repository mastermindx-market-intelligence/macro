from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path

import pytest

import lib.theme_opportunity_card as toc


def lane_a_row() -> dict:
    return {
        "schema": "theme_intelligence.consumer.v1",
        "identity": {
            "theme_id": "ai_semiconductors",
            "relationship_kind": "primary_basket",
            "basket_id": "ai_semiconductors",
            "market": "US",
            "horizon": "swing",
        },
        "dimensions": {
            "leadership": {
                "state": "DETECTED",
                "reason_code": "C_OWNER_AUTHORIZED",
                "label": "fresh leadership campaign",
                "source_records": ["site/basketdata/latest.json#/themes/ai_semiconductors"],
            },
            "thesis": {
                "state": "NOT_DETECTED",
                "reason_code": "NO_MACHINE_INVALIDATION_DETECTED",
                "stage": "WATCH",
            },
            "crowding": {
                "state": "NOT_DETECTED",
                "reason_code": "HIGH_CROWDING_NOT_DETECTED",
                "band": "low",
            },
            "entry": {
                "state": "UNAVAILABLE",
                "reason_code": "OWNER_FIELD_NOT_JOINED",
            },
            "health": {
                "state": "STALE",
                "reason_code": "PAGE_HAS_STALE_LEGS",
                "page_stale_legs": 1,
            },
        },
        "specialist_context": {
            "lane": "quiet",
            "stage": "WATCH",
            "divergence": "Hidden opportunity",
            "reason_codes": ["LANE_QUIET", "STAGE_WATCH"],
        },
        "source_records": ["site/basketdata/foresight_cascade.json"],
        "independent_evidence_families": ["price_leadership", "economic_thesis"],
        "clocks": {
            "observation": "2026-09-18",
            "availability": None,
            "computation": "2026-09-19T00:15:00Z",
            "publication": None,
        },
        "watermarks": {
            "snapshot": "2026-09-18",
            "inputs": {"foresight": "2026-09-18", "leadership": "2026-09-19"},
        },
        "bar_status": {"closed": True, "provisional": False},
        "correction_lineage": {
            "supersedes": None,
            "first_observed": "2026-09-18",
            "first_displayed": "2026-09-19T00:20:00Z",
        },
        "authority": {
            "is_context_only": True,
            "display_only": True,
            "not_a_signal": True,
            "may_rank": False,
            "may_gate": False,
            "may_size": False,
            "may_escalate": False,
            "may_trade": False,
        },
    }


def display_copy() -> dict:
    axis_copy = {
        "leadership": ("Leadership detected", "检测到领导力", "Price leadership remains visible.", "价格领导力仍然可见。", "up"),
        "thesis": ("No machine invalidation", "未检测到机器失效", "WATCH is non-confirmation, not deterioration.", "WATCH 表示尚未确认，而非恶化。", "info"),
        "crowding": ("Not crowded", "不拥挤", "No high crowding hazard is detected.", "未检测到高拥挤风险。", "neutral"),
        "entry": ("Theme entry unavailable", "主题入场读数不可用", "Theme-level entry has not been joined yet.", "主题层入场读数尚未接入。", "unknown"),
        "health": ("Some inputs are stale", "部分输入已陈旧", "One owner input is older than the current snapshot.", "一个所有者输入早于当前快照。", "warn"),
    }
    return {
        "theme": {"name_en": "AI Semiconductors", "name_zh": "AI半导体"},
        "surface": {
            "source_lens_en": "Theme Tracker",
            "source_lens_zh": "主题追踪",
            "current_route": "state_of_themes.html#theme-ai_semiconductors",
        },
        "summary": {
            "what_changed_en": "Leadership persists while the economic thesis remains unconfirmed.",
            "what_changed_zh": "领导力仍在，但经济论点尚未确认。",
            "why_matters_en": "Market leadership and thesis health are separate facts.",
            "why_matters_zh": "市场领导力与论点健康是两项独立事实。",
            "opportunity_en": "Watch the theme; do not infer a stock entry from the parent state.",
            "opportunity_zh": "继续观察主题；不要从母主题状态推断个股入场。",
            "risk_en": "A real owner falsifier or deterioration record would change the thesis read.",
            "risk_zh": "真实的所有者失效条件或恶化记录会改变论点读数。",
            "disagreement_en": "Leadership is positive while thesis confirmation is incomplete.",
            "disagreement_zh": "领导力为正，但论点确认尚未完成。",
        },
        "dimensions": {
            key: {
                "label_en": values[0],
                "label_zh": values[1],
                "reason_en": values[2],
                "reason_zh": values[3],
                "tone": values[4],
            }
            for key, values in axis_copy.items()
        },
        "names": [{
            "instrument_id": "NVDA",
            "symbol": "NVDA",
            "name_en": "NVIDIA",
            "name_zh": "英伟达",
            "relationship_kind": "DIRECT_MEMBER",
            "membership_basis": "point-in-time basket membership",
            "membership_as_of": "2026-09-18",
        }],
        "routes": {
            "tracker": "state_of_themes.html#theme-ai_semiconductors",
            "foresight": "foresight.html#theme-ai_semiconductors",
            "radar": "radar.html#theme-ai_semiconductors",
            "sector": "sector_central.html#confluence",
        },
        "input_health": [],
    }


def owner_envelope() -> dict:
    return {
        "fixture": True,
        "theme_context_ref": "site/basketdata/theme_lanes.json#/theme_context/ai_semiconductors",
        "theme_context": lane_a_row(),
        "display": display_copy(),
        "entry_contexts": [],
    }


def test_lane_a_contract_maps_exact_five_dimensions_without_parallel_axes() -> None:
    adapter = getattr(toc, "compose_from_owner_context", None)
    assert callable(adapter), "Lane E must consume Lane A's accepted owner contract directly"
    model = adapter(owner_envelope())
    assert model["source_contract"] == "theme_intelligence.consumer.v1"
    assert tuple(model["axis_order"]) == (
        "leadership", "thesis", "crowding", "entry", "health",
    )
    assert set(model["axes"]) == set(model["axis_order"])
    assert "opportunity" not in model["axes"]
    assert "evidence" not in model["axes"]
    assert model["axes"]["leadership"]["state"] == "DETECTED"
    assert model["axes"]["thesis"]["state"] == "NOT_DETECTED"
    assert model["axes"]["health"]["state"] == "STALE"


def test_lane_a_authority_ceiling_fails_closed_before_presentation() -> None:
    value = owner_envelope()
    value["theme_context"]["authority"]["may_rank"] = True
    with pytest.raises(toc.CardPresentationError, match="may_rank"):
        toc.compose_from_owner_context(value)

    value = owner_envelope()
    value["theme_context"]["authority"]["display_only"] = False
    with pytest.raises(toc.CardPresentationError, match="display_only"):
        toc.compose_from_owner_context(value)


def lane_d_entry_context(
    *,
    routing_state: str = "QUALIFIED_PENDING_CONFIRMATION_EXTENDED",
    may_present: bool = True,
    headwind_warning: bool = False,
    relationship: str = "DIRECT_MEMBER",
    instrument_kind: str = "DIRECT_INSTRUMENT",
    availability: str = "AVAILABLE",
    setup_qualification: str = "QUALIFIED",
    expiry_state: str = "ACTIVE",
) -> dict:
    return {
        "schema": "mastermind.entry_context.v1",
        "context_only": True,
        "instrument": {"id": "NVDA", "kind": instrument_kind, "market": "US"},
        "relationship": {
            "kind": relationship,
            "availability": "AVAILABLE",
            "absence_scope": "site/marketdata/subsector_confluence.json",
            "global_absence": None,
            "group_id": "semiconductors",
            "group_kind": "subsector",
            "group_label": "Semiconductors",
        },
        "observation": {
            "market": "US",
            "timeframe": "1D",
            "session": "EOD",
            "horizon": "daily",
            "weighting": "equal",
        },
        "qualification": {
            "member_eligibility": "QUALIFIED",
            "member_gate": "QUALIFIED",
            "stock_setup": setup_qualification,
            "member_tier": "T1",
            "member_reason": "buy fired; forward confirmation pending",
            "basis": "member_signal_gate_and_existing_stock_setup",
            "inherited_from_group": False,
        },
        "confirmation": {
            "state": "PENDING",
            "group_state": "PENDING",
            "basis": "owner_fields_only",
        },
        "group_context": {
            "entry_tier": "T1",
            "entry_buyable": True,
            "regime_state": "EXTENDED",
            "headwind": headwind_warning,
            "extended": True,
            "as_of": "2026-09-18",
        },
        "stock_setup": {
            "availability": availability,
            "scope": "site/factordata/us_standouts.json",
            "global_absence": None,
            "source_lane": "buy",
            "source_ref": "site/factordata/us_standouts.json#/buy/0",
            "source_setup_id": "setup-nvda-20260918",
            "source_setup_id_reason": None,
            "as_of": "2026-09-18",
            "age_days": 1,
            "status": "partial",
            "tier": "T1",
            "reason": "buy fired; forward confirmation pending",
        },
        "lineage": {
            "state": "AVAILABLE",
            "source_revision": 4,
            "correction_of": None,
            "supersedes": None,
            "source_content_sha256": "sha256:" + "a" * 64,
            "reason": None,
        },
        "levels": {
            "trigger": "hold above 105",
            "zone": {"low": 100.0, "high": 105.0},
            "invalidation": 95.0,
            "chase_above": 110.0,
        },
        "expiry": {
            "state": expiry_state,
            "expires_at": None,
            "expires_at_reason": "owner_record_has_no_absolute_expiry",
            "freshness_basis": {
                "ticks": 1,
                "fresh_bars": 1,
                "fresh_bars_knowable": True,
                "near_miss_reason": None,
            },
        },
        "prophet": {
            "availability": "AVAILABLE",
            "version": "us_prophet_v3",
            "score": 61.2,
            "score_kind": "unfitted equal-weight evidence-family vote",
            "score_authority": "context_only",
            "source_ref": "site/factordata/us_standouts.json#/buy/0",
            "context_only": True,
        },
        "live_entry_radar": {
            "availability": "AVAILABLE",
            "scope": "site/live/entry_radar.json",
            "as_of": "2026-09-19",
            "state": "evaluated",
            "reasons": [],
            "episode_refs": ["ep-nvda"],
            "context_only": True,
        },
        "clocks": {
            "stock_setup": {
                "observation": {"value": "2026-09-18", "reason": None},
                "availability": {"value": None, "reason": "owner_artifact_has_no_availability_clock"},
                "computation": {"value": "2026-09-19T00:15:00Z", "reason": None},
                "publication": {"value": None, "reason": "owner_artifact_has_no_publication_clock"},
            },
            "group": {
                "observation": {"value": "2026-09-18", "reason": None},
                "availability": {"value": None, "reason": "owner_record_has_no_availability_clock"},
                "computation": {"value": "2026-09-19T00:20:00Z", "reason": None},
                "publication": {"value": None, "reason": "owner_record_has_no_publication_clock"},
            },
            "live_entry_radar": {
                "observation": {"value": "2026-09-19", "reason": None},
                "availability": {"value": None, "reason": "owner_artifact_has_no_availability_clock"},
                "computation": {"value": "2026-09-19T15:00:00Z", "reason": None},
                "publication": {"value": None, "reason": "owner_artifact_has_no_publication_clock"},
            },
        },
        "routes": {
            "instrument": "stock.html#NVDA",
            "group": "subsector/semiconductors.html",
        },
        "routing": {
            "state": routing_state,
            "may_navigate": True,
            "may_present_as_qualified_setup": may_present,
            "may_present_as_headwind_warning": headwind_warning,
            "rank_effect": "NONE",
            "size_effect": "NONE",
        },
        "permissions": {
            "may_describe": True,
            "may_link": True,
            "may_rank": False,
            "may_gate": False,
            "may_size": False,
            "may_escalate": False,
            "may_trade": False,
        },
        "authority": {
            "may_rank": False,
            "may_gate": False,
            "may_size": False,
            "may_escalate": False,
            "may_trade": False,
        },
    }


def test_lane_d_qualified_setup_preserves_exact_route_receipt_and_extended_state() -> None:
    value = owner_envelope()
    value["entry_contexts"] = [lane_d_entry_context()]
    model = toc.compose_from_owner_context(value)
    assert len(model["entry_setups"]) == 1
    setup = model["entry_setups"][0]
    assert setup["routing_state"] == "QUALIFIED_PENDING_CONFIRMATION_EXTENDED"
    assert setup["qualified"] is True
    assert setup["headwind_warning"] is False
    assert setup["may_navigate"] is True
    assert setup["href"] == "stock.html#NVDA"
    assert setup["group_href"] == "subsector/semiconductors.html"
    assert setup["record_ref"] == "site/factordata/us_standouts.json#/buy/0"
    assert setup["record_id"] == "setup-nvda-20260918"
    assert setup["levels"]["zone"] == {"low": 100.0, "high": 105.0}
    assert setup["group_extended"] is True


def _visible_text(html: str) -> str:
    from bs4 import BeautifulSoup
    return BeautifulSoup(html, "html.parser").get_text(" ", strip=True)


def test_rendered_owner_card_uses_five_scoped_axes_and_exact_lane_d_setup() -> None:
    value = owner_envelope()
    value["entry_contexts"] = [lane_d_entry_context()]
    html = toc.render_card(toc.compose_from_owner_context(value))
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    axes = [node["data-axis"] for node in soup.select("[data-axis]")]
    assert axes == ["leadership", "thesis", "crowding", "entry", "health"]
    assert "opportunity" not in axes and "evidence" not in axes
    assert soup.select_one('[data-axis="entry"][data-owner-state="UNAVAILABLE"]')
    setup = soup.select_one(
        '[data-routing-state="QUALIFIED_PENDING_CONFIRMATION_EXTENDED"]'
    )
    assert setup is not None
    assert setup["data-qualified"] == "true"
    link = setup.select_one('a[href="stock.html#NVDA"]')
    assert link is not None
    assert link["data-entry-record-ref"] == "site/factordata/us_standouts.json#/buy/0"
    visible = _visible_text(html)
    assert "Theme-level entry" in visible
    assert "Individual setups" in visible
    assert "confirmation pending" in visible.lower()
    assert "group extended" in visible.lower()


def _run_js_owner(value: dict) -> "subprocess.CompletedProcess[str]":
    import json
    import subprocess
    from pathlib import Path

    js_path = Path(__file__).resolve().parents[1] / "templates" / "theme_opportunity_card.js"
    script = f"""
const fs = require('fs');
const vm = require('vm');
const sandbox = {{ window: {{}} }};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync({json.dumps(str(js_path))}, 'utf8'), sandbox);
try {{
  const model = sandbox.window.ThemeOpportunityCard.fromOwnerContext({json.dumps(value)});
  process.stdout.write(sandbox.window.ThemeOpportunityCard.render(model));
}} catch (error) {{
  process.stderr.write(String(error && (error.stack || error.message) || error));
  process.exit(7);
}}
"""
    return subprocess.run(["node", "-e", script], capture_output=True, text=True)


def test_client_adapter_consumes_same_lane_a_and_lane_d_contracts() -> None:
    value = owner_envelope()
    value["entry_contexts"] = [lane_d_entry_context()]
    result = _run_js_owner(value)
    assert result.returncode == 0, result.stderr
    html = result.stdout
    for axis, state in (
        ("leadership", "DETECTED"),
        ("thesis", "NOT_DETECTED"),
        ("crowding", "NOT_DETECTED"),
        ("entry", "UNAVAILABLE"),
        ("health", "STALE"),
    ):
        assert f'data-axis="{axis}"' in html
        assert f'data-owner-state="{state}"' in html
    assert 'data-routing-state="QUALIFIED_PENDING_CONFIRMATION_EXTENDED"' in html
    assert 'href="stock.html#NVDA"' in html
    assert "opportunity\" data-owner-state" not in html
    assert "evidence\" data-owner-state" not in html


def test_component_css_distinguishes_theme_axes_from_individual_setups() -> None:
    from pathlib import Path

    css = (
        Path(__file__).resolve().parents[1]
        / "templates"
        / "theme_opportunity_card.css"
    ).read_text(encoding="utf-8")
    assert ".toc-specialist" in css
    assert ".toc-setups" in css
    assert ".toc-setup" in css
    assert '.toc-setup[data-qualified="true"]' in css
    assert '.toc-setup[data-headwind-warning="true"]' in css
    assert ".toc-watermarks" in css


def test_source_failure_cannot_be_presented_as_quiet_or_positive() -> None:
    value = owner_envelope()
    value["theme_context"]["dimensions"]["health"] = {
        "state": "UNAVAILABLE",
        "reason_code": "SOURCE_FAILED",
    }
    value["display"]["dimensions"]["health"] = {
        "label_en": "Quiet for now",
        "label_zh": "暂时平静",
        "reason_en": "Nothing notable yet.",
        "reason_zh": "暂无值得关注之处。",
        "tone": "neutral",
    }
    with pytest.raises(toc.CardPresentationError, match="source failure|health"):
        toc.compose_from_owner_context(value)


def test_sanitized_setup_cannot_relabel_proxy_or_stale_context_as_qualified() -> None:
    value = owner_envelope()
    value["entry_contexts"] = [lane_d_entry_context()]
    model = toc.compose_from_owner_context(value)
    setup = model["entry_setups"][0]
    setup["relationship_kind"] = "PROXY"
    setup["instrument_kind"] = "PROXY_INSTRUMENT"
    setup["qualified"] = True
    with pytest.raises(toc.CardPresentationError, match="qualified|proxy|routing"):
        toc.validate_presentation(model)

    value = owner_envelope()
    value["entry_contexts"] = [lane_d_entry_context()]
    model = toc.compose_from_owner_context(value)
    setup = model["entry_setups"][0]
    setup["availability"] = "STALE"
    setup["qualified"] = True
    with pytest.raises(toc.CardPresentationError, match="qualified|stale|availability"):
        toc.validate_presentation(model)


def _run_js_validate(model: dict) -> subprocess.CompletedProcess[str]:
    js_path = Path(__file__).resolve().parents[1] / "templates" / "theme_opportunity_card.js"
    script = f"""
const fs = require('fs');
const vm = require('vm');
const sandbox = {{ window: {{}} }};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync({json.dumps(str(js_path))}, 'utf8'), sandbox);
try {{
  sandbox.window.ThemeOpportunityCard.validate({json.dumps(model)});
  process.stdout.write('accepted');
}} catch (error) {{
  process.stderr.write(String(error.message || error));
  process.exit(7);
}}
"""
    return subprocess.run(["node", "-e", script], capture_output=True, text=True)


def test_js_sanitized_setup_boundary_matches_python() -> None:
    value = owner_envelope()
    value["entry_contexts"] = [lane_d_entry_context()]
    model = toc.compose_from_owner_context(value)
    setup = model["entry_setups"][0]
    setup["relationship_kind"] = "PROXY"
    setup["instrument_kind"] = "PROXY_INSTRUMENT"
    setup["qualified"] = True
    result = _run_js_validate(model)
    assert result.returncode == 7
    assert any(word in result.stderr.lower() for word in ("qualified", "proxy", "routing"))
