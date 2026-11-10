"""Carried blocks: existing producer artifacts re-expressed for the Sector generation.

REAL    every input is a committed producer artifact under ``site/`` (session
        2026-11-06; some lane 7 artifacts carry their own older/newer as-of, which the
        blocks report verbatim). The code under test is the NEW carry module.
FIXTURE only where stated (absent / malformed / non-finite source, oversize).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

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


def _flows():
    """REAL: the committed ETF-flow producer, run over the committed data/flows parquet."""
    from collectors.sponsors import sector_flow_periods
    flows = sector_flow_periods()
    if flows is None:
        pytest.skip("no committed data/flows history in this checkout")
    return flows


def test_real_artifacts_yield_every_producible_block():
    built = carry.build_carry(SITE, _central(), _roster(), _flows())
    assert set(built) == {"sector_central_r1", "display_order", "etf_flows", "confluence",
                          "bottoming_watch", "theme_table", "member_industry",
                          "member_sub_industry", "removed_members", "roster_baskets"}
    # without the owner's roster / flow history those blocks are not carried (never guessed)
    bare = carry.build_carry(SITE, _central())
    assert "removed_members" not in bare and "etf_flows" not in bare
    assert "roster_baskets" not in bare
    assert "hazard_qualification" not in built  # owner not on this base; never copied
    # every non-confluence block carries a string as-of; confluence is dated per universe
    for name, block in built.items():
        if name not in ("confluence", "member_industry", "member_sub_industry"):
            assert isinstance(block["as_of"], str) and block["as_of"], name
    assert all(isinstance(u["as_of"], str) and u["as_of"] for u in built["confluence"].values())


def test_etf_flow_windows_equal_the_producers_flow_periods():
    """R3-N3: the carried window table restates the producer's constant - a producer
    change of day count under the same labels must fail here, not mislabel silently.
    The producer constant is imported in this test only (the carry module takes the
    producer's output as data and must not import the producer)."""
    from collectors.sponsors import FLOW_PERIODS
    assert carry.ETF_FLOW_WINDOWS == FLOW_PERIODS  # labels AND day counts, order included


def test_etf_flows_carries_the_lane7_windows_from_the_committed_producer():
    """Lane 7 needs 11 SPDRs x 1/3/5/10/21-day delta(shares) x NAV with as-of and depth."""
    flows = _flows()
    block = carry.build_carry(SITE, _central(), _roster(), flows)["etf_flows"]
    assert block["source"] == "collectors.sponsors.sector_flow_periods"
    assert block["unit"] == "usd_mn" and block["as_of"] == flows["asof"]
    assert block["depth"] == flows["depth"]
    assert [(w["label"], w["trading_days"]) for w in block["windows"]] == [
        ("1D", 1), ("3D", 3), ("1W", 5), ("2W", 10), ("1M", 21)]
    assert all(w["full_window"] == (block["depth"] >= w["trading_days"]) for w in block["windows"])
    assert len(block["funds"]) == 11
    assert {f["ticker"] for f in block["funds"]} == {
        "XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY"}
    by_ticker = {r["ticker"]: r["vals"] for r in flows["rows"]}
    for fund in block["funds"]:
        assert fund["flow_mn"] == by_ticker[fund["ticker"]]  # copied, never recomputed
    assert block["net_flow_mn"] == {k: flows["net"][k] for k in flows["labels"]}
    # the old tile (1d/5d/21d only) is NOT what lane 7's window contract needs
    tile = json.loads((SITE / "flow_desk.json").read_text())["etf_tile"]
    assert set(tile["funds"][0]) == {"ticker", "flow_1d", "flow_5d", "flow_21d"}


def test_fixture_etf_flows_rejects_a_producer_output_of_the_wrong_shape():
    """FIXTURE: a partial window set or undated output is not carried."""
    good = {"asof": "2026-11-05", "depth": 3, "labels": ["1D", "3D", "1W", "2W", "1M"],
            "rows": [{"ticker": "XLB", "vals": dict.fromkeys(["1D", "3D", "1W", "2W", "1M"], 1.0)}],
            "net": dict.fromkeys(["1D", "3D", "1W", "2W", "1M"], 1.0)}
    assert carry.etf_flows(good)["windows"][3] == {
        "label": "2W", "trading_days": 10, "full_window": False}  # depth 3 < 10
    for bad in (None, {**good, "labels": ["1D", "5D"]}, {**good, "asof": None},
                {**good, "rows": []}, {**good, "depth": True},
                {**good, "rows": [{"ticker": "XLB", "vals": {"1D": 1.0}}]}):
        assert carry.etf_flows(bad) is None


def test_fixture_a_malformed_etf_flows_row_drops_only_that_block():
    """FIXTURE: R3-N4 - a non-mapping fund row drops ONLY etf_flows; an exception here
    would strip every carried block in the builder's fail-soft handler."""
    labels = [lbl for lbl, _ in carry.ETF_FLOW_WINDOWS]
    bad = {"asof": "2026-11-05", "depth": 79, "labels": labels,
           "rows": ["XLB"], "net": dict.fromkeys(labels, 1.0)}
    assert carry.etf_flows(bad) is None  # refused, never an AttributeError
    built = carry.build_carry(SITE, _central(), _roster(), bad)
    assert "etf_flows" not in built
    for name in ("sector_central_r1", "display_order", "confluence", "bottoming_watch",
                 "theme_table", "member_industry", "member_sub_industry",
                 "removed_members", "roster_baskets"):
        assert name in built, name


def test_undated_block_is_dropped_not_carried_with_a_null_date(tmp_path):
    """FIXTURE: R2-N4 - a source with no date is not carried as `as_of: null`."""
    central = {"as_of": None, "sectors": [{"id": "a", "ticker": "A", "heat": {
        "n_tiles": 2, "n_priced_1M": 2, "adv": 1}}], "meta": {"board_order": "conviction"}}
    built = carry.build_carry(SITE, central)
    assert "sector_central_r1" not in built and "display_order" not in built


def test_removed_members_use_the_owner_effective_session_not_the_central_date():
    """FIXTURE over real roster: R2-N5 - same clock as `configured_members`."""
    assert carry.owner_effective_as_of(SITE) == "2026-11-06"
    roster = {"version": "t", "baskets": {"g": {"members": [
        {"ticker": "EARLY", "removed": "2026-11-05"}, {"ticker": "ONDAY", "removed": "2026-11-06"},
        {"ticker": "LATER", "removed": "2026-11-09"}]}}}
    # an owner session of 11-06 removes EARLY and ONDAY, not LATER - whatever central says
    assert [r["symbol"] for r in carry.removed_members(roster, "2026-11-06")["removed"]] == [
        "EARLY", "ONDAY"]
    assert [r["symbol"] for r in carry.removed_members(roster, "2026-11-09")["removed"]] == [
        "EARLY", "LATER", "ONDAY"]
    assert carry.removed_members(roster, None) is None


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
    built = carry.build_carry(SITE, _central(), _roster(), _flows())
    assert set(built["confluence"]) == {"sp500", "nasdaq", "russell", "china"}
    for key, relative in carry.CONFLUENCE_UNIVERSES:
        block = built["confluence"][key]
        document = json.loads((SITE / relative).read_bytes())
        assert block["source"] == relative and block["entry_now"] == document["entry_now"]
        # dated per universe: the file's own as_of, else its generated_utc (named)
        assert block["as_of"] == document[block["as_of_field"]]
        assert block["as_of_field"] in ("as_of", "generated_utc")
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


def test_roster_baskets_names_every_basket_the_capture_must_account_for():
    """R3-S1: the carried owner roster the completeness check runs against."""
    roster = carry.build_carry(SITE, _central(), _roster())["roster_baskets"]
    assert roster["source"] == "data/baskets/membership.json"
    assert roster["as_of"] == carry.owner_effective_as_of(SITE) == "2026-11-06"
    baskets = json.loads(_real("basketdata/baskets.json"))
    live = {g["id"] for g in baskets["baskets"]}
    refused = {r["basket_id"] for r in baskets["observation_refusals"]}
    # on the real bytes every roster basket is live or refused (nothing vanishes), and
    # each basket's current members equal the owner's own captured configured list
    assert set(roster["baskets"]) == live | refused
    assert sum(len(v) for v in roster["baskets"].values()) == 1020
    for g in baskets["baskets"]:
        assert sorted(roster["baskets"][g["id"]]) == sorted(
            g["observation"]["configured_members"]), g["id"]
    assert len(json.dumps(roster).encode()) <= carry.MAX_BLOCK_BYTES
    # no roster document, or no owner session to cut it at: no block (null downstream)
    assert carry.roster_baskets(None, "2026-11-06") is None
    assert carry.roster_baskets(_roster(), None) is None


def test_roster_baskets_uses_the_owner_current_rule_at_the_effective_session():
    """FIXTURE: current = added <= session < removed - the configured_members clock."""
    roster = {"version": "t", "baskets": {"g": {"members": [
        {"ticker": "IN", "added": "2026-01-06"},
        {"ticker": "FUT", "added": "2026-11-07"},
        {"ticker": "OUT", "added": "2026-01-06", "removed": "2026-11-05"},
        {"ticker": "ONDAY", "added": "2026-01-06", "removed": "2026-11-06"},
        {"ticker": "LATER", "added": "2026-01-06", "removed": "2026-11-09"},
        {"ticker": "DUP", "added": "2026-01-06"}, {"ticker": "DUP", "added": "2026-01-06"}]}}}
    # a repeated listing collapses to one (the owner's own first-listing-wins rule)
    assert carry.roster_baskets(roster, "2026-11-06")["baskets"] == {"g": ["IN", "LATER", "DUP"]}


def test_fixture_absent_malformed_or_nonfinite_sources_yield_no_block(tmp_path):
    """FIXTURE: the carry never repairs or invents."""
    (tmp_path / "marketdata").mkdir()
    (tmp_path / "flow_desk.json").write_text('{"etf_tile":{"asof":NaN}}')
    (tmp_path / "marketdata/subsector_confluence.json").write_text("[]")
    built = carry.build_carry(tmp_path, {"as_of": "2026-11-06", "sectors": []},
                              flows={"asof": float("nan")})
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
    assert source.index("build_carry(site, data, _membership(), sector_flow_periods())") < source.index(
        'data["publication"] = {')
