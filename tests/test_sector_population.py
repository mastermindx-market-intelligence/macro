"""Full group-membership population: SP01 (one capture per read) and SP02 (beyond page one).

REAL vs FIXTURE, stated exactly
-------------------------------
REAL    The five Sector member documents are the committed producer artifacts under
        ``site/`` (session 2026-11-06): 49 baskets, 1,015 member rows, 698 distinct
        symbols. ``action_board.json`` is rewritten through the ordinary producer
        writer (``scripts.build_sector_action_board.write_action_board``) from the
        real committed board, because the committed file still carries one legacy
        ``NaN`` literal the strict decoder refuses - no post-hoc scrub is applied.
        The bytes are published through the REAL private-store publisher into an
        isolated temporary store and read through the REAL reader, route and the
        incumbent regwall/paywall gates.
FIXTURE (a) the two Supabase identity seams (``gates`` fixture - the same local
        auth equivalent the sibling suites document); (b) the "advanced"
        generation ``g2`` used for SP01 is the real bytes with ONE real member
        removed from one real basket (board re-bound to the new basket hash by the
        ordinary writer) - a derived generation, not a nightly publication;
        (c) the clock is injected. Nothing here asserts live-host acceptance.
"""
from __future__ import annotations

from datetime import datetime, timezone
import copy
import json
from pathlib import Path
import re
import shutil

import pytest

from app import sector_generation as api
from app.sector_generation_reader import SectorGenerationReader
from lib import sector_generation_contract as contract
from lib import sector_generation_wire as wire
from lib import sector_population as population
from scripts import build_sector_action_board as board_writer
from tests.test_sector_generation_reader import _client, _publish, gates  # noqa: F401

REPO = Path(__file__).resolve().parents[1]
SESSION = "2026-11-06"
PUBLISHED = datetime(2026, 11, 6, 23, tzinfo=timezone.utc)
MEMBERS = contract.SECTOR_GENERATION_MEMBERS
COOKIE = {"sb-fixture-auth-token": "fixture"}
URL = "/api/sector-generation/population"


def _real(name: str) -> bytes:
    return (REPO / "site" / name).read_bytes()


from functools import lru_cache  # noqa: E402


@lru_cache(maxsize=1)
def _cached_real_carry() -> dict:
    """The real-input `carried` dict, built ONCE per process (same real quadruple
    every caller uses; the two PIT blocks each cost one owner store read).

    MUST NOT be called under a point-in-time monkeypatch (a patched PIT store,
    membership path or history path): the cache is process-wide and is never
    invalidated, so one patched call would poison every later caller in the same
    process with the patched store's answers. Under any such monkeypatch, build a
    fresh carry directly instead of using this cache (N6)."""
    from lib.sector_central_carry import build_carry
    from collectors.sponsors import sector_flow_periods
    central = json.loads(_real("sectordata/sector_central.json"))
    roster = json.loads((REPO / "data/baskets/membership.json").read_text())
    return build_carry(REPO / "site", central, roster, sector_flow_periods())


def _real_carry_blocks() -> dict:
    """A deep copy of the cached real carry, so no caller can poison another."""
    return copy.deepcopy(_cached_real_carry())


def _real_bundle(*, drop_member: tuple[str, str] | None = None, tmp: Path,
                 carried: bool = True, refuse_group: str | None = None,
                 vanish_group: str | None = None, effective_as_of: str | None = None):
    """Real bytes -> (member bytes, identity); optionally derive an advanced generation.

    ``refuse_group`` (FIXTURE derivation of real bytes) moves one real basket out of
    ``baskets[]`` into ``observation_refusals`` exactly as ``engine/baskets.py:217-228``
    does when a basket falls below the owner's coverage floor. ``vanish_group`` (R3-S1)
    removes the basket from ``baskets[]`` with NO refusal entry - the producer's
    ``lvl.dropna().empty`` exit or any other unexplained drop - while the carried
    owner roster still names it, exactly as a nightly divergence would leave it.
    ``effective_as_of`` (R4-N4) rewrites every observation's effective session in the
    derived capture while the carried roster block stays cut at the real 2026-11-06 -
    a capture whose own clock disagrees with the roster that must vouch for it.
    """
    baskets_raw = _real("basketdata/baskets.json")
    if (drop_member is not None or refuse_group is not None or vanish_group is not None
            or effective_as_of is not None):
        baskets = json.loads(baskets_raw)
        if effective_as_of is not None:
            for group in baskets["baskets"]:
                group["observation"]["effective_as_of"] = effective_as_of
            for refusal in baskets["observation_refusals"]:
                refusal["observation"]["effective_as_of"] = effective_as_of
        if drop_member is not None:
            group = next(g for g in baskets["baskets"] if g["id"] == drop_member[0])
            group["members"] = [m for m in group["members"] if m["symbol"] != drop_member[1]]
            group["n_members"] = len(group["members"])
        if refuse_group is not None:
            group = next(g for g in baskets["baskets"] if g["id"] == refuse_group)
            baskets["baskets"] = [g for g in baskets["baskets"] if g["id"] != refuse_group]
            baskets["observation_refusals"].append(
                {"basket_id": refuse_group, "observation": group["observation"]})
        if vanish_group is not None:
            baskets["baskets"] = [g for g in baskets["baskets"] if g["id"] != vanish_group]
        baskets_raw = json.dumps(baskets, separators=(",", ":"), ensure_ascii=False).encode()
    committed = json.loads(_real("basketdata/action_board.json"), parse_constant=float)
    baskets_path = tmp / "baskets.json"
    baskets_path.write_bytes(baskets_raw)
    out = tmp / "action_board.json"
    board_writer.write_action_board(
        out, baskets_path=baskets_path, action_board=committed["action_board"],
        generated_utc="2026-11-06T22:00:00Z")  # committed file is a bare legacy envelope
    central = json.loads(_real("sectordata/sector_central.json"))
    if carried:
        # The committed sector_central.json predates the carry step; produce the
        # `carried` key with the NEW builder function over the real committed
        # artifacts (REAL inputs, new code) exactly as build_sector_central does.
        central["carried"] = _real_carry_blocks()
    raw = {
        MEMBERS[0]: json.dumps(central, separators=(",", ":"), ensure_ascii=False).encode(),
        MEMBERS[1]: _real("sectordata/sector_cycles.json"),
        MEMBERS[2]: baskets_raw,
        MEMBERS[3]: _real("basketdata/si_handoff.json"),
        MEMBERS[4]: out.read_bytes(),
    }
    identity = {"sector_view": {
        "schema": "sector.view_inputs.v1", "source_session": SESSION,
        "input_version": "sector-inputs-v1", "baseline_session": None,
        "source_qualification": "accepted"}}
    return raw, identity


@pytest.fixture
def real_store(tmp_path):
    bundle = _real_bundle(tmp=tmp_path)
    orch, first, root = _publish(tmp_path, bundle, generation_id="real-g1", now=PUBLISHED)
    assert first.status == "published", first.detail
    reader = SectorGenerationReader(generations_root=root, clock=lambda: PUBLISHED)
    return {"tmp": tmp_path, "root": root, "reader": reader, "first": first}


def _advance(store):
    """Publish the derived g2 (one real member removed) and select it."""
    sub = store["tmp"] / "g2"
    sub.mkdir()
    # first real basket with >1 member; remove its last member
    baskets = json.loads(_real("basketdata/baskets.json"))
    group = next(g for g in baskets["baskets"] if len(g["members"]) > 2)
    gone = group["members"][-1]["symbol"]
    bundle = _real_bundle(drop_member=(group["id"], gone), tmp=sub)
    _, second, _ = _publish(store["tmp"], bundle, generation_id="real-g2",
                            expected=store["first"].content_id, now=PUBLISHED)
    assert second.status == "published", second.detail
    return group["id"], gone, second


def _all_pages(client, **params):
    pages, cursor = [], None
    while True:
        query = {"audience": "entitled", "limit": "100", **params}
        if cursor:
            query["cursor"] = cursor
        response = client.get(URL, params=query, cookies=COOKIE)
        assert response.status_code == 200, response.text
        page = response.json()["page"]
        pages.append((response, page))
        cursor = page["next_cursor"]
        if cursor is None:
            return pages


def test_real_population_is_full_ordered_joined_and_bounded(real_store):
    baskets = json.loads(_real("basketdata/baskets.json"))
    expected_rows = sum(len(g["members"]) for g in baskets["baskets"])
    assert (len(baskets["baskets"]), expected_rows) == (49, 1015)  # real census
    client = _client(real_store["reader"])
    pages = _all_pages(client)
    assert len(pages) == 11  # 1,015 rows at 100/page: more than one page by design
    rows = [row for _, page in pages for row in page["rows"]]
    assert [r["ordinal"] for r in rows] == list(range(1015))
    assert len({r["symbol"] for r in rows}) == 698
    names = {g["id"]: g for g in baskets["baskets"]}
    for _, page in pages:
        by_id = {g["group_id"]: g for g in page["groups"]}
        for row in page["rows"]:
            joined = by_id[row["group_id"]]  # every row joins to a group on ITS page
            assert joined["name"] == names[row["group_id"]]["name"]
    for response, page in pages:
        assert len(response.content) <= wire.MAX_ENCODED_BYTES
        assert response.headers["cache-control"] == "private, no-store"
        assert page["total_matching"] == 1015
    # F1: the denominator is the owner's configured CURRENT roster (configured minus
    # removed = 1046 - 26 = 1020). 1,015 are served; the 5 current members with no row
    # are identified, each with a closed reason; nothing is unaccounted. Counts computed.
    pop = pages[0][1]["capture"]["population"]
    assert (pop["configured_current"], pop["served"], pop["accounted_unserved"],
            pop["unaccounted"], pop["complete"]) == (1020, 1015, 5, 0, True)
    # Independent check of the denominator straight from the owner's roster file:
    # configured minus removed, per group, equals served + unserved exactly.
    roster = json.loads((REPO / "data/baskets/membership.json").read_text())["baskets"]
    by_group = {}
    for row in rows:
        by_group.setdefault(row["group_id"], set()).add(row["symbol"])
    for u in pop["unserved_members"]:
        by_group.setdefault(u["group_id"], set()).add(u["symbol"])
    expected_roster = {gid: {m["ticker"] for m in g["members"] if not m.get("removed")}
                       for gid, g in roster.items()}
    assert by_group == expected_roster
    assert sum(len(v) for v in expected_roster.values()) == pop["configured_current"]
    assert sorted((u["group_id"], u["symbol"], u["reason"]) for u in pop["unserved_members"]) == [
        ("defensives", "KVUE", "not_observed_at_effective_as_of"),
        ("regional_banks", "WBS", "not_observed_at_effective_as_of"),
        ("us_sector_comm", "PSKY", "not_observed_at_effective_as_of"),
        ("us_sector_comm", "WBD", "not_observed_at_effective_as_of"),
        ("us_sector_staples", "KVUE", "not_observed_at_effective_as_of")]
    # Removed members are reported separately (with their removal date): never listed,
    # never "missing". GATO/MAG are among the 26.
    removed = pop["removed_members"]
    assert removed["status"] == "available" and removed["n"] == 26
    by_symbol = {(r["group_id"], r["symbol"]): r["removed_on"] for r in removed["members"]}
    assert by_symbol[("silver_miners", "GATO")] == "2025-01-16"
    assert by_symbol[("silver_miners", "MAG")] == "2025-09-04"
    served = {(r["group_id"], r["symbol"]) for r in rows}
    assert not (served & set(by_symbol))
    assert not (served & {(u["group_id"], u["symbol"]) for u in pop["unserved_members"]})
    assert "missing" not in pop and "expected" not in pop and "admitted" not in pop
    # Prophet eligibility is a separate, honestly unproduced concept.
    assert {json.dumps(r["prophet_eligibility"], sort_keys=True) for r in rows} == {
        '{"reason": "not_produced", "status": "unavailable"}'}
    assert not re.search(r"\bNaN\b|Infinity", "".join(r.text for r, _ in pages))


def test_industry_is_current_basis_not_point_in_time_and_never_relabelled(real_store):
    """REAL inputs, NEW carry code: every row carries a labelled industry state."""
    client = _client(real_store["reader"])
    pages = _all_pages(client)
    identity = pages[0][1]["capture"]["identity"]
    gics, sub = identity["industry_classification"], identity["sub_industry_classification"]
    # Two SEPARATE taxonomies, each with its own source, as-of and basis label.
    assert (gics["status"], gics["point_in_time"], gics["taxonomy"]) == (
        "available", False, "gics_industry")
    assert gics["basis"] == "current_gics_industry_not_point_in_time"
    assert gics["source"] == "stagedata/screener.json" and gics["as_of"] == "2026-11-09"
    assert (sub["status"], sub["point_in_time"]) == ("available", False)
    assert sub["basis"] == "current_sp500_membership_not_point_in_time"
    assert sub["source"] == "marketdata/subsector_confluence.json" and sub["as_of"] == "2026-11-06"
    rows = [r for _, p in pages for r in p["rows"]]
    gics_symbols = {r["symbol"] for r in rows if r["industry"]["status"] == "available"}
    sub_symbols = {r["symbol"] for r in rows if r["sub_industry"]["status"] == "available"}
    assert (len(gics_symbols), len(sub_symbols)) == (617, 424)  # real coverage of 698 symbols
    app_row = next(r for r in rows if r["symbol"] == "APP")
    assert app_row["sub_industry"]["key"] == "software-application"
    assert app_row["sub_industry"]["label"] == "Software - Application"
    assert app_row["industry"]["label"] == next(
        x["industry"] for x in json.loads(_real("stagedata/screener.json"))["rows"]
        if x["ticker"] == "APP")
    assert "key" not in app_row["industry"]  # never merged into the sub-industry shape
    assert all(r["industry"] == {"status": "unavailable", "reason": "not_in_current_classification"}
               for r in rows if r["symbol"] not in gics_symbols)
    # ONE taxonomy stamp (Part B 3): the labels are current-basis and the historical
    # revision is unavailable because no point-in-time classification source exists.
    assert identity["taxonomy_revision"] == {
        "status": "unavailable", "reason": "no_point_in_time_classification_source",
        "labels_basis": "current_not_point_in_time",
        "labels": ["industry", "sub_industry"]}
    # Original affiliation stays honestly unproduced (no source on this base).
    assert identity["original_affiliation_set"]["status"] == "unavailable"


def test_sp02_member_beyond_page_one_is_reachable_and_correctly_joined(real_store):
    client = _client(real_store["reader"])
    pages = _all_pages(client)
    first_page_symbols = {r["symbol"] for r in pages[0][1]["rows"]}
    late = pages[7][1]["rows"][3]  # ordinal 703: well beyond page one
    assert late["ordinal"] == 703
    assert late["symbol"] not in first_page_symbols or late["also_in_groups"] > 0
    # Found by search over the FULL population before paging, with limit=1.
    found = client.get(URL, params={"audience": "entitled", "limit": "1",
                                    "q": late["symbol"], "group": late["group_id"]},
                       cookies=COOKIE).json()["page"]
    assert found["total_matching"] == 1 and found["rows"][0]["ordinal"] == 703
    assert found["rows"][0] == late
    joined = found["groups"][0]
    baskets = json.loads(_real("basketdata/baskets.json"))
    real_group = next(g for g in baskets["baskets"] if g["id"] == late["group_id"])
    real_member = next(m for m in real_group["members"] if m["symbol"] == late["symbol"])
    assert joined["group_id"] == real_group["id"] and joined["name"] == real_group["name"]
    assert late["name"] == real_member["name"]
    assert late["membership"]["effective_on"] == real_member["added"]
    assert joined["n_members_listed"] == len(real_group["members"])
    # The action-board join is the real board's row for that group, or explicitly absent.
    board = json.loads(_real("basketdata/action_board.json"), parse_constant=float)["action_board"]
    lanes = {r["ticker"]: lane for lane in board
             if isinstance(board[lane], list) for r in board[lane] if r.get("kind") == "theme"}
    if joined["group_id"] in lanes:
        assert joined["action"]["status"] == "available"
        assert joined["action"]["lane"] == next(
            l for l in ("buy_now", "buy_soon", "on_the_run", "take_profits", "hold", "avoid")
            if any(r.get("ticker") == joined["group_id"] and r.get("kind") == "theme"
                   for r in board[l]))
    else:
        assert joined["action"] == {"status": "unavailable", "reason": "no_action_row"}
    # A symbol in several baskets is one membership per group, never merged or dropped.
    multi = next(r for _, p in pages for r in p["rows"] if r["also_in_groups"] > 0)
    hits = client.get(URL, params={"audience": "entitled", "limit": "200", "q": multi["symbol"]},
                      cookies=COOKIE).json()["page"]
    exact = [r for r in hits["rows"] if r["symbol"] == multi["symbol"]]  # q is a substring search
    assert len(exact) == multi["also_in_groups"] + 1
    assert len({r["group_id"] for r in exact}) == len(exact)


def test_sp01_reader_that_started_on_capture_x_finishes_on_x(real_store):
    client = _client(real_store["reader"])
    first = client.get(URL, params={"audience": "entitled", "limit": "100"},
                       cookies=COOKIE).json()["page"]
    capture_x = first["capture"]["owner_ref"]
    assert capture_x["generation_id"] == "real-g1" and first["capture"]["currentness"] == "selected_at_read"
    group, gone, _ = _advance(real_store)  # publication moves to g2 mid-read
    # A fresh page-1 read now starts on g2 (so the pointer really moved)...
    fresh = client.get(URL, params={"audience": "entitled", "limit": "1"},
                       cookies=COOKIE).json()["page"]
    assert fresh["capture"]["owner_ref"]["generation_id"] == "real-g2"
    assert fresh["total_matching"] == 1014
    # ...but the continuation of the reader that began on g1 stays on g1, entire.
    seen, cursor = list(first["rows"]), first["next_cursor"]
    while cursor:
        page = client.get(URL, params={"audience": "entitled", "limit": "100", "cursor": cursor},
                          cookies=COOKIE).json()["page"]
        assert page["capture"]["owner_ref"]["generation_id"] == "real-g1"
        assert page["capture"]["owner_ref"]["content_id"] == capture_x["content_id"]
        assert page["capture"]["currentness"] == "retained_original"
        seen.extend(page["rows"])
        cursor = page["next_cursor"]
    assert [r["ordinal"] for r in seen] == list(range(1015))  # all 1,015, none from g2's 1,014
    assert any(r["group_id"] == group and r["symbol"] == gone for r in seen)


def test_cursor_binding_change_is_an_explicit_reset_not_a_mixed_page(real_store):
    client = _client(real_store["reader"])
    first = client.get(URL, params={"audience": "entitled", "limit": "100"},
                       cookies=COOKIE).json()["page"]
    cursor = first["next_cursor"]
    base = {"audience": "entitled", "limit": "100", "cursor": cursor}
    for changed in ({"limit": "50"}, {"q": "A"}, {"group": "mag7"}):
        response = client.get(URL, params={**base, **changed}, cookies=COOKIE)
        assert response.status_code == 409
        assert response.json() == {"schema": "sector_generation.error/v1",
                                   "code": "CURSOR_RESET", "reason": "binding_changed"}
    # S1: a well-formed token whose signature is not recognised (forged OR minted by an
    # earlier key) is the explicit reset; only malformed grammar stays 400.
    tampered = cursor[:-1] + ("0" if cursor[-1] != "0" else "1")
    forged = client.get(URL, params={**base, "cursor": tampered}, cookies=COOKIE)
    assert forged.status_code == 409 and forged.json() == {
        "schema": "sector_generation.error/v1", "code": "CURSOR_RESET",
        "reason": "signature_unrecognised"}
    assert client.get(URL, params={**base, "cursor": "not a token"}, cookies=COOKIE).status_code == 400
    # A different actor cannot continue (or open the reference of) another actor's capture.
    import app.main as macro_main
    original = macro_main._mm_verify_uid_cached
    macro_main._mm_verify_uid_cached = lambda token: "22222222-2222-2222-2222-222222222222"
    try:
        other = client.get(URL, params=base, cookies=COOKIE)
        other_ref = client.get(URL, params={"audience": "entitled",
                                            "cursor": first["context_ref"]}, cookies=COOKIE)
    finally:
        macro_main._mm_verify_uid_cached = original
    assert other.status_code == 409 and other.json()["reason"] == "binding_changed"
    # S3(e): the context reference is actor-bound too.
    assert other_ref.status_code == 409 and other_ref.json()["reason"] == "binding_changed"


def test_restart_or_key_change_answers_reset_not_invalid_and_discloses_nothing(real_store):
    """S1: the stale-key answer is the reset/unavailable class, byte-identical to forged."""
    client = _client(real_store["reader"])
    first = client.get(URL, params={"audience": "entitled", "limit": "100"},
                       cookies=COOKIE).json()["page"]
    old_key = population._PROCESS_KEY
    population._PROCESS_KEY = b"\x07" * 32  # a restart / another worker's key
    try:
        stale = client.get(URL, params={"audience": "entitled", "limit": "100",
                                        "cursor": first["next_cursor"]}, cookies=COOKIE)
        stale_ref = client.get(URL, params={"audience": "entitled",
                                            "cursor": first["context_ref"]}, cookies=COOKIE)
    finally:
        population._PROCESS_KEY = old_key
    assert stale.status_code == 409 and stale.json() == {
        "schema": "sector_generation.error/v1", "code": "CURSOR_RESET",
        "reason": "signature_unrecognised"}
    assert stale_ref.status_code == 404 and stale_ref.json() == {
        "schema": "sector_generation.error/v1", "code": "ORIGINAL_UNAVAILABLE"}
    for response in (stale, stale_ref):
        assert response.headers["cache-control"] == "private, no-store"
        assert "real-g1" not in response.text


def test_resolver_ref_durability_is_stated_never_assumed(real_store, monkeypatch):
    """S2: the reference says whether it survives a restart."""
    client = _client(real_store["reader"])
    monkeypatch.delenv("SECTOR_GENERATION_CURSOR_SECRET", raising=False)
    page = client.get(URL, params={"audience": "entitled", "limit": "1"},
                      cookies=COOKIE).json()["page"]
    assert page["capture"]["owner_ref"]["retained_resolver_ref_durability"] == "process_lifetime_only"
    monkeypatch.setenv("SECTOR_GENERATION_CURSOR_SECRET", "s" * 40)
    page = client.get(URL, params={"audience": "entitled", "limit": "1"},
                      cookies=COOKIE).json()["page"]
    assert page["capture"]["owner_ref"]["retained_resolver_ref_durability"] == "durable"
    # With a provisioned secret the tokens survive a process-key change.
    old_key = population._PROCESS_KEY
    population._PROCESS_KEY = b"\x09" * 32
    try:
        again = client.get(URL, params={"audience": "entitled", "limit": "1",
                                        "cursor": page["context_ref"]}, cookies=COOKIE)
    finally:
        population._PROCESS_KEY = old_key
    assert again.status_code == 200


@pytest.mark.parametrize("secret", ["", "short", "x" * 31])
def test_short_or_empty_secret_fails_closed_on_mint_and_open(real_store, monkeypatch, secret):
    """S3(b): never a silent weak key."""
    client = _client(real_store["reader"])
    monkeypatch.setenv("SECTOR_GENERATION_CURSOR_SECRET", secret)
    mint = client.get(URL, params={"audience": "entitled", "limit": "100"}, cookies=COOKIE)
    assert mint.status_code == 503 and mint.json()["code"] == "SECTOR_GENERATION_UNAVAILABLE"
    open_ = client.get(URL, params={"audience": "entitled", "cursor": "e30.%s" % ("0" * 64)},
                       cookies=COOKIE)
    assert open_.status_code == 503
    for response in (mint, open_):
        assert response.headers["cache-control"] == "private, no-store"


def test_duplicate_parameters_and_refusal_headers(real_store):
    """S3(c)(d): duplicates are refused and EVERY refusal is private/no-store."""
    client = _client(real_store["reader"])
    refusals = [
        client.get(URL + "?audience=entitled&audience=entitled", cookies=COOKIE),
        client.get(URL + "?audience=entitled&limit=1&limit=2", cookies=COOKIE),
        client.get(URL + "?audience=entitled&q=a&q=b", cookies=COOKIE),
        client.get(URL + "?audience=entitled&cursor=a.b&cursor=c.d", cookies=COOKIE),
        client.get(URL, params={"audience": "preview"}, cookies=COOKIE),
        client.get(URL, params={"audience": "entitled", "generation": "real-g1"}, cookies=COOKIE),
        client.get(URL, params={"audience": "entitled"}),  # 401 from the incumbent gates
    ]
    assert [r.status_code for r in refusals] == [400, 400, 400, 400, 400, 400, 401]
    for response in refusals:
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["vary"] == "Cookie"
        assert response.headers["x-content-type-options"] == "nosniff"


def test_unverified_actor_is_refused_not_bound_to_a_shared_anonymous(real_store, monkeypatch):
    """N2: a caller with no verified user id never shares an 'anonymous' actor."""
    with pytest.raises(population.PopulationError):
        population.actor_digest("")
    with pytest.raises(population.PopulationError):
        population.actor_digest(None)
    client = _client(real_store["reader"])

    def unverified(transient):
        def raiser(request):
            raise api._ActorUnverified(transient)
        return raiser

    monkeypatch.setattr(api, "_actor_digest", unverified(False))  # no session token
    response = client.get(URL, params={"audience": "entitled"}, cookies=COOKIE)
    assert response.status_code == 401 and response.json()["code"] == "AUTHENTICATION_REQUIRED"
    assert response.headers["cache-control"] == "private, no-store"
    # R2-N8: a token the gates accepted but that no longer verifies is a transient
    # identity failure (503), not a login prompt.
    monkeypatch.setattr(api, "_actor_digest", unverified(True))
    transient = client.get(URL, params={"audience": "entitled"}, cookies=COOKIE)
    assert transient.status_code == 503 and transient.json()["code"] == "SERVICE_UNAVAILABLE"
    assert transient.headers["cache-control"] == "private, no-store"


def _synthetic(*, observation=None, members=("AAA", "BBB"), removed_roster=None):
    """FIXTURE: one tiny basket document for F1 accounting edge cases."""
    group = {"id": "g1", "name": "G", "members": [{"symbol": s, "name": s, "added": "2024-01-01"}
                                                  for s in members], "n_members": len(members)}
    if observation is not None:
        group["observation"] = observation
    return {"baskets": [group], "observation_refusals": []}


def _obs(configured, *, observed=None, panel_missing=(), asof_missing=(),
         effective_as_of=SESSION):
    """A captured observation. The effective session is stated (R4-N4): the real
    producer stamps it on every observation, live and refused alike."""
    return {"configured_members": list(configured),
            "observed_members": list(configured if observed is None else observed),
            "missing_columns": list(panel_missing), "missing_at_asof": list(asof_missing),
            "effective_as_of": effective_as_of}


def _roster_central(baskets: dict[str, list[str]], **carried_extra) -> dict:
    """FIXTURE central carrying the owner's roster block (R3-S1) - the document the
    central builder carries from ``data/baskets/membership.json``."""
    return {"carried": {"roster_baskets": {
        "source": "data/baskets/membership.json", "version": "t",
        "as_of": "2026-11-06", "baskets": baskets}, **carried_extra}}


def test_f1_completeness_is_computed_from_the_configured_roster(tmp_path):
    """FIXTURE: complete only when served + explicitly accounted == configured current."""
    def build(baskets, roster=None, central=None):
        if central is None:
            roster = ({g["id"]: list(g["observation"]["configured_members"])
                       for g in baskets["baskets"]
                       if isinstance(g.get("observation"), dict)}
                      if roster is None else roster)
            central = _roster_central(roster)
        return population.build_population(baskets=baskets, handoff={}, action_board={},
                                           central=central)
    # served == configured: complete
    ok = build(_synthetic(observation=_obs(["AAA", "BBB"])))
    assert (ok.configured_current, ok.served, len(ok.unserved), ok.complete) == (2, 2, 0, True)
    # a configured member with no row, explained by the owner: accounted, still complete
    accounted = build(_synthetic(observation=_obs(["AAA", "BBB", "CCC"], asof_missing=["CCC"])))
    assert [(u["symbol"], u["reason"]) for u in accounted.unserved] == [
        ("CCC", "not_observed_at_effective_as_of")]
    assert (accounted.configured_current, accounted.complete) == (3, True)
    panel = build(_synthetic(observation=_obs(["AAA", "BBB", "CCC"], panel_missing=["CCC"])))
    assert panel.unserved[0]["reason"] == "absent_from_price_panel"
    # a configured member the owner never explained: NOT complete
    silent = build(_synthetic(observation=_obs(["AAA", "BBB", "CCC"], observed=["AAA", "BBB"])))
    assert silent.unserved[0]["reason"] == "unaccounted_by_owner"
    assert (silent.unaccounted, silent.accounted_unserved, silent.complete) == (1, 0, False)
    # R2-B1: a member the owner OBSERVED with a price (observed_members keeps it) but that
    # is not served is a row lost after the owner's observation - NOT explained, NOT complete.
    lost = build(_synthetic(observation=_obs(["AAA", "BBB", "CCC"])))  # CCC observed, no row
    assert [(u["symbol"], u["reason"]) for u in lost.unserved] == [("CCC", "unaccounted_by_owner")]
    assert (lost.unaccounted, lost.accounted_unserved, lost.complete) == (1, 0, False)
    assert "empty_price_tape" not in population.UNSERVED_REASONS
    # a served row the roster does not configure: NOT complete
    extra = build(_synthetic(observation=_obs(["AAA"])))
    assert (extra.unaccounted, extra.complete) == (1, False)
    # no captured roster at all: completeness is UNKNOWN (None), never True
    unknown = build(_synthetic(observation=None))
    assert (unknown.configured_current, unknown.complete) == (None, None)
    # R3-S1: a roster basket absent from BOTH the live list and the refusals - its
    # members are unaccounted and complete is False, never silently out of the denominator
    vanished = build(_synthetic(observation=_obs(["AAA", "BBB"])),
                     roster={"g1": ["AAA", "BBB"], "gone": ["XXX", "YYY"]})
    assert (vanished.configured_current, vanished.served, vanished.unaccounted,
            vanished.complete) == (4, 2, 2, False)
    assert {(u["group_id"], u["symbol"], u["reason"]) for u in vanished.unserved
            if u["group_id"] == "gone"} == {("gone", s, "unaccounted_by_owner")
                                            for s in ("XXX", "YYY")}
    # R3-S1: a capture with NO roster block, or a malformed one, is UNKNOWN - the
    # roster is what makes `complete` verifiable, so it can never verify a `true`
    assert build(_synthetic(observation=_obs(["AAA", "BBB"])), central={}).complete is None
    for bad in ("x", 5, {}, {"as_of": "2026-11-06"}, {"as_of": "2026-11-06", "baskets": {}},
                {"as_of": "2026-11-06", "baskets": {"g1": ["AAA", "AAA"]}},
                {"as_of": "2026-11-06", "baskets": {"G 1": ["AAA"]}},
                {"as_of": "2026-11-06", "baskets": {"gone": [7]}},
                {"as_of": None, "baskets": {"gone": ["AAA"]}}):
        broken = build(_synthetic(observation=_obs(["AAA", "BBB"])),
                       central={"carried": {"roster_baskets": bad}})
        assert broken.complete is None and broken.configured_current is None, bad


def _store_from(tmp_path, **bundle):
    """Publish a (derived) real bundle into a fresh isolated store and return its client."""
    _, published, root = _publish(tmp_path, _real_bundle(tmp=tmp_path, **bundle),
                                  generation_id="derived", now=PUBLISHED)
    assert published.status == "published", published.detail
    return _client(SectorGenerationReader(generations_root=root, clock=lambda: PUBLISHED))


def test_r2_b1_real_route_a_lost_served_row_is_not_complete(tmp_path):
    """REAL bytes with ONE real served member (housing/CARR) dropped and the owner's
    captured observation left intact: the member was observed with a price, so it is a
    row lost after the owner's observation - the route must not call that complete."""
    client = _store_from(tmp_path, drop_member=("housing", "CARR"))
    pop = client.get(URL, params={"audience": "entitled", "limit": "1"},
                     cookies=COOKIE).json()["page"]["capture"]["population"]
    assert (pop["configured_current"], pop["served"]) == (1020, 1014)
    assert (pop["accounted_unserved"], pop["unaccounted"], pop["complete"]) == (5, 1, False)
    lost = [u for u in pop["unserved_members"] if u["reason"] == "unaccounted_by_owner"]
    assert lost == [{"group_id": "housing", "symbol": "CARR", "reason": "unaccounted_by_owner"}]
    assert all(u["reason"] != "empty_price_tape" for u in pop["unserved_members"])


def test_r2_b2_real_route_a_refused_basket_stays_in_the_denominator(tmp_path):
    """REAL bytes with the real `housing` basket (18 configured) moved into the owner's
    `observation_refusals` exactly as the producer does below its coverage floor."""
    client = _store_from(tmp_path, refuse_group="housing")
    page = client.get(URL, params={"audience": "entitled", "limit": "1", "group": "housing"},
                      cookies=COOKIE).json()["page"]
    pop = page["capture"]["population"]
    assert (pop["configured_current"], pop["served"], pop["accounted_unserved"],
            pop["unaccounted"]) == (1020, 997, 23, 0)  # 18 refused + the 5 unobserved
    refused = [u for u in pop["unserved_members"] if u["reason"] == "group_refused_by_owner_observation"]
    assert len(refused) == 18 and {u["group_id"] for u in refused} == {"housing"}
    assert pop["complete"] is True and "group_refused_by_owner_observation" in pop["unserved_reasons"]
    # the refusal is visible per group, even though the group has no served row
    group = next(g for g in page["groups"] if g["group_id"] == "housing")
    assert group["refused_by_owner"] is True and group["n_members_listed"] == 0
    assert group["n_configured_current"] == 18 and group["n_unserved"] == 18
    assert group["owner_observation_refusal"]["configured_n"] == 18
    assert len(group["unserved"]) == 18 and page["rows"] == []
    index = client.get(URL, params={"audience": "entitled", "limit": "1"},
                       cookies=COOKIE).json()["page"]["group_index"]
    assert next(g for g in index if g["group_id"] == "housing")["n_unserved"] == 18


def test_r3_n6_group_index_states_refused_by_owner(real_store, tmp_path):
    """R3-N6: every group_index entry carries refused_by_owner (true or false), so a
    refusal is visible on the unfiltered first page, not only via a group filter."""
    client = _client(real_store["reader"])
    index = client.get(URL, params={"audience": "entitled", "limit": "1"},
                       cookies=COOKIE).json()["page"]["group_index"]
    assert len(index) == 49  # real capture: every basket live, none refused
    assert all(g["refused_by_owner"] is False for g in index)
    refused_dir = tmp_path / "refused"  # a second publish needs its own isolated store
    refused_dir.mkdir()
    refused = _store_from(refused_dir, refuse_group="housing")
    index = refused.get(URL, params={"audience": "entitled", "limit": "1"},
                        cookies=COOKIE).json()["page"]["group_index"]
    housing = next(g for g in index if g["group_id"] == "housing")
    assert housing["refused_by_owner"] is True and housing["n_members_listed"] == 0
    assert all(isinstance(g["refused_by_owner"], bool) for g in index)


def test_v11_group_index_serves_name_zh_and_changes_nothing_else(real_store, tmp_path,
                                                                 monkeypatch):
    """V1.1 wire §5 (REAL): every group_index entry carries ``name_zh`` - tonight a
    non-null string within 160 on all 49 real groups - and nothing else about the
    capture moves: the cursor grammar, ``BASIS_VERSION`` and the consumer content
    hash (equal to a fresh ``build_population`` over the same real docs) are exact."""
    client = _client(real_store["reader"])
    first = client.get(URL, params={"audience": "entitled", "limit": "10"},
                       cookies=COOKIE).json()["page"]
    index = first["group_index"]
    assert len(index) == 49
    assert all("name_zh" in g for g in index)  # the key is always present
    assert all(isinstance(g["name_zh"], str) and 0 < len(g["name_zh"]) <= 160
               for g in index)
    memory = next(g for g in index if g["group_id"] == "memory_storage")
    assert memory["name_zh"] == "内存、HBM 与存储"  # the real captured Chinese name
    # the cursor grammar is unchanged: page 1's cursor still validates page 2
    # (the index itself rides only the unfiltered first page - page 2 has no key)
    second = client.get(URL, params={"audience": "entitled", "limit": "10",
                                     "cursor": first["next_cursor"]},
                        cookies=COOKIE).json()["page"]
    assert "group_index" not in second and second["rows"]
    # the capture itself is untouched by the serve-time projection
    capture = client.get(URL, params={"audience": "entitled", "limit": "1"},
                         cookies=COOKIE).json()["page"]["capture"]
    assert capture["owner_ref"]["basis_version"] == population.BASIS_VERSION \
        == "sector_population.basis/v1:baskets.members"
    central = json.loads(_real("sectordata/sector_central.json"))
    central["carried"] = _real_carry_blocks()
    rebuilt = population.build_population(
        baskets=json.loads(_real("basketdata/baskets.json")),
        handoff=json.loads(_real("basketdata/si_handoff.json")),
        action_board=json.loads((real_store["tmp"] / "action_board.json").read_bytes()),
        central=central)
    assert capture["owner_ref"]["consumer_content_sha256"] == rebuilt.content_sha256


def test_v11_group_index_name_zh_serves_null_for_hostile_shapes(tmp_path, monkeypatch):
    """V1.1 wire §5 (FIXTURE over real bytes): a 161-char, empty, non-string or absent
    ``name_zh`` serves null - the key stays present, the group still serves, and the
    serve-side bound is exactly 1..160 characters (unit-pinned below)."""
    from app.sector_generation import _group_index_name_zh
    assert _group_index_name_zh("内存、HBM 与存储") == "内存、HBM 与存储"
    assert _group_index_name_zh("x" * 160) == "x" * 160
    for hostile in ("x" * 161, "", None, 17, ["x"]):
        assert _group_index_name_zh(hostile) is None, hostile

    original = _real

    def patched(name):
        raw = original(name)
        if name != "basketdata/baskets.json":
            return raw
        document = json.loads(raw)
        by_id = {b["id"]: b for b in document["baskets"]}
        by_id["big_pharma"]["name_zh"] = "长" * 161   # over the bound
        by_id["us_sector_health"]["name_zh"] = ""     # empty
        by_id["defensives"]["name_zh"] = 17           # not a string
        by_id["energy_complex"].pop("name_zh", None)  # absent
        return json.dumps(document, separators=(",", ":"),
                          ensure_ascii=False).encode()

    monkeypatch.setattr(f"{__name__}._real", patched)
    mutated_dir = tmp_path / "namezh"
    mutated_dir.mkdir()
    _, published, root = _publish(mutated_dir, _real_bundle(tmp=mutated_dir),
                                  generation_id="namezh", now=PUBLISHED)
    assert published.status == "published", published.detail
    mutated = _client(SectorGenerationReader(generations_root=root,
                                             clock=lambda: PUBLISHED))
    index = mutated.get(URL, params={"audience": "entitled", "limit": "1"},
                        cookies=COOKIE).json()["page"]["group_index"]
    zh = {g["group_id"]: g["name_zh"] for g in index}
    assert len(index) == 49 and all("name_zh" in g for g in index)
    assert zh["big_pharma"] is None and zh["us_sector_health"] is None
    assert zh["defensives"] is None and zh["energy_complex"] is None
    assert zh["memory_storage"] == "内存、HBM 与存储"  # untouched groups keep theirs
    # the group still serves rows: the null costs nothing but the name
    # (the index itself rides only the unfiltered first page)
    page = mutated.get(URL, params={"audience": "entitled", "limit": "5",
                                    "group": "big_pharma"},
                       cookies=COOKIE).json()["page"]
    assert page["rows"] and "group_index" not in page


def test_r3_s1_real_route_a_basket_absent_from_both_lists_is_not_complete(tmp_path):
    """R3-S1: a real basket (housing, 18 configured) removed from the live list with
    NO refusal entry - the producer's ``lvl.dropna().empty`` exit or any other
    unexplained drop. The owner's carried roster still names it, so its members stay
    in the denominator as unaccounted and the route must NEVER answer complete."""
    client = _store_from(tmp_path, vanish_group="housing")
    pop = client.get(URL, params={"audience": "entitled", "limit": "1"},
                     cookies=COOKIE).json()["page"]["capture"]["population"]
    assert (pop["configured_current"], pop["served"], pop["accounted_unserved"]) == (1020, 997, 5)
    vanished = [u for u in pop["unserved_members"] if u["group_id"] == "housing"]
    assert len(vanished) == 18
    assert {u["reason"] for u in vanished} == {"unaccounted_by_owner"}
    assert (pop["unaccounted"], pop["complete"]) == (18, False)


def test_sp18_same_context_refresh_emits_no_duplicate_generation(real_store):
    """REAL bytes through the real publisher: republishing identical content is `unchanged`.

    This is the publisher's half of SP18 only ("a same-context refresh emits no
    duplicate"). The other half - "a correction links to its original" - is NOT
    produced: neither the manifest nor the selection records a predecessor (see the wire
    doc), so `correction_lineage` stays unavailable/not_produced.
    """
    tmp, root, first = real_store["tmp"], real_store["root"], real_store["first"]
    before = sorted(p.name for p in (root / "sector").iterdir() if p.is_dir())
    again_dir = tmp / "again"
    again_dir.mkdir()
    _, second, _ = _publish(tmp, _real_bundle(tmp=again_dir), generation_id="real-g1",
                            expected=first.content_id, now=PUBLISHED)
    assert second.status == "unchanged" and second.content_id == first.content_id
    assert sorted(p.name for p in (root / "sector").iterdir() if p.is_dir()) == before
    manifest = json.loads((root / "sector" / "real-g1" / "manifest.json").read_text())
    assert not {"predecessor", "supersedes", "previous_content_id", "corrects"} & set(manifest)
    selection = json.loads((root / "sector" / "current.json").read_text())
    assert not {"predecessor", "supersedes", "previous_content_id", "corrects"} & set(selection)
    capture = _client(real_store["reader"]).get(
        URL, params={"audience": "entitled", "limit": "1"}, cookies=COOKIE
    ).json()["page"]["capture"]
    assert capture["correction_rights"]["correction_lineage"] == {
        "status": "unavailable", "reason": "not_produced"}


def test_search_also_finds_accounted_unserved_members(real_store):
    """R2-N2: `q` over the full population includes the accounted-but-unserved list."""
    client = _client(real_store["reader"])
    page = client.get(URL, params={"audience": "entitled", "q": "KVUE"},
                      cookies=COOKIE).json()["page"]
    assert page["total_matching"] == 0 and page["rows"] == []
    assert sorted((u["group_id"], u["reason"]) for u in page["unserved_matching"]) == [
        ("defensives", "not_observed_at_effective_as_of"),
        ("us_sector_staples", "not_observed_at_effective_as_of")]


def test_forged_context_reference_answers_the_original_unavailable_class(real_store):
    """S3: a forged `x` token (not just a stale one) is the same 404 body."""
    client = _client(real_store["reader"])
    first = client.get(URL, params={"audience": "entitled", "limit": "1"},
                       cookies=COOKIE).json()["page"]
    ref = first["context_ref"]
    forged = ref[:-1] + ("0" if ref[-1] != "0" else "1")
    response = client.get(URL, params={"audience": "entitled", "cursor": forged}, cookies=COOKIE)
    assert response.status_code == 404 and response.json() == {
        "schema": "sector_generation.error/v1", "code": "ORIGINAL_UNAVAILABLE"}
    assert response.headers["cache-control"] == "private, no-store"


def test_r2_b2_owner_refused_baskets_stay_in_the_denominator():
    """FIXTURE: a basket the owner refused keeps its configured roster, visibly."""
    refused = {"basket_id": "g2", "observation": {
        "configured_members": ["XXX", "YYY", "ZZZ"], "status": "insufficient",
        "coverage": 0.33, "observed_n": 1, "configured_n": 3, "min_members": 3,
        "min_coverage": 0.6, "effective_as_of": "2026-11-06", "aggregate_eligible": False}}
    baskets = _synthetic(observation=_obs(["AAA", "BBB"]))
    baskets["observation_refusals"] = [refused]
    pop = population.build_population(baskets=baskets, handoff={}, action_board={},
                                      central=_roster_central(
                                          {"g1": ["AAA", "BBB"], "g2": ["XXX", "YYY", "ZZZ"]}))
    assert (pop.configured_current, pop.served, pop.accounted_unserved, pop.unaccounted) == (5, 2, 3, 0)
    assert {(u["group_id"], u["symbol"], u["reason"]) for u in pop.unserved} == {
        ("g2", s, "group_refused_by_owner_observation") for s in ("XXX", "YYY", "ZZZ")}
    group = next(g for g in pop.groups if g["group_id"] == "g2")
    assert group["refused_by_owner"] is True and group["n_members_listed"] == 0
    assert group["n_configured_current"] == 3 and group["n_unserved"] == 3
    assert group["owner_observation_refusal"]["coverage"] == 0.33
    assert pop.complete is True  # all 5 accounted: 2 served + 3 owner-refused
    # the live groups report themselves as NOT refused
    assert next(g for g in pop.groups if g["group_id"] == "g1")["refused_by_owner"] is False
    # a missing or malformed refusal list makes completeness UNKNOWN, never true
    missing_key = _synthetic(observation=_obs(["AAA", "BBB"]))
    del missing_key["observation_refusals"]
    assert population.build_population(baskets=missing_key, handoff={}, action_board={},
                                       central={}).complete is None
    for bad in ("nope", [{"basket_id": "g2"}], [{"basket_id": "g2", "observation": {
            "configured_members": "XXX"}}], [{"basket_id": "g1", "observation": {
            "configured_members": ["AAA"]}}]):  # last: duplicates a live group id
        broken = _synthetic(observation=_obs(["AAA", "BBB"]))
        broken["observation_refusals"] = bad
        assert population.build_population(baskets=broken, handoff={}, action_board={},
                                           central={}).complete is None


def test_r3_n1_owner_observation_refusal_strings_are_bounded():
    """FIXTURE: R3-N1 - refusal strings take the same ``_text`` bound the live groups
    use; a 200k-char status and a boolean coverage are dropped, numbers pass."""
    refused = {"basket_id": "g2", "observation": {
        "configured_members": ["XXX"], "status": "s" * 200_000, "coverage": True,
        "observed_n": 1.0, "configured_n": 1, "min_members": 3, "min_coverage": 0.6,
        "effective_as_of": "2026-11-06"}}
    baskets = _synthetic(observation=_obs(["AAA", "BBB"]))
    baskets["observation_refusals"] = [refused]
    pop = population.build_population(
        baskets=baskets, handoff={}, action_board={},
        central=_roster_central({"g1": ["AAA", "BBB"], "g2": ["XXX"]}))
    refusal = next(g for g in pop.groups if g["group_id"] == "g2")["owner_observation_refusal"]
    assert refusal == {"observed_n": 1.0, "configured_n": 1, "min_members": 3,
                       "min_coverage": 0.6, "effective_as_of": "2026-11-06"}


def test_removed_member_that_is_also_configured_is_a_contradiction():
    """FIXTURE: owner roster says removed while the capture still configures it."""
    baskets = _synthetic(observation=_obs(["AAA", "BBB"]))
    pop = population.build_population(
        baskets=baskets, handoff={}, action_board={},
        central=_roster_central({"g1": ["AAA", "BBB"]}, removed_members={
            "source": "r", "as_of": "2026-11-06", "removed": [
                {"group_id": "g1", "symbol": "AAA", "removed_on": "2025-01-01"}]}))
    assert pop.unaccounted == 1 and pop.complete is False


def test_max_unserved_is_refused_not_truncated():
    """FIXTURE: an unserved list over the bound fails the build instead of being cut."""
    names = [f"S{i}" for i in range(population.MAX_UNSERVED + 1)]
    baskets = _synthetic(observation=_obs(["AAA", "BBB", *names], asof_missing=names))
    with pytest.raises(population.PopulationError):
        population.build_population(baskets=baskets, handoff={}, action_board={}, central={})


def test_malformed_or_missing_industry_blocks_degrade_to_unavailable_not_error():
    """FIXTURE: population-level behaviour when the carried taxonomies are bad."""
    for carried in ({}, {"member_industry": "x", "member_sub_industry": 3},
                    {"member_industry": {"symbols": {"AAA": "Media"}, "point_in_time": True}}):
        pop = population.build_population(
            baskets=_synthetic(observation=_obs(["AAA", "BBB"])), handoff={}, action_board={},
            central={"carried": carried})
        assert pop.industry_classification == {"status": "unavailable", "reason": "not_produced"}
        assert {r["industry"]["reason"] for r in pop.rows} == {"not_produced"}


def test_f1_removed_members_are_separate_from_listed_and_missing():
    """FIXTURE: a removal is neither served, unserved nor missing; it carries its date."""
    from lib.sector_central_carry import removed_members
    roster = {"version": "t", "baskets": {"g1": {"members": [
        {"ticker": "AAA", "removed": None}, {"ticker": "OLD", "removed": "2025-01-16"},
        {"ticker": "FUTR", "removed": "2099-01-01"}]}}}
    removed = removed_members(roster, "2026-11-06")
    assert removed["removed"] == [{"group_id": "g1", "symbol": "OLD", "removed_on": "2025-01-16"}]
    assert removed_members(None, "2026-11-06") is None  # no roster => not carried


def test_retained_capture_loss_resets_and_never_substitutes_latest(real_store):
    client = _client(real_store["reader"])
    first = client.get(URL, params={"audience": "entitled", "limit": "100"},
                       cookies=COOKIE).json()["page"]
    _advance(real_store)
    shutil.rmtree(real_store["root"] / "sector" / "real-g1")
    response = client.get(URL, params={"audience": "entitled", "limit": "100",
                                       "cursor": first["next_cursor"]}, cookies=COOKIE)
    assert response.status_code == 409
    assert response.json()["reason"] == "capture_not_retained"
    assert "real-g2" not in response.text
    ref = client.get(URL, params={"audience": "entitled", "cursor": first["context_ref"]},
                     cookies=COOKIE)
    assert ref.status_code == 404 and ref.json()["code"] == "ORIGINAL_UNAVAILABLE"


def test_original_ref_reopens_the_retained_capture_not_the_latest(real_store):
    client = _client(real_store["reader"])
    first = client.get(URL, params={"audience": "entitled", "limit": "1"},
                       cookies=COOKIE).json()["page"]
    ref = first["capture"]["owner_ref"]["retained_resolver_ref"]
    assert ref == first["context_ref"]
    _advance(real_store)
    original = client.get(URL, params={"audience": "entitled", "limit": "5", "cursor": ref,
                                       "q": "A"}, cookies=COOKIE).json()["page"]
    assert original["capture"]["owner_ref"]["generation_id"] == "real-g1"
    assert original["capture"]["currentness"] == "retained_original"
    assert original["capture"]["population"]["served"] == 1015


def test_denied_before_read_one_reader_and_closed_selectors(real_store):
    calls = []

    class Counting(SectorGenerationReader):
        def read_population(self, request):
            calls.append(request)
            return super().read_population(request)

    reader = Counting(generations_root=real_store["root"], clock=lambda: PUBLISHED)
    client = _client(reader)
    assert client.get(URL, params={"audience": "entitled"}).status_code == 401  # no cookie
    assert calls == []
    for params in ({}, {"audience": "preview"}, {"audience": "entitled", "generation": "real-g1"},
                   {"audience": "entitled", "path": "/etc/passwd"}, {"audience": "entitled", "limit": "0"},
                   {"audience": "entitled", "limit": "201"}, {"audience": "entitled", "q": "x" * 65},
                   {"audience": "entitled", "group": "UPPER"}):
        assert client.get(URL, params=params, cookies=COOKIE).status_code == 400, params
    assert calls == []
    ok = client.get(URL, params={"audience": "entitled", "limit": "10"}, cookies=COOKIE)
    assert ok.status_code == 200 and len(calls) == 1  # exactly one reader call
    assert calls[0].capture is None and calls[0].audience == "entitled"


def test_oversized_page_is_refused_not_truncated():
    huge = {"rows": ["x" * 1024] * 5000}
    with pytest.raises(wire.SectorGenerationTooLarge):
        wire.encode_sector_population(audience="entitled", source_session=SESSION,
            published_at=PUBLISHED.isoformat(), qualification="accepted", page=huge)
    with pytest.raises(ValueError):
        wire.encode_sector_population(audience="entitled", source_session=SESSION,
            published_at=PUBLISHED.isoformat(), qualification="accepted",
            page={"v": float("nan")})


def test_producer_emits_finite_json_without_post_hoc_repair(tmp_path):
    """REAL: the committed board carries a legacy NaN; the ordinary writer's output is strict."""
    committed_raw = _real("basketdata/action_board.json").decode()
    assert len(re.findall(r"\bNaN\b", committed_raw)) >= 1  # the real defect this guards
    raw, _ = _real_bundle(tmp=tmp_path)
    produced = raw[MEMBERS[4]].decode()
    assert not re.search(r"\bNaN\b|\bInfinity\b", produced)
    decoded = contract._decode_member(raw[MEMBERS[4]])  # the strict member decoder accepts it
    assert decoded["schema"] == "sector_intelligence_action_board.v1"
    # Every finite number is unchanged; only the non-finite position became null.
    original = json.loads(committed_raw, parse_constant=lambda _: float("nan"))
    def walk(a, b, path=""):
        if isinstance(a, dict):
            assert set(a) == set(b), path
            for k in a:
                walk(a[k], b[k], path + "/" + k)
        elif isinstance(a, list):
            assert len(a) == len(b), path
            for i, (x, y) in enumerate(zip(a, b)):
                walk(x, y, f"{path}[{i}]")
        elif isinstance(a, float) and a != a:
            assert b is None, path
        elif path.split("/")[-1] != "generated_utc":
            assert a == b, path
    walk(original["action_board"], decoded["action_board"])


def test_r4_n3_an_undated_carried_block_reads_unavailable_never_available():
    """R4-N3 (read side): every carried DATED block that arrives without a string
    ``as_of`` is served as unavailable/``carried_block_undated`` - never available
    with an unstated or null clock, and never silently dropped either."""
    carried = {
        "member_industry": {"symbols": {"AAA": "Media"}, "point_in_time": False},
        "member_sub_industry": {"symbols": {"AAA": "software-application"},
                                "subsectors": {"software-application": "Software - Application"},
                                "point_in_time": False},
        "removed_members": {"source": "r", "removed": [
            {"group_id": "g1", "symbol": "AAA", "removed_on": "2025-01-01"}]},
        "membership_first_known": {"basis": "lower_bound_from_stored_snapshots",
                                   "first_known": {"g1": {"AAA": "2026-08-13"}}},
        "membership_snapshots": {"suite": "baskets", "groups": {"g1": {
            "status": "available", "snapshot_date": "2026-10-14", "members_sha": None,
            "member_count": 1, "equals_current_roster": True}}}}
    pop = population.build_population(
        baskets=_synthetic(observation=_obs(["AAA", "BBB"])), handoff={}, action_board={},
        central={"carried": carried})
    undated = {"status": "unavailable", "reason": "carried_block_undated"}
    assert pop.industry_classification == dict(undated)
    assert pop.sub_industry_classification == dict(undated)
    assert pop.removed == dict(undated)
    assert pop.first_known == dict(undated)
    assert pop.membership_snapshot == dict(undated)
    # rows degrade to the honest not_produced class, never to an unlabelled value
    assert {r["industry"]["reason"] for r in pop.rows} == {"not_produced"}
    assert {r["sub_industry"]["reason"] for r in pop.rows} == {"not_produced"}
    assert pop.removed.get("members") is None  # an undated removal list is not served
    # the same blocks WITH their as_of string stay available (dated is the rule, not ban)
    for block in carried.values():
        block["as_of"] = "2026-11-06"
    dated = population.build_population(
        baskets=_synthetic(observation=_obs(["AAA", "BBB"])), handoff={}, action_board={},
        central={"carried": carried})
    assert dated.industry_classification["status"] == "available"
    assert dated.removed["status"] == "available" and dated.removed["n"] == 1
    assert dated.first_known["status"] == "available"
    assert dated.membership_snapshot["status"] == "available"


def test_r4_n4_the_carried_roster_must_agree_with_the_capture_clock(real_store, tmp_path):
    """R4-N4: completeness is only verifiable when the carried roster's ``as_of``
    equals the capture's single ``observation.effective_as_of``; any disagreement
    nulls ``configured_current``/``complete`` and is disclosed with closed reasons."""
    client = _client(real_store["reader"])
    capture = client.get(URL, params={"audience": "entitled", "limit": "1"},
                         cookies=COOKIE).json()["page"]["capture"]
    pop = capture["population"]
    assert pop["roster_clock"] == {"status": "agree", "roster_as_of": "2026-11-06",
                                   "capture_effective_as_of": "2026-11-06"}
    assert (pop["configured_current"], pop["complete"]) == (1020, True)
    # REAL bytes, derived capture: every observation restated one session earlier while
    # the carried roster block stays cut at 2026-11-06 - the roster can no longer vouch.
    # (its own isolated store: the fixture's store already owns tmp_path's selection)
    skewed_dir = tmp_path / "skewed"
    skewed_dir.mkdir()
    skewed = _store_from(skewed_dir, effective_as_of="2026-11-05")
    pop = skewed.get(URL, params={"audience": "entitled", "limit": "1"},
                     cookies=COOKIE).json()["page"]["capture"]["population"]
    assert pop["roster_clock"] == {"status": "mismatch", "reason": "roster_as_of_mismatch",
                                   "roster_as_of": "2026-11-06",
                                   "capture_effective_as_of": "2026-11-05"}
    assert pop["configured_current"] is None and pop["complete"] is None
    # S1: a roster that cannot vouch for the capture contributes NOTHING - no
    # ``unaccounted_by_owner`` entries from it, and ``unaccounted`` itself is served
    # as null, never a guessed 0
    assert pop["unaccounted"] is None
    assert all(u["reason"] != "unaccounted_by_owner" for u in pop["unserved_members"])
    # FIXTURE: the closed reasons around the capture's own clock
    def build(doc, roster):
        return population.build_population(baskets=doc, handoff={}, action_board={},
                                           central=_roster_central(roster))
    two_sessions = {"baskets": [
        {"id": "g1", "name": "G", "n_members": 1,
         "members": [{"symbol": "AAA", "name": "A", "added": "2024-01-01"}],
         "observation": _obs(["AAA"], effective_as_of="2026-11-06")},
        {"id": "g2", "name": "H", "n_members": 1,
         "members": [{"symbol": "XXX", "name": "X", "added": "2024-01-01"}],
         "observation": _obs(["XXX"], effective_as_of="2026-11-05")}],
        "observation_refusals": []}
    not_single = build(two_sessions, {"g1": ["AAA"]})
    assert not_single.roster_clock == {
        "status": "mismatch", "reason": "capture_effective_as_of_not_single",
        "roster_as_of": "2026-11-06", "capture_effective_as_of": ["2026-11-05", "2026-11-06"]}
    assert not_single.complete is None and not_single.configured_current is None
    # S1, the reviewer's realistic trigger: the owner's REFUSALS stamped at a different
    # session than the live groups - two stamps, so the roster cannot vouch. The
    # roster's own unexplained basket (gone) must contribute NOTHING and unaccounted
    # reads null, while the refusal's owner-explained evidence is still served.
    refused_skew = {"baskets": [
        {"id": "g1", "name": "G", "n_members": 1,
         "members": [{"symbol": "AAA", "name": "A", "added": "2024-01-01"}],
         "observation": _obs(["AAA"], effective_as_of="2026-11-06")}],
        "observation_refusals": [
            {"basket_id": "g2", "observation": _obs(["YYY"], effective_as_of="2026-11-05")}]}
    skewed = build(refused_skew, {"g1": ["AAA"], "g2": ["YYY"], "gone": ["XXX"]})
    assert skewed.roster_clock["reason"] == "capture_effective_as_of_not_single"
    assert skewed.unaccounted is None and skewed.complete is None
    assert not [u for u in skewed.unserved
                if u["reason"] == population.REASON_UNACCOUNTED]
    assert [(u["group_id"], u["symbol"]) for u in skewed.unserved
            if u["group_id"] == "g2"] == [("g2", "YYY")]
    # control: the SAME capture with the refusal stamped at the SAME session - one
    # agreeing clock - DOES account both the refusal and ``gone`` (the clock gate,
    # not the fixture, is what suppresses it above)
    agreeing_doc = {"baskets": [
        {"id": "g1", "name": "G", "n_members": 1,
         "members": [{"symbol": "AAA", "name": "A", "added": "2024-01-01"}],
         "observation": _obs(["AAA"], effective_as_of="2026-11-06")}],
        "observation_refusals": [
            {"basket_id": "g2", "observation": _obs(["YYY"], effective_as_of="2026-11-06")}]}
    agreeing = build(agreeing_doc, {"g1": ["AAA"], "g2": ["YYY"], "gone": ["XXX"]})
    assert agreeing.roster_clock["status"] == "agree"
    assert agreeing.unaccounted == 1 and agreeing.complete is False
    assert [(u["group_id"], u["symbol"], u["reason"]) for u in agreeing.unserved
            if u["group_id"] == "gone"] == [("gone", "XXX", population.REASON_UNACCOUNTED)]
    # the clock comparison is EXACT STRING EQUALITY: a form-only difference (the same
    # session with an ISO time suffix) still reads mismatch, never a normalized agree
    form_only = population.build_population(
        baskets=_synthetic(observation=_obs(["AAA", "BBB"])), handoff={}, action_board={},
        central={"carried": {"roster_baskets": {
            "as_of": "2026-11-06T00:00:00", "baskets": {"g1": ["AAA", "BBB"]}}}})
    assert form_only.roster_clock == {"status": "mismatch", "reason": "roster_as_of_mismatch",
                                      "roster_as_of": "2026-11-06T00:00:00",
                                      "capture_effective_as_of": "2026-11-06"}
    assert form_only.unaccounted is None and form_only.complete is None
    # N1: a null effective_as_of is the producer's legitimate "no clock" value
    # (population_observation stamps _date_text(when), which is None when the
    # producer has no clock) - unavailable, NOT malformed (see the dedicated N1 test)
    unstated = _synthetic(observation=_obs(["AAA", "BBB"], effective_as_of=None))
    unclocked = build(unstated, {"g1": ["AAA", "BBB"]})
    assert unclocked.roster_clock == {
        "status": "unavailable", "reason": "capture_effective_as_of_unavailable",
        "roster_as_of": "2026-11-06"}
    assert unclocked.complete is None and unclocked.configured_current is None
    # no observation mapping AT ALL states no clock the same way: unavailable
    no_observation = build(_synthetic(observation=None), {"g1": ["AAA", "BBB"]})
    assert no_observation.roster_clock == {
        "status": "unavailable", "reason": "capture_effective_as_of_unavailable",
        "roster_as_of": "2026-11-06"}
    # no roster block at all / a malformed one: the clock is unavailable for that reason
    absent = population.build_population(
        baskets=_synthetic(observation=_obs(["AAA", "BBB"])), handoff={}, action_board={},
        central={})
    assert absent.roster_clock == {"status": "unavailable", "reason": "roster_block_absent"}
    malformed = population.build_population(
        baskets=_synthetic(observation=_obs(["AAA", "BBB"])), handoff={}, action_board={},
        central={"carried": {"roster_baskets": {"as_of": "2026-11-06", "baskets": {"gone": [7]}}}})
    assert malformed.roster_clock == {"status": "unavailable", "reason": "roster_block_malformed"}
    assert absent.complete is None and malformed.complete is None


def test_s2_a_malformed_capture_effective_as_of_makes_the_clock_indeterminate():
    """S2: an observation mapping present but whose ``effective_as_of`` is a value of
    the wrong type or shape - a list, a number, an empty string, a nested object -
    makes the capture clock INDETERMINATE even beside one good stamp: the roster
    cannot vouch, ``configured_current``/``complete`` read null (never true in any
    shape), the roster contributes nothing, and the disagreement is disclosed with
    the closed ``capture_effective_as_of_malformed`` reason. A null or absent stamp
    is NOT one of these shapes (N1: it is the producer's "no clock" value and reads
    ``capture_effective_as_of_unavailable`` instead)."""
    good_stamp = "2026-11-06"
    roster = {"g1": ["AAA"], "gone": ["XXX"]}
    for bad in ([], 20261106, "", {"session": "2026-11-06"}):
        doc = {"baskets": [
            {"id": "g1", "name": "G", "n_members": 1,
             "members": [{"symbol": "AAA", "name": "A", "added": "2024-01-01"}],
             "observation": {**_obs(["AAA"]), "effective_as_of": good_stamp}},
            {"id": "g2", "name": "H", "n_members": 1,
             "members": [{"symbol": "BBB", "name": "B", "added": "2024-01-01"}],
             "observation": {**_obs(["BBB"]), "effective_as_of": bad}}],
            "observation_refusals": []}
        pop = population.build_population(
            baskets=doc, handoff={}, action_board={}, central=_roster_central(roster))
        assert pop.roster_clock == {"status": "unavailable",
                                    "reason": "capture_effective_as_of_malformed",
                                    "roster_as_of": "2026-11-06"}, bad
        assert pop.configured_current is None and pop.complete is None, bad
        assert pop.unaccounted is None, bad
        assert not [u for u in pop.unserved
                    if u["reason"] == population.REASON_UNACCOUNTED], bad


def test_n1_a_null_or_absent_effective_as_of_is_the_producers_no_clock_value():
    """N1: an ``effective_as_of`` that is null - or whose key is absent - is the
    producer's legitimate "no clock" value (``population_observation`` stamps
    ``_date_text(when)``, which is None when the producer has no clock to state), so
    the capture clock reads unavailable/``capture_effective_as_of_unavailable`` - the
    reason it carried before S2 - never ``capture_effective_as_of_malformed``, which
    stays for a PRESENT value of the wrong type or shape. Both outcomes are
    fail-closed alike: the roster vouches for nothing, ``configured_current``/
    ``complete``/``unaccounted`` read null, never true, never a guessed 0."""
    roster = {"g1": ["AAA"], "gone": ["XXX"]}
    for how in ("null", "absent key", "null beside a good stamp"):
        obs = _obs(["AAA"])
        doc = {"baskets": [
            {"id": "g1", "name": "G", "n_members": 1,
             "members": [{"symbol": "AAA", "name": "A", "added": "2024-01-01"}],
             "observation": obs}],
            "observation_refusals": []}
        if how == "null":
            obs["effective_as_of"] = None
        elif how == "absent key":
            obs.pop("effective_as_of")
        else:  # one group states a session; the other states no clock
            doc["baskets"].append(
                {"id": "g2", "name": "H", "n_members": 1,
                 "members": [{"symbol": "BBB", "name": "B", "added": "2024-01-01"}],
                 "observation": _obs(["BBB"], effective_as_of="2026-11-06")})
            doc["baskets"][0]["observation"]["effective_as_of"] = None
        pop = population.build_population(
            baskets=doc, handoff={}, action_board={}, central=_roster_central(roster))
        assert pop.roster_clock == {"status": "unavailable",
                                    "reason": "capture_effective_as_of_unavailable",
                                    "roster_as_of": "2026-11-06"}, how
        assert pop.configured_current is None and pop.complete is None, how
        assert pop.unaccounted is None, how
        assert not [u for u in pop.unserved
                    if u["reason"] == population.REASON_UNACCOUNTED], how
    # control: a PRESENT wrong-typed value is still malformed (S2), fail-closed alike
    malformed = {"baskets": [
        {"id": "g1", "name": "G", "n_members": 1,
         "members": [{"symbol": "AAA", "name": "A", "added": "2024-01-01"}],
         "observation": {**_obs(["AAA"]), "effective_as_of": ["2026-11-06"]}}],
        "observation_refusals": []}
    pop = population.build_population(
        baskets=malformed, handoff={}, action_board={}, central=_roster_central(roster))
    assert pop.roster_clock["reason"] == "capture_effective_as_of_malformed"
    assert pop.complete is None and pop.unaccounted is None


def test_n6_a_pattern_matching_non_calendar_day_reads_like_a_pattern_mismatch():
    """N6: a string that matches the day PATTERN but is not a real calendar date
    (``2026-02-30``, ``2026-13-01``) is treated exactly as a pattern mismatch is
    treated today at every site that day-checks a carried fact: the SAME closed
    reason, no new reason code. A ``first_known`` pair value or a group's
    ``snapshot_date`` in that shape degrades the WHOLE fact to
    unavailable/``not_produced``; ``store_first``/``store_last`` read null."""
    def first_known(doc):
        return population.build_population(
            baskets=_synthetic(observation=_obs(["AAA", "BBB"])), handoff={}, action_board={},
            central={"carried": {"membership_first_known": doc}}).first_known

    def snapshots(doc):
        return population.build_population(
            baskets=_synthetic(observation=_obs(["AAA", "BBB"])), handoff={}, action_board={},
            central={"carried": {"membership_snapshots": doc}}).membership_snapshot

    not_produced = {"status": "unavailable", "reason": "not_produced"}
    good_fk = {"as_of": "2026-11-06", "basis": "lower_bound_from_stored_snapshots",
               "first_known": {"g1": {"AAA": "2026-08-13", "BBB": None}}}
    assert first_known(good_fk)["status"] == "available"  # control: real dates pass
    for bogus in ("2026-02-30", "2026-13-01"):
        value = {**good_fk, "first_known": {"g1": {"AAA": bogus, "BBB": None}}}
        assert first_known(value) == dict(not_produced), bogus  # same as a mismatch
    assert first_known({**good_fk, "first_known": {"g1": {"AAA": "not-a-date",
                                                          "BBB": None}}}) == dict(not_produced)
    span = first_known({**good_fk, "store_first": "2026-02-30",
                        "store_last": "2026-13-01"})
    assert span["store_first"] is None and span["store_last"] is None
    good_snap = {"as_of": "2026-11-06", "suite": "baskets",
                 "groups": {"g1": {"status": "available", "snapshot_date": "2026-10-14",
                                   "members_sha": None, "member_count": 1,
                                   "equals_current_roster": True}}}
    assert snapshots(good_snap)["status"] == "available"  # control
    for bogus in ("2026-02-30", "2026-13-01"):
        bad = {**good_snap, "groups": {"g1": {**good_snap["groups"]["g1"],
                                              "snapshot_date": bogus}}}
        assert snapshots(bad) == dict(not_produced), bogus  # same as a mismatch
    assert snapshots({**good_snap, "groups": {"g1": {**good_snap["groups"]["g1"],
                                                     "snapshot_date": "not-a-date"}}}
                     ) == dict(not_produced)


def test_s3_the_carried_snapshot_fact_enforces_suite_and_members_sha():
    """S3: the carried ``membership_snapshots`` fact is only readable when it states
    the owner's own suite (the literal ``baskets``) and every available group's
    ``members_sha`` is null or a lowercase 64-hex digest; failing either degrades the
    WHOLE fact with the closed ``carried_fact_malformed`` reason, never a partially
    trusted group set. The owner's own per-group unavailable reasons - including
    ``pit_answer_unreadable`` - pass through verbatim."""
    dated = {"as_of": "2026-11-06", "suite": "baskets", "groups": {
        "g1": {"status": "available", "snapshot_date": "2026-10-14",
               "members_sha": "e21bee3f132251844940e3c114aaca993bca628883b8877b1248a34c8e4245aa",
               "member_count": 8, "equals_current_roster": True},
        "g2": {"status": "unavailable", "reason": "pit_answer_unreadable"}}}

    def fact(doc):
        return population.build_population(
            baskets=_synthetic(observation=_obs(["AAA", "BBB"])), handoff={}, action_board={},
            central={"carried": {"membership_snapshots": doc}}).membership_snapshot

    good = fact(dated)
    assert good["status"] == "available" and good["suite"] == "baskets"
    assert good["groups"]["g2"] == {"status": "unavailable", "reason": "pit_answer_unreadable"}
    malformed = {"status": "unavailable", "reason": "carried_fact_malformed"}
    for suite in ("sector", "BASKETS", None, ""):
        assert fact({**dated, "suite": suite}) == dict(malformed), suite
    for sha in ("not-a-sha", "E21BEE3F132251844940E3C114AACA993BCA628883B8877B1248A34C8E4245AA",
                "e21bee3f132251844940e3c114aaca993bca628883b8877b1248a34c8e4245", 123):
        bad = {**dated, "groups": {**dated["groups"], "g1": {
            **dated["groups"]["g1"], "members_sha": sha}}}
        assert fact(bad) == dict(malformed), sha
    null_sha = {**dated, "groups": {**dated["groups"], "g1": {
        **dated["groups"]["g1"], "members_sha": None}}}
    assert fact(null_sha)["status"] == "available"  # a null sha stays legal


def test_r4_n6_non_finite_refusal_fields_are_dropped_and_the_page_stays_finite():
    """R4-N6: a NaN/inf in an owner refusal field is dropped by ``_refusal_field``;
    the population still encodes to a strictly finite, normal response.

    Seam note: this is the DECODED-document seam, not published bytes - the strict
    member decoder (``parse_constant``) rejects any byte stream carrying NaN or
    Infinity before the population builder runs, so a non-finite float can only
    reach ``_refusal_field`` via a decoded mapping (the same route the committed
    action_board's legacy NaN takes through ``parse_constant=float``). Injecting
    them there proves the real guarantee: the field is dropped, never repaired,
    and the response passes ``allow_nan=False`` end to end."""
    refusal = {"basket_id": "g2", "observation": {
        "configured_members": ["XXX"], "status": float("nan"), "coverage": float("inf"),
        "configured_n": 1, "min_members": 3, "effective_as_of": "2026-11-06"}}
    baskets = _synthetic(observation=_obs(["AAA", "BBB"]))
    baskets["observation_refusals"] = [refusal]
    pop = population.build_population(
        baskets=baskets, handoff={}, action_board={},
        central=_roster_central({"g1": ["AAA", "BBB"], "g2": ["XXX"]}))
    served = next(g for g in pop.groups if g["group_id"] == "g2")
    assert served["owner_observation_refusal"] == {"configured_n": 1, "min_members": 3,
                                                  "effective_as_of": "2026-11-06"}
    assert pop.complete is True  # the refusal still accounts its member normally
    capture = population.compatibility_tuple(
        generation_id="g", content_id="c", published_at=PUBLISHED.isoformat(),
        source_session=SESSION, qualification="accepted",
        read_captured_at=PUBLISHED.isoformat(), member_sha256={}, population=pop,
        ref="ref", currentness="current")
    encoded = wire.encode_sector_population(
        audience="entitled", source_session=SESSION, published_at=PUBLISHED.isoformat(),
        qualification="accepted", page={"capture": capture, "rows": [dict(r) for r in pop.rows]})
    assert b"NaN" not in encoded and b"Infinity" not in encoded  # finite, normal response


def test_part_b_pit_membership_facts_travel_in_the_capture_not_on_rows(real_store):
    """Part B, REAL route: the three carried point-in-time facts surface in the
    entitled capture with the committed store's own values, and never on rows."""
    client = _client(real_store["reader"])
    pages = _all_pages(client)
    identity, pop = pages[0][1]["capture"]["identity"], pages[0][1]["capture"]["population"]
    fk = identity["membership_first_known"]
    assert (fk["status"], fk["basis"], fk["as_of"]) == (
        "available", "lower_bound_from_stored_snapshots", SESSION)
    assert fk["source"] == "engine/basket_membership_pit.py:data/baskets/membership_history.parquet"
    assert fk["basis_note"] and (fk["store_first"], fk["store_last"]) == ("2026-08-13", "2026-10-14")
    assert fk["absent_pair_reason"] == "no_stored_snapshot"
    pairs = {(g, s): d for g, bucket in fk["groups"].items() for s, d in bucket.items()}
    assert len(pairs) == 1020 and all(d is not None for d in pairs.values())
    assert set(pairs.values()) == {"2026-08-13", "2026-08-18", "2026-09-04", "2026-10-14"}
    assert pairs[("silver_miners", "PAAS")] == "2026-08-13"  # a real early-store member
    snap = identity["membership_snapshot"]
    assert (snap["status"], snap["suite"], snap["as_of"]) == ("available", "baskets", SESSION)
    assert len(snap["groups"]) == 49
    assert all(e["status"] == "available" and e["snapshot_date"] == "2026-10-14"
               and e["equals_current_roster"] is True
               for e in snap["groups"].values())
    silver = snap["groups"]["silver_miners"]
    assert (silver["member_count"], silver["members_sha"]) == (
        8, "e21bee3f132251844940e3c114aaca993bca628883b8877b1248a34c8e4245aa")
    assert pop["roster_clock"]["status"] == "agree"  # the third fact (R4-N4)
    # the facts live ONLY in the capture: no row carries a PIT field
    rows = [r for _, page in pages for r in page["rows"]]
    rows_json = json.dumps(rows)
    for needle in ("first_known", "membership_snapshot", "roster_clock",
                   "equals_current_roster", "members_sha"):
        assert needle not in rows_json
    # every page still fits the unchanged 4 MiB encoded bound (largest page measured
    # on the real capture with all three new facts: 97,237 bytes - 2.3% of the bound)
    largest = max(len(response.content) for response, _ in pages)
    assert largest <= wire.MAX_ENCODED_BYTES == 4 * 1024 * 1024


def test_nothing_new_appears_in_the_legacy_projection_or_typed_blocks(tmp_path):
    """Frozen constraint: the legacy projection and ``typed_blocks`` (closed at twelve
    sources - the seven incumbent plus the five lane-1 v1.1 row blocks) gain NOTHING
    from the Part B facts, even when the carry carries them."""
    from engine.sector_native_view import project_sector_view, typed_blocks_of
    raw, identity = _real_bundle(tmp=tmp_path)  # real bytes + NEW carry (PIT blocks in)
    assert set(_real_carry_blocks()) >= {"membership_first_known", "membership_snapshots"}
    inputs, receipt = contract._capture_view(
        member_bytes=raw, input_identity=identity, generation_id="carry",
        published_at=PUBLISHED.isoformat(), now=PUBLISHED)
    for audience in ("entitled", "preview"):
        projection = project_sector_view(inputs, receipt, audience=audience)
        assert set(typed_blocks_of(projection["data"])) == {
            "r1_rising_priced_share", "r2_display_order", "r2_hazard_qualification",
            "etf_flows", "confluence", "bottoming_watch", "theme_table",
            "confluence_universe_sp500", "confluence_universe_nasdaq",
            "confluence_universe_russell", "confluence_universe_baskets", "theme_rows"}
        text = json.dumps(projection)
        for needle in ("roster_clock", "first_known", "membership_snapshot",
                       "taxonomy_revision", "equals_current_roster", "members_sha"):
            assert needle not in text, (audience, needle)
