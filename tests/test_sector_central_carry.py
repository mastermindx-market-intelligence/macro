"""Carried blocks: existing producer artifacts re-expressed for the Sector generation.

REAL    every input is a committed producer artifact under ``site/`` (session
        2026-11-06; some lane 7 artifacts carry their own older/newer as-of, which the
        blocks report verbatim). The code under test is the NEW carry module.
FIXTURE only where stated (absent / malformed / non-finite source, oversize).
"""
from __future__ import annotations

import json
from pathlib import Path

from engine.sector_native_view import project_sector_view, typed_blocks_of
from lib import sector_central_carry as carry
from lib import sector_generation_contract as contract
from tests.test_sector_population import PUBLISHED, _real, _real_bundle

REPO = Path(__file__).resolve().parents[1]
SITE = REPO / "site"


def _central():
    return json.loads(_real("sectordata/sector_central.json"))


def _roster():
    return json.loads((REPO / "data/baskets/membership.json").read_text())


def test_real_artifacts_yield_every_producible_block():
    built = carry.build_carry(SITE, _central(), _roster())
    assert set(built) == {"sector_central_r1", "display_order", "etf_flows", "confluence",
                          "bottoming_watch", "theme_table", "member_industry",
                          "member_sub_industry", "removed_members"}
    # without the owner's roster no removal block is carried (never guessed)
    assert "removed_members" not in carry.build_carry(SITE, _central())
    assert "hazard_qualification" not in built  # owner not on this base; never copied


def test_r1_states_its_denominators_and_matches_the_measured_census():
    central = _central()
    r1 = carry.build_carry(SITE, central)["sector_central_r1"]
    assert r1["denominators"] == {"rising_share_of_priced": "n_priced_1M",
                                  "priced_share_of_tiles": "n_tiles"}
    by_id = {row["id"]: row for row in r1["sectors"]}
    assert set(by_id) == {s["id"] for s in central["sectors"]}
    for sector in central["sectors"]:
        heat, row = sector["heat"], by_id[sector["id"]]
        assert (row["n_tiles"], row["n_priced_1M"], row["rising_1M"]) == (
            heat["n_tiles"], heat["n_priced_1M"], heat["adv"])
        assert row["missing_1M"] == heat["n_tiles"] - heat["n_priced_1M"]
        assert row["rising_share_of_priced"] == round(heat["adv"] / heat["n_priced_1M"], 4)


def test_display_order_is_the_producers_own_published_order():
    central = _central()
    order = carry.build_carry(SITE, central)["display_order"]
    assert order["basis"] == "conviction" and order["ordinal"] == "list_position_zero_based"
    assert order["sectors"] == [s["id"] for s in central["sectors"]]
    assert order["baskets"] == [b["id"] for b in central["baskets"]]


def test_lane7_blocks_carry_their_own_source_and_as_of():
    built = carry.build_carry(SITE, _central())
    assert set(built["confluence"]) == {"sp500", "nasdaq", "russell", "china"}
    for key, relative in carry.CONFLUENCE_UNIVERSES:
        block = built["confluence"][key]
        document = json.loads((SITE / relative).read_bytes())
        assert block["source"] == relative and block["as_of"] == document.get("as_of")
        assert block["entry_now"] == document["entry_now"]
    flow = json.loads((SITE / "flow_desk.json").read_text())
    assert built["etf_flows"]["source"] == "flow_desk.json#etf_tile"
    assert built["etf_flows"]["as_of"] == flow["etf_tile"]["asof"]  # may be stale: disclosed
    baskets = json.loads(_real("basketdata/baskets.json"))["theme_intel"]
    assert built["bottoming_watch"]["bottoming_watch"] == baskets["act_now"]["bottoming_watch"]
    assert built["bottoming_watch"]["as_of"] == baskets["as_of"]
    themes = json.loads(_real("basketdata/si_handoff.json"))["theme_context"]
    assert built["theme_table"]["themes"] == themes["themes"]
    for name in ("confluence", "etf_flows", "bottoming_watch", "theme_table", "display_order",
                 "sector_central_r1"):
        assert len(json.dumps(built[name]).encode()) <= carry.MAX_BLOCK_BYTES


def test_industry_and_sub_industry_are_separate_current_basis_taxonomies():
    built = carry.build_carry(SITE, _central(), _roster())
    gics, sub = built["member_industry"], built["member_sub_industry"]
    for block in (gics, sub):
        assert block["point_in_time"] is False
    # GICS industry: stage screener, current, 617 of the 698 basket symbols.
    assert (gics["source"], gics["basis"], gics["taxonomy"]) == (
        "stagedata/screener.json", "current_gics_industry_not_point_in_time", "gics_industry")
    assert gics["as_of"] == "2026-11-09" and len(gics["symbols"]) == 617
    assert all(isinstance(v, str) for v in gics["symbols"].values())
    # S&P 500 sub-industry: its own source/as-of; 430 symbols (424 are basket members).
    assert (sub["source"], sub["basis"]) == (carry.INDUSTRY_SOURCE, carry.INDUSTRY_BASIS)
    assert sub["as_of"] == "2026-11-06" and len(sub["symbols"]) == 430
    assert sub["symbols"]["APP"] == "software-application"
    assert sub["subsectors"]["software-application"]["label"] == "Software - Application"
    assert gics["symbols"] != sub["symbols"]  # never merged


def test_removed_members_come_from_the_owner_roster_with_dates():
    removed = carry.build_carry(SITE, _central(), _roster())["removed_members"]
    assert removed["source"] == "data/baskets/membership.json" and len(removed["removed"]) == 26
    pairs = {(r["group_id"], r["symbol"]): r["removed_on"] for r in removed["removed"]}
    assert pairs[("silver_miners", "GATO")] == "2025-01-16"
    assert pairs[("silver_miners", "MAG")] == "2025-09-04"


def test_fixture_absent_malformed_or_nonfinite_sources_yield_no_block(tmp_path):
    """FIXTURE: the carry never repairs or invents."""
    (tmp_path / "marketdata").mkdir()
    (tmp_path / "flow_desk.json").write_text('{"etf_tile":{"asof":NaN}}')
    (tmp_path / "marketdata/subsector_confluence.json").write_text("[]")
    built = carry.build_carry(tmp_path, {"as_of": "2026-11-06", "sectors": []})
    assert built == {}


def test_generation_projects_carried_blocks_available_and_hazard_unavailable(tmp_path):
    raw, identity = _real_bundle(tmp=tmp_path)
    inputs, receipt = contract._capture_view(
        member_bytes=raw, input_identity=identity, generation_id="carry",
        published_at=PUBLISHED.isoformat(), now=PUBLISHED)
    data = project_sector_view(inputs, receipt, audience="entitled")["data"]
    blocks = typed_blocks_of(data)
    assert {n: b["status"] for n, b in blocks.items()} == {
        "r1_rising_priced_share": "available", "r2_display_order": "available",
        "r2_hazard_qualification": "unavailable", "etf_flows": "available",
        "confluence": "available", "bottoming_watch": "available", "theme_table": "available"}
    assert blocks["r2_hazard_qualification"]["reason"] == "not_produced"
    preview = typed_blocks_of(project_sector_view(inputs, receipt, audience="preview")["data"])
    assert preview["r1_rising_priced_share"]["status"] == "available"
    assert preview["confluence"]["reason"] == "audience_not_entitled"


def test_builder_wires_the_carry_before_publication():
    source = (REPO / "scripts/build_sector_central.py").read_text()
    assert source.index("build_carry(site, data, _membership())") < source.index(
        'data["publication"] = {')
