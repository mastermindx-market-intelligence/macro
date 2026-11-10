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
                          "membership_first_known", "membership_snapshots"}
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
                          "membership_first_known", "membership_snapshots"}
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


def test_n5_a_pit_builder_failure_degrades_only_the_pit_facts(tmp_path, monkeypatch):
    """N5: ANY failure of the PIT builder - here the engine module failing to import -
    makes ONLY the two point-in-time facts unavailable (``membership_unreadable``);
    every other carried block is still served. KeyboardInterrupt/SystemExit are never
    swallowed by the degradation."""
    def boom():
        raise ImportError("engine missing")
    monkeypatch.setattr(carry, "_pit_module", boom)
    site = tmp_path / "site"
    (site / "basketdata").mkdir(parents=True)
    (site / "basketdata/baskets.json").write_text(json.dumps(
        {"baskets": [{"id": "g", "observation": {"effective_as_of": "2026-11-06"}}]}))
    membership = _roster_doc({"g": {"members": [{"ticker": "A", "added": "2024-01-01"}]}})
    built = carry.build_carry(site, {"as_of": "2026-11-06", "sectors": []}, membership, None)
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
    computing the carried facts from a single store read plus the owner's public
    ``membership_intervals_from_history``. Also reports before/after wall time."""
    import time
    from engine import basket_membership_pit as pit
    frame = pit.read_history(pit.SUITE_US, strict=True, include_collection_records=True)
    assert not frame.empty, "the committed real PIT store must be present"
    dates = sorted({str(d) for d in frame["snapshot_date"].dropna()})
    groups = sorted({str(g) for g in frame["basket_id"].dropna()})
    fields = ("pit", "basis", "members", "snapshot_date")
    started = time.perf_counter()
    per_call = {(g, d): tuple(pit.members_asof(g, d, suite=pit.SUITE_US).get(k) for k in fields)
                for g in groups for d in dates}
    t_per_call = time.perf_counter() - started
    started = time.perf_counter()
    one_read = {}
    for d in dates:
        answers = carry._pit_answers_at(pit, frame, d, groups)
        assert answers is not None, d
        for g in groups:
            one_read[(g, d)] = answers[g]
    t_one_read = time.perf_counter() - started
    print(f"N4 wall time over {len(per_call)} (group, stored date) pairs: "
          f"per-call members_asof {t_per_call:.2f}s vs one-read {t_one_read:.2f}s")
    assert one_read == per_call
    assert t_one_read < t_per_call


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
