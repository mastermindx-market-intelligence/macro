"""Homepage economic context consumes the existing sealed workspace publication.

Synthetic owner fixtures exercise the real composers, manifest reader and view.
No real feed, wall clock, network or portfolio is required for these regressions.
"""
from __future__ import annotations
import copy
import importlib
import json
from pathlib import Path
import pytest
from engine.market_os.macro_workspaces import contract, growth, inflation, financial_conditions
from scripts import build_macro_suite_pages as pages
from tests.test_macro_workspace_growth import _base_regime as growth_owner
from tests.test_macro_workspace_inflation import _base_intel as inflation_owner
from tests.test_macro_workspace_financial_conditions import _base_regime as conditions_owner

BUILT = "2026-09-06T12:00:00Z"
IDS = ("growth_real_economy", "inflation_system", "financial_conditions")


def _module():
    assert importlib.util.find_spec("lib.macro_economic_backdrop") is not None, "Economic backdrop consumer is not implemented"
    return importlib.import_module("lib.macro_economic_backdrop")


def _snapshots():
    owners = (growth.compose(growth_owner(), built_at=BUILT),
              inflation.compose(inflation_owner(), built_at=BUILT),
              financial_conditions.compose(conditions_owner(), built_at=BUILT))
    return {s["workspace"]["id"]: contract.finalize(s) for s in owners}


def _publish(root: Path, snapshots: dict) -> Path:
    manifest = {"min_client_contract": pages.MIN_CLIENT_CONTRACT, "workspaces": {}}
    for wid, raw in snapshots.items():
        snap = contract.finalize(raw)
        contract.validate(snap)
        relative = f"workspaces/{wid}/US/latest.json"
        payload = (json.dumps(snap, ensure_ascii=False, sort_keys=True) + "\n").encode()
        file = root / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(payload)
        manifest["workspaces"][f"{wid}/US"] = {"path": relative,
            "content_sha256": snap["generation"]["content_sha256"], "bytes": len(payload)}
    (root / "workspaces/manifest.json").write_text(json.dumps(manifest))
    return root


def _read(root, snapshots=None):
    _publish(root, snapshots if snapshots is not None else _snapshots())
    return _module().build_economic_backdrop(root, page_built_at=BUILT)


def test_reads_three_fixed_topics_through_real_publication(tmp_path):
    snapshots = _snapshots()
    cards = _read(tmp_path, snapshots)
    assert tuple(c["id"] for c in cards) == IDS
    for card in cards:
        assert card["state"] == snapshots[card["id"]]["headline"]["state_label"]
        assert len(card["facts"]) == 2
        assert card["href"] == f"/macro_{card['id']}.html"
        assert card["asof"] == snapshots[card["id"]]["generation"]["calculation_as_of"]


@pytest.mark.parametrize("wid", IDS)
@pytest.mark.parametrize("state", ("SOURCE_FAILED", "STALE_SOURCE", "NOT_YET_RELEASED", "RIGHTS_BLOCKED"))
def test_failed_or_stale_source_never_reuses_known_state_as_success(tmp_path, wid, state):
    snapshots = _snapshots()
    snapshots[wid]["availability"]["state"] = state
    cards = _read(tmp_path, snapshots)
    bad = next(c for c in cards if c["id"] == wid)
    assert bad["state"]["en"] == "Read unavailable"
    assert bad["facts"] == []
    assert bad["tone"] == "unavailable"
    assert bad["note"]["en"]
    assert all(c["facts"] for c in cards if c["id"] != wid)


def test_claimed_current_with_failed_required_leg_is_not_success(tmp_path):
    snapshots = _snapshots()
    snapshots[IDS[0]]["availability"]["required"][0]["freshness"] = "SOURCE_FAILED"
    cards = _read(tmp_path, snapshots)
    assert cards[0]["state"]["en"] == "Read unavailable"
    assert cards[0]["facts"] == []


def test_same_cut_comparison_is_not_marketed_as_a_monthly_change(tmp_path):
    cards = _read(tmp_path)
    assert all("month" not in c["note"]["en"].lower() for c in cards)
    assert all("since" not in c["note"]["en"].lower() for c in cards)


@pytest.mark.parametrize("wid", IDS)
def test_tampered_body_is_refused_per_card_without_killing_the_overview(tmp_path, wid):
    _publish(tmp_path, _snapshots())
    path = tmp_path / f"workspaces/{wid}/US/latest.json"
    data = json.loads(path.read_text())
    data["headline"]["state_label"]["en"] = "Fake cheerful state"
    path.write_text(json.dumps(data))
    cards = _module().build_economic_backdrop(tmp_path, page_built_at=BUILT)
    assert next(c for c in cards if c["id"] == wid)["state"]["en"] == "Read unavailable"
    assert all(c["facts"] for c in cards if c["id"] != wid)


def test_missing_manifest_keeps_three_useful_investigation_links(tmp_path):
    cards = _module().build_economic_backdrop(tmp_path, page_built_at=BUILT)
    assert len(cards) == 3
    assert all(c["tone"] == "unavailable" and c["facts"] == [] for c in cards)
    assert all(c["href"].startswith("/macro_") and c["link"]["en"] for c in cards)


def test_no_cpi_projection_can_enter_the_released_inflation_facts(tmp_path):
    cards = _read(tmp_path)
    inflation_card = cards[1]
    assert all(f["metric_id"] in ("headline_cpi_yoy_pct", "core_cpi_yoy_pct") for f in inflation_card["facts"])
    assert all(f["period"] == "2026-07" for f in inflation_card["facts"])
    assert inflation_card["asof"] != "2026-07"


@pytest.mark.parametrize("value", (0.0, -0.1, None))
def test_fact_zero_negative_and_missing_values_do_not_share_a_fallback(tmp_path, value):
    snapshots = _snapshots()
    metric = next(m for m in snapshots[IDS[1]]["metrics"]["items"] if m["metric_id"] == "headline_cpi_yoy_pct")
    metric["value"] = value
    if value is None:
        metric["status"] = "ABSENT"
        metric["null_reason"] = "SOURCE_FAILED"
    card = _read(tmp_path, snapshots)[1]
    fact = next(f for f in card["facts"] if f["metric_id"] == "headline_cpi_yoy_pct")
    assert ("not provided" in fact["value"]["en"].lower()) == (value is None)
    if value is not None:
        assert "%" in fact["value"]["en"]
    if value == -0.1:
        assert "-" in fact["value"]["en"]


def test_consumer_is_pure_and_retains_owner_identity_in_receipt(tmp_path):
    snapshots = _snapshots()
    before = copy.deepcopy(snapshots)
    first = _read(tmp_path, snapshots)
    second = _module().build_economic_backdrop(tmp_path, page_built_at=BUILT)
    assert first == second and snapshots == before
    for card in first:
        assert card["source"]["digest"] == snapshots[card["id"]]["generation"]["content_sha256"]
        assert card["source"]["authority"] == snapshots[card["id"]]["authority"]["class"] == "context_only"
        assert "page build" in card["receipt"]["en"].lower()


def test_success_keeps_one_quiet_clock_without_a_redundant_status_caption(tmp_path):
    cards = _read(tmp_path)
    assert all(c["availability"] is None for c in cards)
    assert all(c["source"]["availability_state"] in ("CURRENT", "LATE_WITHIN_TOLERANCE") for c in cards)


def test_unknown_calculation_cut_does_not_become_today(tmp_path):
    snapshots = _snapshots()
    snapshots[IDS[0]]["generation"]["calculation_as_of"] = None
    cards = _read(tmp_path, snapshots)
    assert cards[0]["tone"] == "unavailable" and cards[0]["asof"] is None
    assert cards[0]["facts"] == []


def test_production_partial_preserves_content_and_escapes_owner_text(tmp_path):
    from jinja2 import Environment, FileSystemLoader, StrictUndefined
    from html import unescape
    root = Path(__file__).resolve().parents[1]
    partial = root / "templates/_macro_economic_backdrop.html.j2"
    assert partial.exists(), "Production economic-backdrop partial is not installed"
    cards = _read(tmp_path)
    cards[0]["state"]["en"] = '<script>alert("not executable")</script>'
    env = Environment(loader=FileSystemLoader(root / "templates"), autoescape=True, undefined=StrictUndefined)
    html = env.from_string('{% import "_macro_economic_backdrop.html.j2" as row %}{{ row.economic_backdrop(cards) }}').render(cards=cards)
    assert html.count('class="panel ebd-card ') == 3
    assert "<script>" not in html
    assert '<script>alert("not executable")</script>' in unescape(html)
    assert html.count('class="ebd-go"') == 3
    assert "onclick=" not in html and "title=" not in html



@pytest.mark.parametrize("wid", IDS)
def test_duplicate_metric_identity_never_silently_selects_a_fact(tmp_path, wid):
    snapshots = _snapshots()
    selected = {"growth_real_economy": "gdpnow_growth", "inflation_system": "headline_cpi_yoy_pct", "financial_conditions": "real_10y"}
    original = next(m for m in snapshots[wid]["metrics"]["items"] if m["metric_id"] == selected[wid])
    duplicate = copy.deepcopy(original)
    duplicate["value"] = 0.0
    snapshots[wid]["metrics"]["items"].append(duplicate)
    cards = _read(tmp_path, snapshots)
    disputed = next(c for c in cards if c["id"] == wid)
    assert disputed["tone"] == "unavailable"
    assert disputed["facts"] == []
    assert all(c["facts"] for c in cards if c["id"] != wid)
