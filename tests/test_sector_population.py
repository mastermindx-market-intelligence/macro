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


def _real_bundle(*, drop_member: tuple[str, str] | None = None, tmp: Path,
                 carried: bool = True):
    """Real bytes -> (member bytes, identity); optionally derive an advanced generation."""
    baskets_raw = _real("basketdata/baskets.json")
    if drop_member is not None:
        baskets = json.loads(baskets_raw)
        group = next(g for g in baskets["baskets"] if g["id"] == drop_member[0])
        group["members"] = [m for m in group["members"] if m["symbol"] != drop_member[1]]
        group["n_members"] = len(group["members"])
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
        from lib.sector_central_carry import build_carry
        central["carried"] = build_carry(REPO / "site", central)
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
        assert page["capture"]["population"]["complete"] is True
        assert page["capture"]["population"]["admitted"] == 1015
        assert page["capture"]["population"]["expected"] == 1015
        # REAL: the owner reports 2 listed members without a usable measurement;
        # they stay listed and are counted, never silently dropped.
        assert page["capture"]["population"]["missing"] == 2
        assert page["total_matching"] == 1015
    # Prophet eligibility is a separate, honestly unproduced concept.
    assert {json.dumps(r["prophet_eligibility"], sort_keys=True) for r in rows} == {
        '{"reason": "not_produced", "status": "unavailable"}'}
    assert not re.search(r"\bNaN\b|Infinity", "".join(r.text for r, _ in pages))


def test_industry_is_current_basis_not_point_in_time_and_never_relabelled(real_store):
    """REAL inputs, NEW carry code: every row carries a labelled industry state."""
    client = _client(real_store["reader"])
    pages = _all_pages(client)
    classification = pages[0][1]["capture"]["identity"]["industry_classification"]
    assert classification["status"] == "available"
    assert classification["point_in_time"] is False
    assert classification["basis"] == "current_sp500_membership_not_point_in_time"
    assert classification["source"] == "marketdata/subsector_confluence.json"
    rows = [r for _, p in pages for r in p["rows"]]
    states = {r["industry"]["status"] for r in rows}
    assert states == {"available", "unavailable"}  # real: 424 of 698 symbols classified
    classified = {r["symbol"] for r in rows if r["industry"]["status"] == "available"}
    assert len(classified) == 424
    app_row = next(r for r in rows if r["symbol"] == "APP")
    assert app_row["industry"]["key"] == "software-application"
    assert app_row["industry"]["label"] == "Software - Application"
    assert all(r["industry"] == {"status": "unavailable", "reason": "not_in_current_classification"}
               for r in rows if r["symbol"] not in classified)
    # Point-in-time identity is NOT satisfied and stays recorded as unavailable.
    identity = pages[0][1]["capture"]["identity"]
    assert identity["membership_first_known"]["status"] == "unavailable"
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
    tampered = cursor[:-1] + ("0" if cursor[-1] != "0" else "1")
    assert client.get(URL, params={**base, "cursor": tampered}, cookies=COOKIE).status_code == 400
    assert client.get(URL, params={**base, "cursor": "not a token"}, cookies=COOKIE).status_code == 400
    # A different actor cannot continue (or open the reference of) another actor's capture.
    import app.main as macro_main
    original = macro_main._mm_verify_uid_cached
    macro_main._mm_verify_uid_cached = lambda token: "22222222-2222-2222-2222-222222222222"
    try:
        other = client.get(URL, params=base, cookies=COOKIE)
    finally:
        macro_main._mm_verify_uid_cached = original
    assert other.status_code == 409 and other.json()["reason"] == "binding_changed"


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
    assert original["capture"]["population"]["admitted"] == 1015


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
