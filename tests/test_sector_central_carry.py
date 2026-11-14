"""Carried blocks: existing producer artifacts re-expressed for the Sector generation.

REAL    every input is a committed producer artifact under ``site/`` (session
        2026-11-06; some lane 7 artifacts carry their own older/newer as-of, which the
        blocks report verbatim). The code under test is the NEW carry module.
FIXTURE only where stated (absent / malformed / non-finite source, oversize).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from engine.sector_native_view import project_sector_view, typed_blocks_of
from lib import sector_central_carry as carry
from lib import sector_generation_contract as contract
from tests.test_sector_population import PUBLISHED, _real, _real_bundle, _real_carry_blocks

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
    built = _real_carry_blocks()
    assert set(built) == {"sector_central_r1", "display_order", "etf_flows", "confluence",
                          "bottoming_watch", "theme_table", "member_industry",
                          "member_sub_industry", "removed_members", "roster_baskets",
                          "membership_first_known", "membership_snapshots",
                          "confluence_universe_sp500", "confluence_universe_nasdaq",
                          "confluence_universe_russell", "confluence_universe_baskets",
                          "theme_rows"}
    # without the owner's roster / flow history those blocks are not carried (never guessed)
    bare = carry.build_carry(SITE, _central())
    assert "removed_members" not in bare and "etf_flows" not in bare
    assert "roster_baskets" not in bare
    assert "membership_first_known" not in bare and "membership_snapshots" not in bare
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
    block = _real_carry_blocks()["etf_flows"]  # same real inputs the cache built on
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
                 "removed_members", "roster_baskets", "membership_first_known",
                 "membership_snapshots"):
        assert name in built, name


def test_undated_block_is_dropped_not_carried_with_a_null_date(tmp_path):
    """FIXTURE: R2-N4 - a source with no date is not carried as `as_of: null`."""
    central = {"as_of": None, "sectors": [{"id": "a", "ticker": "A", "heat": {
        "n_tiles": 2, "n_priced_1M": 2, "adv": 1}}], "meta": {"board_order": "conviction"}}
    built = carry.build_carry(SITE, central)
    assert "sector_central_r1" not in built and "display_order" not in built


def test_fixture_undated_industry_sources_are_dropped_not_carried_null(tmp_path):
    """FIXTURE: R3-N5 - the two current-basis taxonomy blocks join the dated-block rule."""
    (tmp_path / "stagedata").mkdir()
    (tmp_path / "marketdata").mkdir()
    (tmp_path / "basketdata").mkdir()
    screener = {"rows": [{"ticker": "X", "industry": "Things"}]}
    sub = {"subsectors": [{"key": "k", "label": "K", "members": [{"ticker": "X"}]}]}
    baskets = {"baskets": [{"id": "b", "members": [{"symbol": "X", "added": "2024-01-01"}],
                            "observation": {"effective_as_of": "2026-11-06"}}]}
    (tmp_path / "stagedata/screener.json").write_text(json.dumps(screener))
    (tmp_path / "marketdata/subsector_confluence.json").write_text(json.dumps(sub))
    (tmp_path / "basketdata/baskets.json").write_text(json.dumps(baskets))
    built = carry.build_carry(tmp_path, {"as_of": "2026-11-06", "sectors": []})
    assert "member_industry" not in built and "member_sub_industry" not in built
    # dated sources ARE carried: the same rule as every other dated block
    (tmp_path / "stagedata/screener.json").write_text(json.dumps({**screener, "asof": "2026-11-09"}))
    (tmp_path / "marketdata/subsector_confluence.json").write_text(
        json.dumps({**sub, "as_of": "2026-11-06"}))
    built = carry.build_carry(tmp_path, {"as_of": "2026-11-06", "sectors": []})
    assert built["member_industry"]["as_of"] == "2026-11-09"
    assert built["member_sub_industry"]["as_of"] == "2026-11-06"


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
    built = _real_carry_blocks()
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
    built = _real_carry_blocks()
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
    removed = _real_carry_blocks()["removed_members"]
    assert removed["source"] == "data/baskets/membership.json" and len(removed["removed"]) == 26
    pairs = {(r["group_id"], r["symbol"]): r["removed_on"] for r in removed["removed"]}
    assert pairs[("silver_miners", "GATO")] == "2025-01-16"
    assert pairs[("silver_miners", "MAG")] == "2025-09-04"


def test_roster_baskets_names_every_basket_the_capture_must_account_for():
    """R3-S1: the carried owner roster the completeness check runs against."""
    roster = _real_carry_blocks()["roster_baskets"]
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


def test_r4_n1_a_non_mapping_list_form_roster_entry_is_skipped_never_raised():
    """FIXTURE: R4-N1 - a list-form roster with a non-mapping entry must SKIP that
    entry in BOTH loops. Before the guard this raised AttributeError inside
    build_carry, whose fail-soft handler stripped EVERY carried block; the test
    fails on revert because the exception escapes (no block set at all)."""
    roster = {"version": "t", "baskets": [
        "garbage", {"id": "g", "members": [{"ticker": "A", "added": "2024-01-01"}]}]}
    built = carry.build_carry(SITE, _central(), roster, _flows())
    assert built["roster_baskets"]["baskets"] == {"g": ["A"]}  # entry skipped, not fatal
    assert built["removed_members"]["removed"] == []
    # the other nine carried blocks survive what used to strip all of them
    assert set(built) == {"sector_central_r1", "display_order", "etf_flows", "confluence",
                          "bottoming_watch", "theme_table", "member_industry",
                          "member_sub_industry", "removed_members", "roster_baskets",
                          "membership_first_known", "membership_snapshots",
                          "confluence_universe_sp500", "confluence_universe_nasdaq",
                          "confluence_universe_russell", "confluence_universe_baskets",
                          "theme_rows"}
    # dict-form rosters are unchanged, and a member (not group) non-mapping entry is skipped
    assert carry.removed_members({"baskets": {"g": {"members": ["x"]}}}, "2026-11-06")[
        "removed"] == []


def test_r4_n2_the_roster_clock_is_the_owners_clock():
    """FIXTURE: R4-N2 - the owner's own rule (lib.closes_panel.population_observation):
    the member key is ticker OR symbol and dates compare as pd.Timestamp, so an ISO
    stamp like 2026-11-06T00:00:00 is INCLUDED; an unparseable date means NO roster
    block (completeness null), never a silently included member. Each case diverged
    from the owner before the fix (string comparison / ticker-key-only)."""
    as_of = "2026-11-06"
    iso = carry.roster_baskets({"version": "t", "baskets": {"g": {"members": [
        {"ticker": "A", "added": "2026-11-06T00:00:00"}]}}}, as_of)
    assert iso["baskets"] == {"g": ["A"]}  # string compare said "not yet a member"
    sym = carry.roster_baskets({"version": "t", "baskets": {"g": {"members": [
        {"symbol": "A", "added": "2026-01-06"}]}}}, as_of)
    assert sym["baskets"] == {"g": ["A"]}  # the owner accepts the symbol key too
    # removed with a time component: 2026-11-05T23:59:59 is still before the session
    out_by = carry.roster_baskets({"version": "t", "baskets": {"g": {"members": [
        {"ticker": "A", "removed": "2026-11-05T23:59:59"},
        {"ticker": "B", "removed": "2026-11-06T00:00:00"}]}}}, as_of)
    assert out_by["baskets"] == {"g": []}  # both removed at/before the session
    # an unparseable roster date: the WHOLE block is absent (never a guessed cut)
    for bad in ({"added": "zzz"}, {"removed": "not-a-date"}, {"added": {"x": 1}}):
        assert carry.roster_baskets({"version": "t", "baskets": {"g": {"members": [
            {"ticker": "A", **bad}]}}}, as_of) is None, bad
    # a non-string session or empty session: no block either
    assert carry.roster_baskets(_roster(), None) is None
    assert carry.roster_baskets(_roster(), "") is None


def test_r4_n2_the_real_roster_cut_still_agrees_with_the_owner_on_real_bytes():
    """REAL: the mirrored clock produces the SAME cut the owner captured - every
    live/refused basket's configured_members equals the carried current list."""
    roster = _real_carry_blocks()["roster_baskets"]
    baskets = json.loads(_real("basketdata/baskets.json"))
    live = {g["id"]: g["observation"]["configured_members"] for g in baskets["baskets"]}
    refused = {r["basket_id"]: r["observation"]["configured_members"]
               for r in baskets["observation_refusals"]}
    assert set(roster["baskets"]) == set(live) | set(refused)
    for gid, members in {**live, **refused}.items():
        assert sorted(roster["baskets"][gid]) == sorted(members), gid


def _pit_store(root, monkeypatch, snapshots):
    """FIXTURE PIT store built through the OWNER's own writer: write each dated
    membership document to a tmp ``membership.json``, point the owner's suite paths
    at the tmp store, and stamp with ``append_snapshot(lane="nightly")`` - the one
    lane allowed to advance the US suite. ``snapshots`` is {date: roster_doc}."""
    from engine import basket_membership_pit as pit
    root.mkdir(parents=True, exist_ok=True)
    roster_path = root / "membership.json"
    hist_path = root / "membership_history.parquet"
    monkeypatch.setattr(pit, "membership_path", lambda suite: roster_path)
    monkeypatch.setattr(pit, "history_path", lambda suite: hist_path)
    for date, doc in sorted(snapshots.items()):
        roster_path.write_text(json.dumps(doc))
        result = pit.append_snapshot(pit.SUITE_US, asof=date, lane="nightly")
        assert result["written"] or result["reason"] == "membership unchanged", result
    return pit


def _roster_doc(baskets):
    return {"version": "t", "baskets": baskets}


def test_pit_first_known_is_the_earliest_stored_snapshot_never_the_added_date(tmp_path, monkeypatch):
    """FIXTURE: Part B 1 - first_known is the earliest stored snapshot CONTAINING the
    pair (a lower bound; the store begins at its own first snapshot), never the
    roster's back-dated ``added`` date; a pair no snapshot contains is None."""
    early = {"g": {"members": [{"ticker": "OLD", "added": "2023-05-09"},
                               {"ticker": "GONE", "added": "2023-05-09"}]}}
    later = {"g": {"members": [{"ticker": "OLD", "added": "2023-05-09"},
                               {"ticker": "NEW", "added": "2023-05-09"},
                               {"ticker": "KEEP", "added": "2023-05-09"}]}}
    _pit_store(tmp_path / "store", monkeypatch, {"2026-08-13": _roster_doc(early),
                                                 "2026-08-18": _roster_doc(later)})
    roster = _roster_doc(later)  # the current roster names OLD, NEW, KEEP (not GONE)
    cut = carry.roster_baskets(roster, "2026-08-18")
    block = carry.membership_first_known(roster, "2026-08-18", cut["baskets"])
    assert block["status"] == "available"
    assert block["basis"] == "lower_bound_from_stored_snapshots"
    assert (block["store_first"], block["store_last"]) == ("2026-08-13", "2026-08-18")
    assert block["first_known"] == {"g": {"OLD": "2026-08-13", "NEW": "2026-08-18",
                                          "KEEP": "2026-08-18"}}
    # NEW's roster `added` is 2023-05-09 - the store answer never equals the
    # back-dated date, and no value predates the store's first snapshot
    assert block["first_known"]["g"]["NEW"] != "2023-05-09"
    assert all(day >= block["store_first"] for day in block["first_known"]["g"].values())
    # a member of the roster cut that NO stored snapshot contains: null + the reason
    roster2 = _roster_doc({"g": {"members": [{"ticker": "OLD", "added": "2023-05-09"},
                                             {"ticker": "GHOST", "added": "2024-01-01"}]}})
    cut2 = carry.roster_baskets(roster2, "2026-08-18")
    ghost = carry.membership_first_known(roster2, "2026-08-18", cut2["baskets"])
    assert ghost["first_known"]["g"]["GHOST"] is None
    assert ghost["absent_pair_reason"] == "no_stored_snapshot"


def test_pit_first_known_fail_closed_cases(tmp_path, monkeypatch):
    """FIXTURE: Part B 1 fail-closed - unreadable history, empty store, unknown
    basket, and a store whose snapshots are all LATER than the session."""
    # corrupt bytes: the store exists but cannot be read - block-level unavailable
    from engine import basket_membership_pit as pit
    roster = _roster_doc({"g": {"members": [{"ticker": "A", "added": "2024-01-01"}]}})
    corrupt = tmp_path / "corrupt"
    corrupt.mkdir()
    (corrupt / "membership.json").write_text(json.dumps(roster))
    (corrupt / "membership_history.parquet").write_bytes(b"not parquet at all")
    monkeypatch.setattr(pit, "membership_path", lambda suite: corrupt / "membership.json")
    monkeypatch.setattr(pit, "history_path", lambda suite: corrupt / "membership_history.parquet")
    cut = carry.roster_baskets(roster, "2026-11-06")
    bad = carry.membership_first_known(roster, "2026-11-06", cut["baskets"])
    assert bad["status"] == "unavailable" and bad["reason"] == "membership_unreadable"
    snap = carry.membership_snapshots(roster, "2026-11-06", cut["baskets"])
    assert snap["groups"]["g"] == {"status": "unavailable", "reason": "membership_unreadable"}
    # an empty store (no snapshots ever): no pair can be proven
    _pit_store(tmp_path / "empty", monkeypatch, {})
    (tmp_path / "empty" / "membership.json").write_text(json.dumps(roster))
    assert carry.membership_first_known(roster, "2026-11-06", cut["baskets"]) == {
        "source": carry.PIT_STORE_SOURCE, "as_of": "2026-11-06",
        "status": "unavailable", "reason": "no_stored_snapshots",
        "basis": carry.FIRST_KNOWN_BASIS}
    # a store whose only snapshot is AFTER the session: no basket-scoped observation
    # at the session, carried as unavailable with the owner's basis string
    _pit_store(tmp_path / "ahead", monkeypatch, {"2026-10-14": _roster_doc(
        {"g": {"members": [{"ticker": "A", "added": "2024-01-01"}]}})})
    ahead = carry.membership_first_known(roster, "2026-08-01", cut["baskets"])
    assert ahead["status"] == "unavailable"
    assert ahead["reason"] == "no_stored_snapshots_at_or_before_as_of"
    snap_ahead = carry.membership_snapshots(roster, "2026-08-01", cut["baskets"])
    assert snap_ahead["groups"]["g"]["status"] == "unavailable"
    # a basket the store has never heard of (roster names it, store does not)
    unknown = _roster_doc({"h": {"members": [{"ticker": "B", "added": "2024-01-01"}]}})
    cut_h = carry.roster_baskets(unknown, "2026-10-14")
    snap_h = carry.membership_snapshots(unknown, "2026-10-14", cut_h["baskets"])
    assert snap_h["groups"]["h"] == {"status": "unavailable", "reason": "unknown_basket"}
    fk_h = carry.membership_first_known(unknown, "2026-10-14", cut_h["baskets"])
    assert fk_h["first_known"]["h"]["B"] is None
    # no roster cut at all: no PIT blocks (the facts are scoped to roster pairs)
    assert carry.membership_first_known(roster, "2026-11-06", None) is None
    assert carry.membership_first_known(roster, None, cut["baskets"]) is None


def test_pit_snapshots_carry_the_stored_snapshot_and_roster_equality(tmp_path, monkeypatch):
    """FIXTURE: Part B 2 - per basket the stored snapshot at/before the session with
    the owner's own sha (as stamped, never recomputed) and member count, plus ONE
    boolean vs the carried roster's current members; no member list is carried."""
    day1 = {"g": {"members": [{"ticker": "A", "added": "2024-01-01"},
                              {"ticker": "B", "added": "2024-01-01"}]}}
    # B left: the owner's roster keeps the member with its removal date, exactly as
    # data/baskets/membership.json does - positive rows alone cannot prove a exit
    day2 = {"g": {"members": [{"ticker": "A", "added": "2024-01-01"},
                              {"ticker": "B", "added": "2024-01-01",
                               "removed": "2026-08-20"}]}}
    pit = _pit_store(tmp_path / "store", monkeypatch, {"2026-08-13": _roster_doc(day1),
                                                       "2026-09-04": _roster_doc(day2)})
    roster_same = _roster_doc(day2)  # current roster == stored 09-04 member set
    cut = carry.roster_baskets(roster_same, "2026-11-06")
    snap = carry.membership_snapshots(roster_same, "2026-11-06", cut["baskets"])
    entry = snap["groups"]["g"]
    assert entry["status"] == "available" and entry["snapshot_date"] == "2026-09-04"
    assert entry["member_count"] == 1 and entry["equals_current_roster"] is True
    stored = pit.read_history(pit.SUITE_US, strict=True)
    stamped = {r["members_sha"] for _, r in stored.iterrows()
               if str(r["snapshot_date"]) == "2026-09-04"}
    assert stamped == {entry["members_sha"]}  # the owner's own stamped sha, as stored
    assert "members" not in entry  # the member list is never carried twice
    # a roster that differs from the stored snapshot: equals_current_roster false
    roster_diff = _roster_doc({"g": {"members": [{"ticker": "A", "added": "2024-01-01"},
                                                 {"ticker": "C", "added": "2024-01-01"}]}})
    cut_diff = carry.roster_baskets(roster_diff, "2026-11-06")
    diff = carry.membership_snapshots(roster_diff, "2026-11-06", cut_diff["baskets"])
    assert diff["groups"]["g"]["equals_current_roster"] is False
    # no roster cut: the equality boolean is null (either side may be unavailable)
    no_cut = carry.membership_snapshots(roster_same, "2026-11-06", None)
    assert no_cut["groups"]["g"]["equals_current_roster"] is None


def test_pit_blocks_on_real_bytes_sizes_and_values():
    """REAL: the two Part B blocks on the committed artifacts and the committed PIT
    store (4 snapshots 2026-08-13/08-18/09-04/10-14) - sizes under the block cap."""
    built = _real_carry_blocks()
    fk, snap = built["membership_first_known"], built["membership_snapshots"]
    assert (len(json.dumps(fk).encode()), len(json.dumps(snap).encode())) == (23090, 10265)
    assert all(len(json.dumps(built[n]).encode()) <= carry.MAX_BLOCK_BYTES
               for n in ("membership_first_known", "membership_snapshots"))
    assert fk["store_first"] == "2026-08-13" and fk["store_last"] == "2026-10-14"
    pairs = {(g, s): d for g, bucket in fk["first_known"].items() for s, d in bucket.items()}
    assert len(pairs) == 1020 and set(pairs.values()) <= {
        "2026-08-13", "2026-08-18", "2026-09-04", "2026-10-14"}
    # every value is a stored snapshot date - never a back-dated roster `added`
    roster = json.loads((REPO / "data/baskets/membership.json").read_text())["baskets"]
    added = {(g, m["ticker"]): m.get("added") for g, b in roster.items()
             for m in b["members"]}
    backdated = {p for p, day in pairs.items() if added.get(p) and added[p] < "2026-08-13"}
    assert backdated and all(pairs[p] != added[p] for p in backdated)
    assert snap["suite"] == "baskets" and set(snap["groups"]) == set(roster)
    assert all(e["status"] == "available" and e["snapshot_date"] == "2026-10-14"
               and e["equals_current_roster"] is True
               for e in snap["groups"].values())


def test_n1_roster_baskets_mirrors_the_owners_population_observation():
    """N1: the roster cut's mirrored rule is asserted EQUAL to the owner's own
    ``population_observation`` configured list over the same member fixtures - the
    differential that proves the mirror (R4-N2), rather than restating it. The owner
    runs on an empty price panel: ``configured_members`` is panel-independent."""
    import pandas as pd
    from lib.closes_panel import population_observation
    cases = [
        [],
        [{"ticker": "AAA", "added": "2024-01-01"}, {"symbol": "BBB", "added": "2024-02-01"}],
        [{"ticker": "AAA"}, {"symbol": "AAA"}],          # first listing wins, across keys
        [{"symbol": "BBB"}, {"ticker": "BBB", "added": "2020-01-01"}],
        [{"ticker": "FUT", "added": "2026-12-01"}],       # not yet a member at the session
        [{"ticker": "GONE", "removed": "2026-01-01"}],    # already removed
        [{"ticker": "ONDAY", "added": "2026-11-06"}],     # added ON the session: in
        [{"ticker": "OUTDAY", "removed": "2026-11-06"}],  # removed ON the session: out
        [{"ticker": "ISO", "added": "2026-11-06T00:00:00"}],
        [{"ticker": "BLANK", "added": "", "removed": ""}],
        [{"ticker": 5}, {"symbol": 7}],                   # the owner str()s numeric keys
        [{"ticker": ""}, {"symbol": None}, {"ticker": "OK"}],
    ]
    for members in cases:
        owner = population_observation(
            pd.DataFrame(index=pd.DatetimeIndex([])), members, "2026-11-06")["configured_members"]
        mine = carry.roster_baskets({"version": "t", "baskets": {"g": {"members": members}}},
                                    "2026-11-06")["baskets"]["g"]
        assert mine == owner, members


def test_n2_an_over_cap_pit_block_is_a_bounded_unavailable_stub_never_a_silent_drop(
        tmp_path, monkeypatch):
    """N2: an over-cap point-in-time block must NOT vanish from the carry - the
    generation would then read ``not_produced`` and lose the fact entirely. It is
    replaced by a small stub served as unavailable/``block_too_large``, and the stub
    itself must pass the same bound."""
    roster = _roster_doc({"g": {"members": [{"ticker": "A", "added": "2024-01-01"}]}})
    _pit_store(tmp_path / "store", monkeypatch, {"2026-08-13": roster})
    cut = carry.roster_baskets(roster, "2026-11-06")
    monkeypatch.setattr(carry, "MAX_BLOCK_BYTES", 256)  # force the available blocks over
    fk = carry.membership_first_known(roster, "2026-11-06", cut["baskets"])
    snap = carry.membership_snapshots(roster, "2026-11-06", cut["baskets"])
    for block, source in ((fk, carry.PIT_STORE_SOURCE), (snap, carry.PIT_READER_SOURCE)):
        assert block is not None and block["status"] == "unavailable", source
        assert block["reason"] == "block_too_large" and block["source"] == source
        assert block["as_of"] == "2026-11-06"
        assert carry._bounded(block) is block  # the stub passes the same bound
        assert len(json.dumps(block).encode()) <= 256


def test_n5_a_pit_builder_failure_degrades_only_the_pit_facts(tmp_path, monkeypatch,
                                                              caplog):
    """N5: ANY failure of the PIT builder - here the engine module failing to import -
    makes ONLY the two point-in-time facts unavailable (``membership_unreadable``);
    every other carried block is still served. KeyboardInterrupt/SystemExit are never
    swallowed by the degradation. N2: the degradation is LOGGED with the exception
    type and message - a programming error must not ship silently under the same
    closed reason as store corruption."""
    import logging
    def boom():
        raise ImportError("engine missing")
    monkeypatch.setattr(carry, "_pit_module", boom)
    site = tmp_path / "site"
    (site / "basketdata").mkdir(parents=True)
    (site / "basketdata/baskets.json").write_text(json.dumps(
        {"baskets": [{"id": "g", "observation": {"effective_as_of": "2026-11-06"}}]}))
    membership = _roster_doc({"g": {"members": [{"ticker": "A", "added": "2024-01-01"}]}})
    with caplog.at_level(logging.WARNING, logger="lib.sector_central_carry"):
        built = carry.build_carry(site, {"as_of": "2026-11-06", "sectors": []}, membership, None)
    assert [r.getMessage() for r in caplog.records
            if r.name == "lib.sector_central_carry"] == [
        "sector_central_carry: PIT facts degraded (ImportError: engine missing)"]
    for name in ("membership_first_known", "membership_snapshots"):
        assert built[name]["status"] == "unavailable", name
        assert built[name]["reason"] == "membership_unreadable", name
        assert isinstance(built[name]["as_of"], str)  # dated: carried, not dropped
    assert built["roster_baskets"]["baskets"] == {"g": ["A"]}  # the other blocks survive
    assert built["removed_members"]["removed"] == []
    # KeyboardInterrupt is never swallowed
    def interrupt():
        raise KeyboardInterrupt
    monkeypatch.setattr(carry, "_pit_module", interrupt)
    try:
        carry.build_carry(site, {"as_of": "2026-11-06", "sectors": []}, membership, None)
    except KeyboardInterrupt:
        pass
    else:
        raise AssertionError("KeyboardInterrupt must propagate, never be degraded")


def test_n8_a_known_basket_absent_from_the_snapshot_is_unavailable_not_zero(
        tmp_path, monkeypatch):
    """N8: on the owner's LEGACY store path a KNOWN basket with no row in the resolved
    snapshot answers pit=True with zero members - which must NOT be served as
    ``available, member_count: 0`` (indistinguishable from a genuinely empty basket).
    It reads unavailable/``basket_absent_from_snapshot``, with presence decided from
    the snapshot's own basket set in the frame the builder already read - never from
    the owner's free-text note. A basket PRESENT with zero active members stays
    available with member_count 0."""
    from engine import basket_membership_pit as pit
    root = tmp_path / "legacy"
    root.mkdir()
    snaps = root / "snapshots"
    snaps.mkdir()
    day1 = {"b1": {"members": [{"ticker": "AAA", "added": "2024-01-01"},
                               {"ticker": "BBB", "added": "2024-01-01"}]},
            "b2": {"members": [{"ticker": "CCC", "added": "2024-01-01"}]},
            "b3": {"members": [{"ticker": "DDD", "added": "2024-01-01"}]}}
    # b2 is entirely absent from the later snapshot; b1/b3 keep their rows, with
    # removals that make b3's active set empty (present with zero members)
    day2 = {"b1": {"members": [{"ticker": "AAA", "added": "2024-01-01"},
                               {"ticker": "BBB", "added": "2024-01-01",
                                "removed": "2026-09-01"}]},
            "b3": {"members": [{"ticker": "DDD", "added": "2024-01-01",
                                "removed": "2026-09-01"}]}}
    (snaps / "2026-08-13.json").write_text(json.dumps({"version": "t", "baskets": day1}))
    (snaps / "2026-09-04.json").write_text(json.dumps({"version": "t", "baskets": day2}))
    membership = {"version": "t", "baskets": {
        "b1": {"members": day2["b1"]["members"]},
        "b2": {"members": day1["b2"]["members"]},  # still a KNOWN basket of the owner's
        "b3": {"members": day2["b3"]["members"]}}}
    monkeypatch.setattr(pit, "membership_path", lambda suite: root / "membership.json")
    monkeypatch.setattr(pit, "history_path", lambda suite: root / "membership_history.parquet")
    monkeypatch.setattr(pit, "snapshot_dir", lambda suite: snaps)
    (root / "membership.json").write_text(json.dumps(membership))
    # a LEGACY store (record_kind NaN rows) through the owner's own PUBLIC backfill
    result = pit.backfill_from_json_snapshots(pit.SUITE_US, lane="nightly")
    assert result["dates"] == ["2026-08-13", "2026-09-04"], result
    # the owner's own answer for the absent known basket: pit=True, zero members - the
    # exact answer the carry must NOT restate as "available with member_count 0"
    owner = pit.members_asof("b2", "2026-09-10", suite=pit.SUITE_US)
    assert (owner["pit"], owner["members"], owner["snapshot_date"]) == (True, [], "2026-09-04")
    cut = carry.roster_baskets(membership, "2026-09-10")
    snap = carry.membership_snapshots(membership, "2026-09-10", cut["baskets"])
    groups = snap["groups"]
    assert groups["b2"] == {"status": "unavailable", "reason": "basket_absent_from_snapshot"}
    b1 = groups["b1"]
    assert (b1["status"], b1["snapshot_date"], b1["member_count"]) == (
        "available", "2026-09-04", 1)
    assert b1["members_sha"] and len(b1["members_sha"]) == 64  # the owner's stamped sha
    assert b1["equals_current_roster"] is True
    b3 = groups["b3"]
    assert (b3["status"], b3["member_count"]) == ("available", 0)  # present, zero active


def test_n4_the_one_read_pit_path_matches_per_call_members_asof_on_the_real_store():
    """N4: the builder's one-read path answers every (group, stored date) pair on the
    REAL committed store identically to the owner's per-call ``members_asof`` on
    (pit, basis, members, snapshot_date) - the equality that alone authorizes
    computing the carried facts from a single store read. This test needs the
    committed PIT store, so it runs in the post-nightly DATA-HEALTH lane (its CI
    step is gate:data, never the PR merge gate) and FAILS - never skips - when the
    store is absent; the PULL-REQUEST-TIME pin of the same equality is the store-free
    synthetic differential in ``test_sf2_...`` below."""
    from engine import basket_membership_pit as pit
    frame = pit.read_history(pit.SUITE_US, strict=True, include_collection_records=True)
    assert not frame.empty, "the committed real PIT store must be present"
    dates = sorted({str(d) for d in frame["snapshot_date"].dropna()})
    groups = sorted({str(g) for g in frame["basket_id"].dropna()})
    fields = ("pit", "basis", "members", "snapshot_date")
    per_call = {(g, d): tuple(pit.members_asof(g, d, suite=pit.SUITE_US).get(k) for k in fields)
                for g in groups for d in dates}
    one_read = {}
    for d in dates:
        answers = carry._pit_answers_at(pit, frame, d, groups)
        assert answers is not None, d
        for g in groups:
            one_read[(g, d)] = answers[g]
    assert one_read == per_call


def _pit_row(d, b, t, added=None, removed=None, kind=None):
    """One synthetic history row in the owner's stored schema (SF2)."""
    return {"snapshot_date": d, "suite": "baskets", "basket_id": b, "ticker": t,
            "added": added, "removed": removed, "name_zh": None,
            "members_sha": "0" * 64, "source_shape": "membership",
            "record_kind": kind, "collection_id": None, "collection_receipt": None}


_SF2_DATES = ("2025-12-31", "2026-01-01", "2026-01-15", "2026-02-01", "2026-02-10",
              "2026-02-15", "2026-02-20", "2026-03-01", "2026-03-15", "2026-04-01")


def _sf2_differential(tmp_path, monkeypatch, name, rows, known, shuffle=False):
    """SF2: write a small synthetic store, point the owner's suite paths at it and
    assert the builder's one-read ``_pit_answers_at`` answer equals the owner's
    per-call ``members_asof`` on (pit, basis, members, snapshot_date) for EVERY
    (group, date) pair. No real store is needed."""
    import pandas as pd
    from engine import basket_membership_pit as pit
    root = tmp_path / name
    root.mkdir()
    history = root / "membership_history.parquet"
    (root / "membership.json").write_text(json.dumps(
        {"version": "t", "baskets": {g: {"members": []} for g in known}}))
    monkeypatch.setattr(pit, "history_path", lambda suite: history)
    monkeypatch.setattr(pit, "membership_path", lambda suite: root / "membership.json")
    frame = pd.DataFrame(rows)
    if shuffle:
        frame = frame.sample(frac=1, random_state=7).reset_index(drop=True)
    frame.to_parquet(history)
    store = pit.read_history(pit.SUITE_US, strict=True, include_collection_records=True)
    fields = ("pit", "basis", "members", "snapshot_date")
    for date in _SF2_DATES:
        answers = carry._pit_answers_at(pit, store, date, known)
        for gid in known:
            owner = tuple(pit.members_asof(gid, date, suite=pit.SUITE_US).get(k)
                          for k in fields)
            if answers is None:
                # the date predates the store: the builder falls back to the owner's
                # own per-call reader (identical by construction) - sound only when
                # the owner does not answer point-in-time for that date either
                assert owner[0] is not True, (name, date, gid, owner)
                continue
            assert tuple(answers[gid]) == owner, (name, date, gid,
                                                  tuple(answers[gid]), owner)


def test_sf2_the_one_read_pit_path_equals_per_call_members_asof_store_free(
        tmp_path, monkeypatch):
    """SF2: the one-read path is pinned WITHOUT the real store. Small synthetic
    histories are written in the owner's own store schema, both readers are pointed
    at the same synthetic store, and ``_pit_answers_at`` is asserted equal to the
    owner's per-call ``members_asof`` for every (group, date) pair - including the
    legacy shapes on which an interval reading of legacy history diverged from the
    owner's newest-snapshot reading (SF1), the interval END boundary
    (``valid_to > date``, not ``>=`` - mutation OR1) and the per-basket snapshot
    date (the basket's OWN newest covered row, never the global one - OR5)."""
    # LEGACY stores (record_kind NaN): a removal stated only in a later snapshot,
    # in that snapshot's future but passed by the query date
    _sf2_differential(tmp_path, monkeypatch, "legacy-late-future-removal", [
        _pit_row("2026-01-01", "b", "A"), _pit_row("2026-01-01", "b", "B"),
        _pit_row("2026-02-01", "b", "A", removed="2026-02-15"),
        _pit_row("2026-02-01", "b", "B")], ["b"])
    # a removal an earlier snapshot stated and a later one dropped (reinstated)
    _sf2_differential(tmp_path, monkeypatch, "legacy-reinstated", [
        _pit_row("2026-01-01", "b", "A", removed="2026-03-01"),
        _pit_row("2026-02-01", "b", "A")], ["b"])
    # a member added in the future, then that `added` revised earlier
    _sf2_differential(tmp_path, monkeypatch, "legacy-added-then-changed-in-the-future", [
        _pit_row("2026-01-01", "b", "A", added="2026-02-10"),
        _pit_row("2026-02-01", "b", "A", added="2026-01-20")], ["b"])
    # the same store with UNSORTED rows: neither reader may depend on row order
    _sf2_differential(tmp_path, monkeypatch, "legacy-unsorted", [
        _pit_row("2026-02-01", "b", "B"), _pit_row("2026-01-01", "b", "A"),
        _pit_row("2026-02-01", "b", "A", removed="2026-02-15"),
        _pit_row("2026-01-01", "b", "B")], ["b"], shuffle=True)
    # VERSIONED store: a removal CONFIRMED by a receipt on its own removal day - the
    # owner closes that interval ``valid_to = removed`` and the query AT the removal
    # day (2026-02-15 is in ``_SF2_DATES``) pins the end as EXCLUSIVE
    # (``valid_to > date``, never ``>=`` - mutation OR1). A removal merely STATED in
    # advance never closes the interval until a later receipt passes it, so the
    # receipt must sit on the boundary date itself to make it coverable then.
    _sf2_differential(tmp_path, monkeypatch, "v2-removal-boundary", [
        _pit_row("2026-01-01", "b", "A", kind="member.v2"),
        _pit_row("2026-01-01", "b", "B", kind="member.v2"),
        _pit_row("2026-02-15", "b", "A", removed="2026-02-15", kind="member.v2"),
        _pit_row("2026-02-15", "b", "B", kind="member.v2")], ["b"])
    # VERSIONED store where one basket has NO row at the newest covered date: its
    # snapshot_date is its OWN newest covered row (2026-01-01), never the global
    # newest (2026-02-01) (OR5)
    _sf2_differential(tmp_path, monkeypatch, "v2-basket-missing-at-newest-date", [
        _pit_row("2026-01-01", "b", "A", kind="member.v2"),
        _pit_row("2026-01-01", "c", "X", kind="member.v2"),
        _pit_row("2026-02-01", "c", "X", kind="member.v2")], ["b", "c"])
    # MIXED store: legacy rows then versioned rows, with a basket that stays
    # legacy-only - the owner dispatches the WHOLE covered frame to its versioned
    # path once any versioned row is covered, and so must the builder
    _sf2_differential(tmp_path, monkeypatch, "mixed-legacy-then-v2", [
        _pit_row("2026-01-01", "b", "A"), _pit_row("2026-01-01", "b", "B"),
        _pit_row("2026-01-01", "d", "D"),
        _pit_row("2026-02-01", "b", "A", kind="member.v2")], ["b", "d"])


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
        "confluence": "available", "bottoming_watch": "available", "theme_table": "available",
        "confluence_universe_sp500": "available", "confluence_universe_nasdaq": "available",
        "confluence_universe_russell": "available", "confluence_universe_baskets": "available",
        "theme_rows": "available"}
    assert blocks["r2_hazard_qualification"]["reason"] == "not_produced"
    preview = typed_blocks_of(project_sector_view(inputs, receipt, audience="preview")["data"])
    assert preview["r1_rising_priced_share"]["status"] == "available"
    assert preview["confluence"]["reason"] == "audience_not_entitled"
    assert preview["theme_rows"]["reason"] == "audience_not_entitled"


def test_builder_wires_the_carry_before_publication():
    source = (REPO / "scripts/build_sector_central.py").read_text()
    assert source.index("build_carry(site, data, _membership(), sector_flow_periods())") < source.index(
        'data["publication"] = {')


# --- lane 1 v1.1 row blocks (wire /tmp/si_plan/v11/LANE1_WIRE_V11_ROWS.md) ------

ROWS_FIVE = ("confluence_universe_sp500", "confluence_universe_nasdaq",
             "confluence_universe_russell", "confluence_universe_baskets", "theme_rows")


def _canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False,
                      sort_keys=True, separators=(",", ":")).encode("utf-8")


def test_v11_row_blocks_carry_full_group_rows_and_members():
    """REAL: the five row blocks on the committed artifacts - full group rows and
    members under their own measured cap, the wire's dating rule and the
    projection's counts. Every pin is an EQUALITY against the source file read
    in this same test, so the next nightly's data cannot break it (review r1
    SF-2); tonight's exact numbers live in the specimens and the return, not
    here."""
    built = _real_carry_blocks()

    def source(relative):
        return json.loads((SITE / relative).read_bytes())

    def dated_of(document):
        # the envelope dating rule reads the source, not a constant: the file's
        # as_of when a non-empty string, else its generated_utc
        return next(((field, document[field]) for field in ("as_of", "generated_utc")
                     if isinstance(document.get(field), str) and document[field]), None)

    for name, relative, _owner_word, arrays in carry.CONFLUENCE_UNIVERSE_ROW_BLOCKS:
        block, document = built[name], source(relative)
        assert "status" not in block, name  # the full block, never a stub
        assert len(_canonical(block)) <= carry.MAX_ROW_BLOCK_BYTES == 512 * 1024, name
        # the envelope date is the dating rule's own answer for this source
        assert (block["as_of_field"], block["as_of"]) == dated_of(document), name
        # data.as_of is the document's own value, verbatim - null stays null
        assert block["data"]["as_of"] == document.get("as_of"), name
        for array in arrays:
            # every source row is carried, per array, and so is every member
            assert len(block["data"][array]) == len(document[array]), (name, array)
            for carried_row, source_row in zip(block["data"][array], document[array]):
                assert len(carried_row.get("members", ())) == len(
                    source_row.get("members", ())), (name, array)
                for carried, member in zip(carried_row.get("members", ()),
                                           source_row.get("members", ())):
                    # N-D (review r2): key-presence + .get equality - a future
                    # source member without a name_zh key is correctly carried
                    # without the key (absent stays absent, wire §2); the test
                    # must not KeyError where the producer is right.
                    assert ("name_zh" in carried) == ("name_zh" in member), (name, array)
                    assert carried.get("name_zh") == member.get("name_zh"), (name, array)
    theme, handoff = built["theme_rows"], source("basketdata/si_handoff.json")
    context = handoff["theme_context"]
    entries = {b["id"]: b for b in source("basketdata/baskets.json")["baskets"]}
    assert "status" not in theme
    assert len(_canonical(theme)) <= carry.MAX_ROW_BLOCK_BYTES
    assert theme["as_of"] == context["as_of"]  # the anchor's own date
    assert [row["id"] for row in theme["rows"]] == list(context["themes"])
    for row in theme["rows"]:
        entry = entries.get(row["id"])
        for field in ("name", "name_zh"):
            expected = (entry.get(field) if isinstance(entry, dict)
                        and isinstance(entry.get(field), str) else None)
            assert row[field] == expected, (row["id"], field)


def test_v11_row_blocks_are_the_allow_listed_projection_of_their_sources():
    """REAL: projection exactness (wire §2) - every allow-listed key is present in
    the carry exactly when it is present in the source, with an equal value; no key
    outside the allow-lists appears; row and member order are the producer's."""
    built = _real_carry_blocks()
    for name, relative, _owner_word, arrays in carry.CONFLUENCE_UNIVERSE_ROW_BLOCKS:
        block = built[name]
        document = json.loads((SITE / relative).read_bytes())
        assert block["group_arrays"] == list(arrays)
        data = block["data"]
        assert set(data) == (set(carry._UNIVERSE_DATA_KEYS) & set(document)) | set(arrays)
        for key in carry._UNIVERSE_DATA_KEYS:
            assert (key in data) == (key in document), (name, key)
            if key in data and key != "coverage":
                assert data[key] == document[key], (name, key)
        assert set(data["coverage"]) == set(carry._UNIVERSE_COVERAGE_KEYS) \
            & set(document["coverage"])
        for key in data["coverage"]:
            assert data["coverage"][key] == document["coverage"][key], (name, key)
        for array in arrays:
            source_rows = document[array]
            assert len(data[array]) == len(source_rows), (name, array)
            for carried_row, source_row in zip(data[array], source_rows):
                assert set(carried_row) == set(carry._UNIVERSE_ROW_KEYS) & set(source_row)
                for key in carried_row:
                    if key not in ("entry", "regime", "members"):
                        assert carried_row[key] == source_row[key], (name, key)
                for nested, allow in (("entry", carry._UNIVERSE_ENTRY_KEYS),
                                      ("regime", carry._UNIVERSE_REGIME_KEYS)):
                    assert (nested in carried_row) == (nested in source_row), (name, nested)
                    if nested in source_row:
                        assert set(carried_row[nested]) == set(allow) & set(source_row[nested])
                        for key in carried_row[nested]:
                            assert carried_row[nested][key] == source_row[nested][key]
                assert ("members" in carried_row) == ("members" in source_row)
                if "members" in source_row:
                    assert len(carried_row["members"]) == len(source_row["members"])
                    for carried, source in zip(carried_row["members"], source_row["members"]):
                        assert set(carried) == set(carry._UNIVERSE_MEMBER_KEYS) & set(source)
                        for key in carried:
                            assert carried[key] == source[key]
    # theme rows (wire §3): state verbatim, names/chart_key/perf from their named
    # sources, the mapping's own order, and no href anywhere
    handoff = json.loads(_real("basketdata/si_handoff.json"))["theme_context"]
    entries = {g["id"]: g for g in json.loads(_real("basketdata/baskets.json"))["baskets"]}
    charts = {g["basket_id"]: g.get("chart_key") for g in
              json.loads(_real("marketdata/basket_confluence.json"))["baskets"]}
    block = built["theme_rows"]
    assert block["as_of"] == handoff["as_of"] == "2026-11-06"
    assert block["perf_as_of"] == json.loads(_real("basketdata/baskets.json"))["as_of"]
    assert [row["id"] for row in block["rows"]] == list(handoff["themes"])
    for row in block["rows"]:
        theme_id = row["id"]
        assert row["state"] == handoff["themes"][theme_id]  # verbatim
        assert row["name"] == entries[theme_id]["name"]
        assert row["name_zh"] == entries[theme_id]["name_zh"]
        assert row["chart_key"] == charts[theme_id]
        assert set(row["perf"]) <= set(carry.THEME_PERF_WINDOWS)
        for window, measures in row["perf"].items():
            assert set(measures) <= {"ret", "rel"}
            for key, value in measures.items():
                assert value == entries[theme_id]["perf"][window][key]
    assert "href" not in json.dumps(block)


_ROWS_SITE_FILES = (
    "marketdata/subsector_confluence.json",
    "marketdata/subsector_confluence_nasdaq.json",
    "marketdata/subsector_confluence_russell.json",
    "marketdata/subsector_confluence_china.board.json",
    "marketdata/basket_confluence.json",
    "basketdata/baskets.json",
    "basketdata/si_handoff.json",
)


def _rows_site(tmp_path, mutate=None) -> Path:
    """A tmp site holding the real row-block sources; ``mutate`` maps one relative
    name to replacement bytes, or ``None`` to delete the file."""
    for relative in _ROWS_SITE_FILES:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((SITE / relative).read_bytes())
    for relative, payload in (mutate or {}).items():
        target = tmp_path / relative
        if payload is None:
            target.unlink()
        else:
            target.write_bytes(payload)
    return tmp_path


def _nasdaq_mutation(transform, *, non_finite=False):
    """Rewrite the real Nasdaq document through ``transform`` and encode it.

    ``non_finite`` keeps the encoder's NaN spelling so the file carries a bare
    ``NaN`` literal - exactly the hostile on-disk shape the reader must refuse.
    """
    document = json.loads((SITE / "marketdata/subsector_confluence_nasdaq.json").read_bytes())
    transform(document)
    return json.dumps(document, ensure_ascii=False,
                      allow_nan=non_finite).encode("utf-8")


NASDAQ = "marketdata/subsector_confluence_nasdaq.json"


def _nasdaq_hostile_cases():
    """(label, make_mutate) pairs - each ``make_mutate`` is a zero-arg callable.

    The rewrite is evaluated at TEST time, never at import/parametrize time: a
    replay that points ``SITE`` at another night's files must mutate THOSE
    bytes, or the tmp site would carry this night's Nasdaq dates while the
    good build carries the replay night's (review r2 acceptance replay)."""
    deep = ('{"label":' * 3000) + "1" + ("}" * 3000)  # built as text: never recursed here
    cases = [
        ("absent", lambda: {NASDAQ: None}),
        ("corrupt bytes", lambda: {NASDAQ: b"not json {"}),
        ("wrong owner word", lambda: {NASDAQ: _nasdaq_mutation(
            lambda d: d.update(universe="sp500_subsectors"))}),
        ("undated", lambda: {NASDAQ: _nasdaq_mutation(
            lambda d: (d.pop("as_of", None), d.pop("generated_utc", None)))}),
        ("group array not a list", lambda: {NASDAQ: _nasdaq_mutation(
            lambda d: d.update(subsectors={}))}),
        ("row not a mapping", lambda: {NASDAQ: _nasdaq_mutation(
            lambda d: d.update(sectors=["x"]))}),
        ("row without key", lambda: {NASDAQ: _nasdaq_mutation(
            lambda d: d.update(sectors=[{"kind": "sector", "label": "X"}]))}),
        ("members not a list", lambda: {NASDAQ: _nasdaq_mutation(
            lambda d: d["sectors"][0].update(members="nope"))}),
        ("member without ticker", lambda: {NASDAQ: _nasdaq_mutation(
            lambda d: d["sectors"][0].update(members=[{"price": 1.0}]))}),
        ("entry as a string", lambda: {NASDAQ: _nasdaq_mutation(
            lambda d: d["sectors"][0].update(entry="T3"))}),
        ("nan literal in a value", lambda: {NASDAQ: _nasdaq_mutation(
            lambda d: d["coverage"].update(n_gateable=float("nan")), non_finite=True)}),
        ("deeply nested value", lambda: {NASDAQ: deep.encode("utf-8")}),
    ]
    return cases


@pytest.mark.parametrize("label,make_mutate", _nasdaq_hostile_cases(),
                         ids=[case[0] for case in _nasdaq_hostile_cases()])
def test_v11_one_bad_universe_file_removes_only_that_universe_block(
        tmp_path, label, make_mutate):
    """FIXTURE over real files: a corrupted/absent/wrong-owner/undated Nasdaq file
    never raises and removes ONLY the Nasdaq row block. The other four row blocks
    and ``theme_table``/``theme_rows`` are byte-equal to the unmutated build; the
    incumbent ``confluence`` block is exactly the incumbent ``confluence()`` law's
    own answer over the same mutated site (row-shape mutations leave it byte-equal
    to the good build; an absent/unreadable/undated file is dropped by the
    incumbent's own four-or-nothing rule - never by the new blocks)."""
    good = carry.build_carry(SITE, {"as_of": "2026-11-06", "sectors": []})
    site = _rows_site(tmp_path, make_mutate())
    built = carry.build_carry(site, {"as_of": "2026-11-06", "sectors": []})  # never raises
    assert "confluence_universe_nasdaq" not in built, label
    for name in ("confluence_universe_sp500", "confluence_universe_russell",
                 "confluence_universe_baskets", "theme_rows", "theme_table"):
        assert _canonical(built[name]) == _canonical(good[name]), (label, name)
    # the incumbent confluence block answers exactly its own law over this site
    assert built.get("confluence") == carry.confluence(site)
    if label == "wrong owner word":
        # the incumbent carries the universe field verbatim without gating on it:
        # its nasdaq entry shows the injected word (its own law over this file)
        assert built["confluence"]["nasdaq"]["universe"] == "sp500_subsectors", label
    elif label in ("group array not a list", "row not a mapping",
                   "row without key", "members not a list",
                   "member without ticker", "entry as a string"):
        # the incumbent never reads the group arrays: its value is untouched
        assert _canonical(built["confluence"]) == _canonical(good["confluence"]), label
    else:
        # absent / unreadable / non-finite / undated: the incumbent's OWN refusal drops it
        assert "confluence" not in built and carry.confluence(site) is None, label


def test_v11_theme_rows_fail_closed_cases(tmp_path):
    """FIXTURE: the theme-row anchor refuses a non-mapping theme value, an empty
    anchor and an undated context - each dropping ONLY the row block, never a
    universe block; the incumbent ``theme_table`` answers its own law (it carries
    a non-mapping value verbatim and does not require a dated context)."""
    good = carry.build_carry(SITE, {"as_of": "2026-11-06", "sectors": []})

    def handoff_mutation(transform):
        document = json.loads((SITE / "basketdata/si_handoff.json").read_bytes())
        transform(document)
        return json.dumps(document, ensure_ascii=False).encode("utf-8")

    for label, transform, table in (
            ("theme value not a mapping",
             lambda d: d["theme_context"]["themes"].update(memory_storage="thin"), True),
            ("empty anchor", lambda d: d["theme_context"].update(themes={}), False),
            ("undated context", lambda d: d["theme_context"].pop("as_of"), False)):
        site = _rows_site(tmp_path, {"basketdata/si_handoff.json": handoff_mutation(transform)})
        built = carry.build_carry(site, {"as_of": "2026-11-06", "sectors": []})  # never raises
        assert "theme_rows" not in built, label
        assert ("theme_table" in built) == table, label
        if table:
            # the incumbent carries the non-mapping theme value verbatim
            assert built["theme_table"]["themes"]["memory_storage"] == "thin", label
        elif label == "undated context":
            # the raw function returns the undated table; the build's _DATED_BLOCKS
            # rule drops it (an undated block is never carried with a null date)
            assert carry.theme_table(site)["as_of"] is None, label
        assert _canonical(built["confluence_universe_sp500"]) == _canonical(
            good["confluence_universe_sp500"]), label
        assert _canonical(built["confluence_universe_baskets"]) == _canonical(
            good["confluence_universe_baskets"]), label
    # no dated baskets.json: perf_as_of null and no row carries a perf key
    site = _rows_site(tmp_path)
    baskets = json.loads((site / "basketdata/baskets.json").read_bytes())
    baskets.pop("as_of")
    (site / "basketdata/baskets.json").write_text(json.dumps(baskets))
    block = carry.theme_rows(site)
    assert block["perf_as_of"] is None
    assert all("perf" not in row for row in block["rows"])
    # a theme basket without perf: no perf key on that row, every other row keeps its own
    site = _rows_site(tmp_path)  # fresh copy: the dating pop above must not leak in
    baskets = json.loads((site / "basketdata/baskets.json").read_bytes())
    orphan = next(row["id"] for row in good["theme_rows"]["rows"])  # first theme id
    next(b for b in baskets["baskets"] if b["id"] == orphan).pop("perf")
    (site / "basketdata/baskets.json").write_text(json.dumps(baskets))
    block = carry.theme_rows(site)
    assert "perf" not in next(row for row in block["rows"] if row["id"] == orphan)
    assert sum("perf" in row for row in block["rows"]) == len(block["rows"]) - 1


def test_v11_over_cap_row_blocks_carry_the_stub_never_shortened_rows(monkeypatch):
    """FIXTURE over real files: above MAX_ROW_BLOCK_BYTES the small stub is carried
    (dated, under the ordinary block cap) - never a shortened row set. Every stub
    date and every count is an EQUALITY against the source file read in this same
    test, so the next nightly's data cannot break it (review r2); tonight's exact
    numbers live in the specimens and the return, not here."""
    central = {"as_of": "2026-11-06", "sectors": []}
    full = carry.build_carry(SITE, central)

    def dated_of(document):
        # the envelope dating rule reads the source, not a constant: the file's
        # as_of when a non-empty string, else its generated_utc
        return next(((field, document[field]) for field in ("as_of", "generated_utc")
                     if isinstance(document.get(field), str) and document[field]), None)

    def source(relative):
        return json.loads((SITE / relative).read_bytes())

    stubs = {name: (relative, *dated_of(source(relative)))
             for name, relative, _owner_word, _arrays
             in carry.CONFLUENCE_UNIVERSE_ROW_BLOCKS}
    with monkeypatch.context() as m:
        m.setattr(carry, "MAX_ROW_BLOCK_BYTES", 512)  # below even Russell's 552 bytes
        built = carry.build_carry(SITE, central)
    for name, (source_name, field, as_of) in stubs.items():
        assert built[name] == {"source": source_name, "as_of": as_of, "as_of_field": field,
                               "status": "unavailable", "reason": "block_too_large"}, name
        assert "data" not in built[name] and "group_arrays" not in built[name]
        assert carry._bounded(built[name]) == built[name]  # the stub passes the bound
    handoff = source("basketdata/si_handoff.json")
    assert built["theme_rows"] == {
        "source": "basketdata/si_handoff.json#theme_context.themes",
        "as_of": handoff["theme_context"]["as_of"],
        "status": "unavailable", "reason": "block_too_large"}
    assert "rows" not in built["theme_rows"]
    # no row is dropped to fit: the same inputs under the real cap carry every row
    assert len(full["confluence_universe_sp500"]["data"]["subsectors"]) == \
        len(source("marketdata/subsector_confluence.json")["subsectors"])
    assert len(full["confluence_universe_baskets"]["data"]["baskets"]) == \
        len(source("marketdata/basket_confluence.json")["baskets"])
    assert len(full["theme_rows"]["rows"]) == len(handoff["theme_context"]["themes"])
    # the cap boundary itself: one byte under is the full block, one byte over the stub
    size = len(_canonical(full["confluence_universe_baskets"]))
    with monkeypatch.context() as m:
        m.setattr(carry, "MAX_ROW_BLOCK_BYTES", size - 1)
        over = carry.confluence_universe_rows(
            SITE, "marketdata/basket_confluence.json", "curated_baskets", ("baskets",))
        m.setattr(carry, "MAX_ROW_BLOCK_BYTES", size)
        exact = carry.confluence_universe_rows(
            SITE, "marketdata/basket_confluence.json", "curated_baskets", ("baskets",))
    assert over["status"] == "unavailable" and over["reason"] == "block_too_large"
    assert "status" not in exact and len(exact["data"]["baskets"]) == \
        len(source("marketdata/basket_confluence.json")["baskets"])


def test_v11_an_absent_allow_listed_row_key_stays_absent():
    """FIXTURE (wire §2): an allow-listed key absent from the source row is absent
    from the carried row - never defaulted to null. (On tonight's real artifacts
    every row carries every key it ever carries, so only a removed key can prove
    this.) Present keys stay verbatim on the same row."""
    source_row = json.loads((SITE / NASDAQ).read_bytes())["sectors"][0]
    assert "label_zh" in source_row  # precondition: a really-present key to remove
    without = dict(source_row)
    del without["label_zh"]
    carried = carry._universe_row(without)
    assert carried is not None and "label_zh" not in carried
    full = carry._universe_row(source_row)
    assert full["label_zh"] == source_row["label_zh"]


def test_v11_an_absent_member_name_zh_key_is_carried_absent(tmp_path):
    """N-D (review r2): a source member WITHOUT a ``name_zh`` key is carried
    without the key - absent stays absent (wire §2), the producer is right, so
    nothing may KeyError and no null may be defaulted in. Untouched members on
    the same row keep their own values."""
    relative = "marketdata/subsector_confluence.json"
    document = json.loads((SITE / relative).read_bytes())
    row = next(r for r in document["subsectors"] if r.get("members"))
    assert "name_zh" in row["members"][0]  # precondition: a key to remove
    del row["members"][0]["name_zh"]
    site = _rows_site(tmp_path, {relative: json.dumps(
        document, ensure_ascii=False, allow_nan=False).encode("utf-8")})
    block = carry.confluence_universe_rows(
        site, relative, "sp500_subsectors", ("subsectors", "sectors"))
    assert block is not None
    carried_row = next(r for r in block["data"]["subsectors"] if r.get("members"))
    members = carried_row["members"]
    assert "name_zh" not in members[0]  # absent at the source, absent in the carry
    assert all("name_zh" in member for member in members[1:])  # untouched keep theirs


def _baskets_mutation(transform):
    """Rewrite the real baskets.json through ``transform`` and encode it."""
    document = json.loads((SITE / "basketdata/baskets.json").read_bytes())
    transform(document)
    return json.dumps(document, ensure_ascii=False, allow_nan=False).encode("utf-8")


def test_v11_extra_coverage_key_is_dropped(tmp_path):
    """SF-3/M8 (review r1): a key outside the coverage allow-list is dropped -
    the carried coverage is exactly the allow-listed keys the source has."""
    def add_extra(document):
        document["coverage"]["owner_note"] = "not in the allow-list"

    site = _rows_site(tmp_path, {NASDAQ: _nasdaq_mutation(add_extra)})
    block = carry.confluence_universe_rows(
        site, "marketdata/subsector_confluence_nasdaq.json",
        "nasdaq_subsectors", ("subsectors", "sectors"))
    source_coverage = json.loads((site / NASDAQ).read_bytes())["coverage"]
    assert block is not None and "owner_note" not in block["data"]["coverage"]
    assert set(block["data"]["coverage"]) == set(carry._UNIVERSE_COVERAGE_KEYS) \
        & set(source_coverage)


def test_v11_non_string_theme_name_fields_read_null(tmp_path):
    """SF-3/M11 (review r1): a non-string ``name`` / ``name_zh`` in baskets.json
    reads null on the theme row; every untouched field stays the source's own
    value (read from the mutated source, not a nightly constant)."""
    def non_string(document):
        by_id = {b["id"]: b for b in document["baskets"]}
        by_id["memory_storage"]["name"] = 17
        by_id["big_pharma"]["name_zh"] = ["x"]

    site = _rows_site(tmp_path, {"basketdata/baskets.json": _baskets_mutation(non_string)})
    rows = {row["id"]: row for row in carry.theme_rows(site)["rows"]}
    source = {b["id"]: b for b in
              json.loads((site / "basketdata/baskets.json").read_bytes())["baskets"]}
    assert rows["memory_storage"]["name"] is None            # 17 -> null
    assert rows["memory_storage"]["name_zh"] == source["memory_storage"]["name_zh"]
    assert rows["big_pharma"]["name_zh"] is None             # ["x"] -> null
    assert rows["big_pharma"]["name"] == source["big_pharma"]["name"]


def test_v11_theme_perf_needs_baskets_list_even_with_string_as_of(tmp_path):
    """N-3 (review r1, COO ruling - null stays): a baskets.json whose top-level
    ``as_of`` is a non-empty string but whose ``baskets`` is not a list reads
    ``perf_as_of`` null and no row carries a ``perf`` key. The string ``as_of``
    alone must not switch perf on."""
    def not_a_list(document):
        document["baskets"] = {"id": "memory_storage"}  # mapping, not a list

    site = _rows_site(tmp_path, {"basketdata/baskets.json": _baskets_mutation(not_a_list)})
    block = carry.theme_rows(site)
    source = json.loads((site / "basketdata/baskets.json").read_bytes())
    assert isinstance(source["as_of"], str) and source["as_of"]  # precondition
    assert block is not None and block["perf_as_of"] is None
    assert all("perf" not in row for row in block["rows"])


def test_v11_theme_perf_with_no_allowed_windows_carries_empty_mapping(tmp_path):
    """N-3 (review r1): a basket whose ``perf`` mapping has none of the closed
    window keys still carries ``perf`` - as an empty mapping, not an absent key."""
    def foreign_windows(document):
        by_id = {b["id"]: b for b in document["baskets"]}
        by_id["memory_storage"]["perf"] = {"q7": {"ret": 0.5}, "ytd2": {"ret": 0.1}}

    site = _rows_site(tmp_path, {"basketdata/baskets.json": _baskets_mutation(foreign_windows)})
    rows = {row["id"]: row for row in carry.theme_rows(site)["rows"]}
    assert rows["memory_storage"]["perf"] == {}


def test_v11_theme_producer_null_perf_leaves_the_key_absent(tmp_path):
    """N-3 (review r1): a producer ``perf: null`` on the basket entry is not
    carried as ``null`` - the row simply has no ``perf`` key."""
    def null_perf(document):
        by_id = {b["id"]: b for b in document["baskets"]}
        by_id["memory_storage"]["perf"] = None

    site = _rows_site(tmp_path, {"basketdata/baskets.json": _baskets_mutation(null_perf)})
    rows = {row["id"]: row for row in carry.theme_rows(site)["rows"]}
    assert "perf" not in rows["memory_storage"]
    # an untouched basket on the same night still carries its perf
    assert "perf" in rows["big_pharma"]


def _over_ceiling(path):
    """A sparse file whose on-disk size is one byte over the N-5 ceiling."""
    with open(path, "wb") as handle:
        handle.truncate(carry._ROW_SOURCE_MAX_BYTES + 1)
    return path


def test_v11_over_ceiling_source_file_is_not_parsed_and_carries_the_stub(
        tmp_path, monkeypatch):
    """N-5 (review r1): a row-block source file over ``_ROW_SOURCE_MAX_BYTES``
    on disk is NEVER parsed - the reader carries the small ``block_too_large``
    stub instead, undated (the date lives inside the file we refuse to open).
    Proof of no parse: ``_read`` is patched to raise."""
    def boom(_path):
        raise AssertionError("an over-ceiling source file was parsed")
    monkeypatch.setattr(carry, "_read", boom)
    site = _rows_site(tmp_path)
    _over_ceiling(site / NASDAQ)
    block = carry.confluence_universe_rows(
        site, "marketdata/subsector_confluence_nasdaq.json",
        "nasdaq_subsectors", ("subsectors", "sectors"))
    assert block == {"source": "marketdata/subsector_confluence_nasdaq.json",
                     "status": "unavailable", "reason": "block_too_large"}


def test_v11_over_ceiling_baskets_file_gives_theme_rows_the_stub(tmp_path):
    """N-5 (review r1): the theme-row reader guards its own sources the same
    way - an over-ceiling baskets.json carries the block_too_large stub, not a
    degraded block with null names and no perf."""
    site = _rows_site(tmp_path)
    _over_ceiling(site / "basketdata/baskets.json")
    block = carry.theme_rows(site)
    assert block == {"source": "basketdata/si_handoff.json#theme_context.themes",
                     "status": "unavailable", "reason": "block_too_large"}


def test_v11_over_ceiling_stub_survives_build_carry_undated(tmp_path):
    """N-5 (review r1): the undated stub survives ``build_carry``'s undated-drop
    - the block is carried as ``block_too_large``, never silently degraded to
    ``not_produced``."""
    site = _rows_site(tmp_path)
    _over_ceiling(site / NASDAQ)
    produced = carry.build_carry(site, {})
    assert produced["confluence_universe_nasdaq"] == {
        "source": "marketdata/subsector_confluence_nasdaq.json",
        "status": "unavailable", "reason": "block_too_large"}


def test_v11_source_file_at_the_ceiling_is_read_normally(tmp_path, monkeypatch):
    """N-5 (review r1): the guard is strictly greater-than - a file at exactly
    the ceiling is parsed normally and carries the same block as the unguarded
    read. The ceiling is pinned to the real file's own size for the boundary
    case, so no 64 MiB fixture is written."""
    site = _rows_site(tmp_path)
    monkeypatch.setattr(carry, "_ROW_SOURCE_MAX_BYTES", (site / NASDAQ).stat().st_size)
    assert (site / NASDAQ).stat().st_size == carry._ROW_SOURCE_MAX_BYTES
    block = carry.confluence_universe_rows(
        site, "marketdata/subsector_confluence_nasdaq.json",
        "nasdaq_subsectors", ("subsectors", "sectors"))
    reference = carry.confluence_universe_rows(
        SITE, "marketdata/subsector_confluence_nasdaq.json",
        "nasdaq_subsectors", ("subsectors", "sectors"))
    assert block is not None and "status" not in block
    assert block == reference  # the same bytes: an unguarded read's equal


def _base_guard_site(tmp_path):
    """A FIXED synthetic site for the base-vs-head byte guard (review r2 SF-A).

    Literal inputs that cannot change with the night, exercising both incumbent
    readers with real content: all four universes valid (two carrying id rows),
    one ``as_of``-dated and one ``generated_utc``-dated, and a theme table with
    three rows. Returns the site (== ``tmp_path``)."""
    documents = {
        # as_of-dated; rows in two of the three id lists
        "marketdata/subsector_confluence.json": {
            "as_of": "2099-01-02", "universe": "sp500_subsectors", "ok": True,
            "benchmark": "SPY", "coverage": {"n_subsectors": 2, "n_sectors": 1},
            "entry_now": ["memory_storage", "big_pharma"],
            "forming": ["ai_semiconductors"], "headwind": []},
        # generated_utc-dated (no as_of): the dating rule's other arm
        "marketdata/subsector_confluence_nasdaq.json": {
            "generated_utc": "2099-01-02 09:38 UTC", "universe": "nasdaq_subsectors",
            "ok": True, "benchmark": "QQQ", "coverage": {"n_subsectors": 1},
            "entry_now": ["memory_storage"], "forming": [],
            "headwind": ["big_pharma"]},
        "marketdata/subsector_confluence_russell.json": {
            "as_of": "2099-01-02", "universe": "russell_subsectors", "ok": True,
            "benchmark": "IWM", "coverage": {"n_subsectors": 0},
            "entry_now": [], "forming": [], "headwind": []},
        "marketdata/subsector_confluence_china.board.json": {
            "as_of": "2099-01-02", "universe": "cn_subsectors", "ok": True,
            "benchmark": "510300.SS", "coverage": {"n_subsectors": 1},
            "entry_now": ["cn_memory_storage"], "forming": [], "headwind": []},
        "basketdata/si_handoff.json": {
            "theme_context": {"as_of": "2099-01-02",
                              "themes": {"memory_storage": {"state": "entry_now"},
                                         "big_pharma": {"state": "forming"},
                                         "ai_semiconductors": {"state": "headwind"}}}},
    }
    for relative, document in documents.items():
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(json.dumps(document, ensure_ascii=False,
                                      allow_nan=False).encode("utf-8"))
    return tmp_path


def test_v11_confluence_and_theme_table_are_byte_identical_to_the_base(tmp_path):
    """FIXTURE (review r2 SF-A): wire §0 - the incumbent ``confluence`` and
    ``theme_table`` blocks are byte-identical before and after. The literals pin
    the canonical hashes of the two blocks built from a FIXED synthetic site
    (``_base_guard_site`` - literal inputs, so no nightly refresh can move
    them). At authoring time the BASE module (commit a089d2f9b4d7), loaded
    outside the repo tree, produced the same two hashes on the same fixture
    (proof quoted in the r2 return; the committed test needs no git/history).

    Dated record, real 2026-11-09 artifacts: the two blocks hashed
    ``6d2c77f6de4cf30c35d542a2a3a97fe3af2d3601f42b47089086e624d0150deb`` and
    ``1f62db7c409f1f4410997a4f529e76fb07d3e644e721eecec63eb6e372302914``;
    base-versus-head byte equality on real artifacts was confirmed by the
    independent reviews r1 and r2 (probe p4). On the real site this test now
    asserts only what holds on any night: both blocks present, no ``status``,
    and the same top-level key sets as the fixture blocks."""
    site = _base_guard_site(tmp_path)
    fixture_confluence = carry.confluence(site)
    fixture_theme_table = carry.theme_table(site)
    assert fixture_confluence is not None and fixture_theme_table is not None
    assert hashlib.sha256(_canonical(fixture_confluence)).hexdigest() == \
        "00949329d93bb8e2d3273230c937ce17ddf725c0455b8cc57d14374053729518"
    assert hashlib.sha256(_canonical(fixture_theme_table)).hexdigest() == \
        "a390afa123f158e77eef504bdfd807fefb01093eeac4820431b14c6a1e76648c"
    # the fixture really exercises both readers: four universes, two with id
    # rows; both dating arms; a three-row theme table
    assert set(fixture_confluence) == {"sp500", "nasdaq", "russell", "china"}
    assert [fixture_confluence[key]["as_of_field"] for key in fixture_confluence] == \
        ["as_of", "generated_utc", "as_of", "as_of"]
    assert len(fixture_theme_table["themes"]) == 3
    # REAL, night-independent: the live site's two incumbent blocks keep the
    # fixture's shapes - present, never a stub, same top-level key sets
    built = _real_carry_blocks()
    assert built["confluence"] is not None and "status" not in built["confluence"]
    assert built["theme_table"] is not None and "status" not in built["theme_table"]
    assert set(built["confluence"]) == set(fixture_confluence)
    assert set(built["theme_table"]) == set(fixture_theme_table)


def test_v11_free_js_twin_omits_the_five_row_blocks_and_nothing_else():
    """SF-1 (review r1): the render-blocking JS twin drops exactly the five row
    blocks from ``carried``; the JSON member data keeps all twelve and is not
    mutated; every other key of the twin equals the member's."""
    from scripts.build_sector_central import _js_twin_data
    central = _central()
    central["carried"] = _real_carry_blocks()
    twin = _js_twin_data(central)
    assert set(ROWS_FIVE) <= set(central["carried"])  # the JSON member keeps all twelve
    assert set(twin["carried"]) & set(ROWS_FIVE) == set()
    assert twin["carried"] == {name: block for name, block in central["carried"].items()
                               if name not in ROWS_FIVE}
    assert set(twin) == set(central)
    for key in central:
        if key != "carried":
            assert twin[key] == central[key], key

