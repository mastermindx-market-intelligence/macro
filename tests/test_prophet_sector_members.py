"""Pure-join contracts for ``engine/prophet_sector_members.py`` (``prophet.sector_members/v1``).

Two capture sources, one set of laws
------------------------------------
REAL       When the Sector programme's lane-1 reader is on this tree
           (``lib/sector_generation_contract.py`` + its test helpers), the Sector
           population is the committed producer artifacts under ``site/``
           (session 2026-11-06) re-expressed through ``tests/test_sector_population.py::
           _real_bundle``, published through the REAL private-store publisher and
           captured ONCE through the route's own ``capture_sector_join``.
SYNTHETIC  Until that reader lands on ``main`` the same tests run over a
           synthetic population of the SAME shape (``lib.sector_population.
           Population``'s fields this join reads: ``groups``/``rows``/``unserved``/
           ``first_known``/``industry_classification``), whose member symbols are
           drawn from the committed ``site/prophet/index.json`` so open and
           resolved plans really occur in the fixture group.  The join engine
           reads its population with ``getattr`` only, so the shape is the whole
           interface.  Every law below is asserted in both modes; assertions about
           magnitudes of the real roster (49 baskets, ~700 symbols) run in REAL
           mode only.

Both modes: the small Prophet books for precedence/counts tests are synthetic
dicts (the index is a wire document, not a store); the residual-unaccounted
population is a minimal fake (the owner never produces a gap today; the join
must still report one honestly).  The Prophet index digested by the sort,
digest and non-interference tests is the committed ``site/prophet/index.json``.

This file pins the four product laws: descriptive only, complete population
(``configured == served + accounted_unserved + unaccounted``; state-sum ==
served), null+reason instead of invented numbers, and P3 non-interference.
"""
from __future__ import annotations

import ast
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app import prophet_sector_members as route_mod
from engine import prophet_sector_members as engine

try:  # The Sector lane-1 reader and its real-bundle helpers (not yet on main).
    from tests.test_sector_generation_reader import _publish
    from tests.test_sector_population import PUBLISHED, _real_bundle, _real_carry_blocks
    LANE1 = True
except ImportError:
    _publish = PUBLISHED = _real_bundle = _real_carry_blocks = None
    LANE1 = False

#: The real bundle's session (``tests/test_sector_population.py::SESSION``),
#: shared by the synthetic capture so both modes speak about the same day.
SESSION = "2026-11-06"
REPO = Path(__file__).resolve().parents[1]

STATE_KEYS = ("open_plan", "resolved_plan", "early_observation", "none", "unavailable")
GROUP = "us_sector_industrials"


# --- the capture: REAL (lane 1 present) or SYNTHETIC of the same shape -------------

#: Distinctive values that ONLY the paying-member-only carried blocks would
#: contain; the synthetic capture plants them so the emission test has teeth.
SENTINEL_CARRIED = {
    "theme_rows": {"rows": [{"chart_key": "b-sentinel-theme-row", "name": "Sentinel"}]},
    "confluence_universe_sp500": {"data": {"universe": "sentinel-universe-sp500",
                                           "entry_now": ["sentinel-subsector-a"]}},
    "confluence_universe_nasdaq": {"data": {"universe": "sentinel-universe-nasdaq",
                                            "entry_now": ["sentinel-subsector-b"]}},
    "confluence_universe_russell": {"data": {"universe": "sentinel-universe-russell",
                                             "entry_now": []}},
    "confluence_universe_baskets": {"data": {"universe": "sentinel-universe-baskets",
                                             "entry_now": []}},
}


def _index_symbols() -> tuple[list[str], list[str]]:
    """(assets with an open plan, assets with only resolved plans), sorted, from
    the committed index — so the synthetic group really holds both states."""
    plans = json.loads((REPO / "site/prophet/index.json").read_bytes())["plans"]
    open_assets = sorted({engine.normalize_ticker(p.get("asset")) for p in plans
                          if p.get("closed") is False and p.get("asset")})
    closed_assets = sorted({engine.normalize_ticker(p.get("asset")) for p in plans
                            if p.get("closed") is True and p.get("asset")} - set(open_assets))
    return open_assets, closed_assets


def synthetic_capture(*, pit: bool = True):
    """(population, capture, baskets doc, central doc) — the tuple
    ``capture_sector_join`` returns, built in memory with lane 1's shape."""
    open_assets, closed_assets = _index_symbols()
    industrials = sorted({"CARR", "BRK.B", "ZZQA", "ZZQB", "ZZQC", *open_assets[:12],
                          *closed_assets[:6]})
    defensives = sorted({"CARR", "ZZQD", *open_assets[12:15]})
    ai = sorted({"ZZQA", *open_assets[15:20]})
    groups = (
        {"group_id": "us_sector_industrials", "name": "US Industrials (equal weight)",
         "name_zh": "工业（等权）", "n_configured_current": len(industrials)},
        {"group_id": "defensives", "name": "Defensives", "name_zh": None,
         "n_configured_current": len(defensives) + 1},
        {"group_id": "ai_infrastructure", "name": "AI Infrastructure", "name_zh": None,
         "n_configured_current": len(ai)},
    )
    rows = []
    for gid, symbols in (("us_sector_industrials", industrials), ("defensives", defensives),
                         ("ai_infrastructure", ai)):
        for symbol in symbols:
            rows.append({"group_id": gid, "symbol": symbol, "name": f"{symbol} Holdings",
                         "industry": {"status": "available", "label": "Capital Goods"},
                         "sub_industry": {"status": "unavailable", "reason": "not_produced"},
                         "membership": {"effective_on": "2023-05-09"}})
    first_known = ({"status": "available",
                    "groups": {g["group_id"]: {r["symbol"]: "2026-08-13" for r in rows
                                               if r["group_id"] == g["group_id"]}
                               for g in groups}}
                   if pit else {"status": "unavailable", "reason": "not_produced"})
    population = SimpleNamespace(
        groups=groups, rows=tuple(rows),
        unserved=({"group_id": "defensives", "symbol": "ZZQX",
                   "reason": "absent_from_price_panel"},),
        configured_current=sum(g["n_configured_current"] for g in groups),
        served=len(rows), unaccounted=0, first_known=first_known,
        industry_classification={"status": "available",
                                 "basis": "current_basis_industry_labels"},
        sub_industry_classification={"status": "unavailable", "reason": "not_produced"})
    capture = {"generation_id": "psm-g1", "content_id": "sha256:" + "c" * 64,
               "published_at": "2026-11-06T23:00:00Z", "source_session": SESSION,
               "qualification": "stale", "read_captured_at": "2026-11-10T00:00:00+00:00",
               "member_sha256": {"basketdata/baskets.json": "b" * 64,
                                 "sectordata/sector_central.json": "d" * 64}}
    baskets = {"baskets": [
        {"id": "us_sector_industrials", "perf": {"20d": {"ret": 0.076, "rel": 0.044}}},
        {"id": "defensives", "perf": {"20d": {"ret": -0.012, "rel": None}}},
    ]}
    central = {"baskets": [{"id": "b-us_sector_industrials", "state": {"phase": "Leading"}}],
               "measured_read": {"generation": {"benchmark": "SPY"}},
               "carried": copy.deepcopy(SENTINEL_CARRIED)}
    return population, capture, baskets, central


def carried_blocks() -> dict:
    """The carried blocks the capture actually contains (real or sentinel)."""
    return _real_carry_blocks() if LANE1 else copy.deepcopy(SENTINEL_CARRIED)


@pytest.fixture(scope="module")
def real_join(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("psm-join")
    if LANE1:
        _, result, root = _publish(tmp, _real_bundle(tmp=tmp), generation_id="psm-g1",
                                   now=PUBLISHED)
        assert result.status == "published", result.detail
        population, capture, baskets, central = route_mod.capture_sector_join(root)
    else:
        root = tmp
        population, capture, baskets, central = synthetic_capture()
    return {"root": root, "population": population, "capture": capture,
            "baskets": baskets, "central": central}


@pytest.fixture(scope="module")
def real_index():
    return json.loads((REPO / "site/prophet/index.json").read_bytes())


def _join(real, index, **overrides):
    return engine.SectorMembersJoin(
        population=real["population"], capture=real["capture"], index=index,
        index_sha256="a" * 64, baskets=real["baskets"], central=real["central"],
        observations=overrides.pop("observations", None),
        captured_at="2026-11-10T00:00:00Z", **overrides)


def _plan(asset, *, closed, direction="BULL", signal="2026-10-20",
          formation="2026-10-16", strategy="core", phase="pre_trigger"):
    return {"id": f"{asset}-{direction}-{formation.replace('-', '')}",
            "asset": asset, "closed": closed, "direction": direction,
            "strategy": strategy, "phase": phase,
            "signal_date": signal, "formation_date": formation}


def _book(*plans, asof=SESSION):
    return {"schema": "prophet.index/v1", "asof": asof,
            "computed_at": "2026-11-07T02:00:00Z", "source_mixed_vintage": False,
            "plans": list(plans)}


def _rows_of(real, group_id=GROUP):
    return [r for r in real["population"].rows if r["group_id"] == group_id]


def _member_symbol(real, group_id=GROUP):
    return _rows_of(real, group_id)[0]["symbol"]


def _row(real, symbol, group_id=GROUP):
    for row in _rows_of(real, group_id):
        if engine.normalize_ticker(row["symbol"]) == engine.normalize_ticker(symbol):
            return row
    raise AssertionError(f"{symbol} not in {group_id}")


# --- envelope, disclosure, compatibility -----------------------------------------


def test_index_view_envelope_and_group_invariants(real_join):
    view = _join(real_join, _book()).index_view()
    assert view["schema"] == engine.SCHEMA and view["mode"] == "index"
    assert view["disclosure"]["join_key"] == "us_listing_ticker"
    assert view["disclosure"]["descriptive_only"] is True
    ids = [g["id"] for g in view["groups"]]
    assert ids == sorted(ids)
    for group in view["groups"]:
        counts = group["counts"]
        assert counts["configured"] == (counts["served"] + counts["accounted_unserved"]
                                        + counts["unaccounted"])
        assert sum(counts[k] for k in STATE_KEYS) == counts["served"]
        assert group["kind"] == "basket"  # amendment A1-8: no sector roster exists
    totals = view["totals"]
    assert sum(totals[k] for k in STATE_KEYS) == totals["served"]
    assert totals["configured"] == totals["served"] + totals["accounted_unserved"] \
        + totals["unaccounted"]


def test_totals_deduplicate_by_symbol_across_groups(real_join):
    view = _join(real_join, _book()).index_view()
    pair_served = sum(g["counts"]["served"] for g in view["groups"])
    assert view["totals"]["served"] < pair_served  # pairs > distinct symbols (1020 vs 698)
    assert view["totals"]["served"] == len({engine.normalize_ticker(r["symbol"])
                                            for r in real_join["population"].rows})


def test_compatibility_mixed_basis_on_stale_qualification(real_join):
    # READS age truthfully: the fixture publishes at the session evening, the
    # capture reads at real now, so qualification reads stale and the 3-calendar-day
    # gap upgrades to mixed_basis (amendment A1-7).
    compat = _join(real_join, _book(asof="2026-11-09")).compatibility()
    assert compat["sector_session"] == SESSION
    assert compat["session_gap"] == 3
    assert compat["status"] == "mixed_basis"
    assert "non-accepted basis" in compat["reason"]


def test_compatibility_plain_drift_without_owner_flag_stays_stale(real_join):
    join = _join(real_join, _book(asof="2026-11-09"))
    join.capture["qualification"] = "accepted"
    compat = join.compatibility()
    assert compat["status"] == "stale_sector" and compat["session_gap"] == 3


def test_compatibility_compatible_when_sessions_and_owners_agree(real_join):
    join = _join(real_join, _book())
    join.capture["qualification"] = "accepted"
    assert join.compatibility()["status"] == "compatible"


def test_compatibility_fail_closed_when_either_owner_missing(real_join):
    empty = _join(real_join, None)
    assert empty.compatibility()["status"] == "prophet_unavailable"
    assert empty.prophet_ref() is None
    no_sector = engine.SectorMembersJoin(
        population=type("P", (), {"groups": (), "rows": (), "unserved": (),
                                  "industry_classification": {},
                                  "sub_industry_classification": {}})(),
        capture={}, index=_book(), index_sha256="a" * 64, captured_at="x")
    assert no_sector.compatibility()["status"] == "sector_unavailable"
    assert no_sector.sector_ref() is None


def test_prophet_unavailable_marks_every_member(real_join):
    view = _join(real_join, None).group_view(GROUP, limit=200)
    assert view and all(m["prophet"]["state"] == "unavailable"
                        and m["prophet"]["reason"] == engine.REASON_PROPHET_UNAVAILABLE
                        for m in view["members"])
    assert view["counts"]["unavailable"] == view["counts"]["served"]
    # A3-1: the wire types both plan counts as integers; the Terminal decoder
    # refuses null, so an unavailable member carries 0 beside its state+reason.
    for member in view["members"]:
        assert member["prophet"]["open_plan_count"] == 0
        assert member["prophet"]["resolved_plan_count"] == 0
        assert member["prophet"]["plan"] is None


# --- Prophet state precedence and plan block --------------------------------------


def test_state_precedence_open_over_observation_and_resolved(real_join):
    symbol = _member_symbol(real_join)
    join = _join(real_join, _book(_plan(symbol, closed=False),
                                  _plan(symbol, closed=True)),
                 observations={symbol: {"kind": "turn_watch", "asof": SESSION}})
    state = join.member(_row(real_join, symbol))["prophet"]
    assert state["state"] == "open_plan"
    assert state["plan"]["id"] == f"{symbol}-BULL-20261016"
    assert state["open_plan_count"] == 1 and state["resolved_plan_count"] == 1


def test_state_precedence_observation_over_resolved(real_join):
    symbol = _member_symbol(real_join)
    join = _join(real_join, _book(_plan(symbol, closed=True)),
                 observations={symbol: {"kind": "turn_watch", "asof": SESSION}})
    state = join.member(_row(real_join, symbol))["prophet"]
    assert state["state"] == "early_observation"
    assert state["observation"] == {"kind": "turn_watch", "asof": SESSION}


def test_state_precedence_resolved_then_none(real_join):
    symbol = _member_symbol(real_join)
    row = _row(real_join, symbol)
    resolved = _join(real_join, _book(_plan(symbol, closed=True)))
    assert resolved.member(row)["prophet"]["state"] == "resolved_plan"
    state = _join(real_join, _book()).member(row)["prophet"]
    assert state["state"] == "none" and state["reason"] == engine.REASON_NO_PLAN


def test_plan_block_closed_mapping_and_honest_nulls(real_join):
    symbol = _member_symbol(real_join)
    join = _join(real_join, _book(
        _plan(symbol, closed=False, direction="BEAR", signal=None, formation="2026-09-01"),
        _plan(symbol, closed=True, direction="SIDEWAYS")))
    plan = join.member(_row(real_join, symbol))["prophet"]["plan"]
    assert plan["direction"] == "short"          # BULL→long, BEAR→short (A1-2)
    assert plan["opened_on"] == "2026-09-01"     # signal_date fallback formation_date (A1-3)
    assert plan["resolved_on"] is None and plan["outcome"] is None  # ledger never read


def test_digest_index_counts_joined_rows_not_header(real_index):
    book = engine.digest_index(real_index)
    assert book["plan_count"] == len(real_index["plans"]) \
        == sum(len(v) for v in book["plans"].values())
    assert book["open_plan_count"] == sum(1 for p in real_index["plans"]
                                          if p.get("closed") is False)
    assert book["skipped_rows"] == 0


def test_digest_index_skips_unusable_rows_without_guessing():
    book = engine.digest_index(_book({"id": "x"}, {"asset": "  ", "closed": False}))
    assert book["skipped_rows"] == 2 and book["plan_count"] == 0


def test_normalize_ticker_is_the_shared_join_key():
    assert engine.normalize_ticker(" carr ") == "CARR"
    assert engine.normalize_ticker(None) == "" and engine.normalize_ticker(0) == ""


# --- group mode: search before paging, sort, unknown group ------------------------


def test_group_view_search_filters_before_paging(real_join):
    view = _join(real_join, _book()).group_view(GROUP, query="carr")
    assert view["page"]["q"] == "carr" and view["page"]["total_matching"] < view["counts"]["served"]
    assert view["members"] and all("CARR" in m["symbol"].upper() for m in view["members"])
    # counts describe the WHOLE group, independent of q/state/paging
    assert sum(view["counts"][k] for k in STATE_KEYS) == view["counts"]["served"]


def test_group_view_state_filter_and_deterministic_sort(real_join, real_index):
    join = _join(real_join, real_index)  # the real 893-plan book: mixed states
    view = join.group_view(GROUP, state="open_plan", limit=200)
    assert view["members"] and all(m["prophet"]["state"] == "open_plan" for m in view["members"])
    assert view == join.group_view(GROUP, state="open_plan", limit=200)  # deterministic
    full = join.group_view(GROUP, limit=200)
    ranks = [engine.STATE_RANK[m["prophet"]["state"]] for m in full["members"]]
    assert ranks == sorted(ranks)  # state rank first, then symbol (the sort contract)
    # q + state compose: search before state filter before paging
    both = join.group_view(GROUP, query="carr", state="open_plan")
    assert both["page"]["q"] == "carr" and both["page"]["state"] == "open_plan"


def test_group_view_paging_shape(real_join):
    join = _join(real_join, _book())
    first = join.group_view(GROUP, offset=0, limit=10)
    second = join.group_view(GROUP, offset=10, limit=10)
    assert first["page"]["next_offset"] == 10
    assert len(first["members"]) == 10 and len(second["members"]) == 10
    assert [m["symbol"] for m in first["members"]] != [m["symbol"] for m in second["members"]]


def test_group_view_unknown_group_is_none(real_join):
    assert _join(real_join, _book()).group_view("no_such_group") is None


def test_group_view_unserved_listed_with_owner_reasons(real_join):
    view = _join(real_join, _book()).group_view("defensives")
    assert view["counts"]["accounted_unserved"] + view["counts"]["unaccounted"] \
        == len(view["unserved"])
    assert all(u["reason"] for u in view["unserved"])  # never dropped silently


# --- symbol mode ------------------------------------------------------------------


def test_symbol_view_memberships_and_top_level_state(real_join):
    join = _join(real_join, _book(_plan("CARR", closed=False)))
    view = join.symbol_view("carr")  # normalised on both sides
    assert view["symbol"] == "CARR"
    ids = [m["group"]["id"] for m in view["member_of"]]
    assert ids == sorted(ids) and "us_sector_industrials" in ids
    assert view["prophet"]["state"] == "open_plan"
    member = next(m["member"] for m in view["member_of"]
                  if m["group"]["id"] == "us_sector_industrials")
    assert member["also_in_groups"] == sorted(set(ids) - {"us_sector_industrials"})


def test_symbol_view_unknown_symbol_is_an_empty_membership(real_join):
    view = _join(real_join, _book()).symbol_view("ZZZZZZ")
    assert view["member_of"] == []
    assert view["prophet"]["state"] == "none"


# --- PIT membership basis (merged lane-1 shape) and degradation --------------------


def test_membership_basis_pit_when_first_known_carried(real_join):
    join = _join(real_join, _book())
    assert join.membership_basis() == engine.MEMBERSHIP_BASIS_PIT
    view = join.group_view(GROUP, limit=200)
    assert view["disclosure"]["membership_basis"] == "current_roster_with_pit_first_known"
    carried = real_join["population"].first_known["groups"][GROUP]
    assert any(m["first_known"] for m in view["members"])
    for member in view["members"]:
        # first_known is the PIT lower bound per pair; member_since stays the
        # roster's effective_on — two different clocks, both verbatim (A1-10).
        assert member["first_known"] == carried.get(member["symbol"])
        assert member["member_since"] is None or len(member["member_since"]) == 10


def test_membership_basis_degrades_when_pit_blocks_absent(tmp_path):
    if LANE1:
        # The lane-1 BASE shape: same real bundle, only the two PIT carried blocks removed.
        src = tmp_path / "pre-pit"
        src.mkdir()
        raw, identity = _real_bundle(tmp=src, carried=False)
        central = json.loads(raw["sectordata/sector_central.json"])
        carried = _real_carry_blocks()
        carried.pop("membership_first_known", None)
        carried.pop("membership_snapshots", None)
        central["carried"] = carried
        raw["sectordata/sector_central.json"] = json.dumps(
            central, separators=(",", ":"), ensure_ascii=False).encode()
        _, result, root = _publish(tmp_path, (raw, identity), generation_id="psm-prepit",
                                   now=PUBLISHED)
        assert result.status == "published", result.detail
        population, capture, baskets, central_doc = route_mod.capture_sector_join(root)
    else:
        population, capture, baskets, central_doc = synthetic_capture(pit=False)
    join = engine.SectorMembersJoin(
        population=population, capture=capture, index=_book(), index_sha256="a" * 64,
        baskets=baskets, central=central_doc, captured_at="2026-11-10T00:00:00Z")
    assert join.membership_basis() == engine.MEMBERSHIP_BASIS_CURRENT
    view = join.group_view(GROUP, limit=200)
    assert view["disclosure"]["membership_basis"] == "current_roster_not_point_in_time"
    assert all(m["first_known"] is None for m in view["members"])


# --- residual accounting on a fake population (owner gap, reported not dropped) ---


class _FakePopulation:
    groups = ({"group_id": "g1", "n_configured_current": 3, "name": "G1", "name_zh": None},)
    rows = ({"group_id": "g1", "symbol": "AAA", "name": "Alpha", "industry": None,
             "sub_industry": None, "membership": {"effective_on": "2024-01-01"}},)
    unserved = ({"group_id": "g1", "symbol": "BBB", "reason": "absent_from_price_panel"},)
    configured_current = 3
    served = 1
    unaccounted = 0
    industry_classification = {"status": "unavailable", "reason": "not_produced"}
    sub_industry_classification = {"status": "unavailable", "reason": "not_produced"}


def test_residual_configured_member_is_counted_not_dropped():
    join = engine.SectorMembersJoin(
        population=_FakePopulation(),
        capture={"generation_id": "g", "source_session": SESSION, "qualification": "accepted"},
        index=_book(_plan("AAA", closed=False)), index_sha256="a" * 64, captured_at="x")
    counts = join.group_view("g1")["counts"]
    assert counts["configured"] == 3 and counts["served"] == 1
    assert counts["accounted_unserved"] == 1 and counts["unaccounted"] == 1  # the residual
    assert counts["configured"] == sum(counts[k] for k in
                                       ("served", "accounted_unserved", "unaccounted"))
    unserved = join.group_view("g1")["unserved"]
    assert unserved == [{"symbol": "BBB", "reason": "absent_from_price_panel"}]


# --- P3 non-interference -----------------------------------------------------------


def test_join_never_mutates_the_parsed_index(real_join, real_index):
    pristine = copy.deepcopy(real_index)
    join = engine.SectorMembersJoin(
        population=real_join["population"], capture=real_join["capture"],
        index=real_index, index_sha256="a" * 64, baskets=real_join["baskets"],
        central=real_join["central"], captured_at="x")
    join.index_view()
    join.group_view(GROUP, limit=200)
    join.symbol_view("CARR")
    assert real_index == pristine  # parse → join → views leaves the book untouched
    # Plan order is the owner's own: per asset, the digest preserves the index's
    # file order (no re-ranking, no re-sorting anywhere in the join).
    file_order: dict[str, list[str]] = {}
    for row in real_index["plans"]:
        asset = engine.normalize_ticker(row.get("asset"))
        if asset:
            file_order.setdefault(asset, []).append(row["id"])
    assert set(join.book["plans"]) == set(file_order)
    for asset, expected in file_order.items():
        assert [p["id"] for p in join.book["plans"][asset]] == expected


_REPO_ROOTS = ("app", "lib", "engine", "scripts", "collectors")


def _repo_closure(entry: Path) -> set[str]:
    """Repo-local import closure of ``entry`` (AST walk, no execution)."""
    seen: set[Path] = set()
    queue = [entry]
    modules: set[str] = set()
    while queue:
        path = queue.pop()
        if path in seen:
            continue
        seen.add(path)
        try:
            tree = ast.parse(path.read_text())
        except (OSError, SyntaxError):
            continue
        names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names
                             if alias.name.split(".")[0] in _REPO_ROOTS)
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level \
                    and node.module.split(".")[0] in _REPO_ROOTS:
                names.append(node.module)
        for name in names:
            modules.add(name)
            for candidate in (REPO / (name.replace(".", "/") + ".py"),
                              REPO / (name.replace(".", "/") + "/__init__.py")):
                if candidate.exists():
                    queue.append(candidate)
    return modules


def test_build_prophet_decision_path_never_imports_the_join():
    # P3: scripts/build_prophet.py (the Prophet decision path) must not import
    # this join, directly or transitively — descriptive context cannot become a
    # plan input by accident of import order.
    closure = _repo_closure(REPO / "scripts/build_prophet.py")
    assert "engine.prophet_sector_members" not in closure
    assert "app.prophet_sector_members" not in closure


def test_engine_module_is_pure_no_io():
    source = (REPO / "engine/prophet_sector_members.py").read_text()
    assert "open(" not in source and "import os" not in source  # no reads, no writes
