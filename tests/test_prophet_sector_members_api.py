"""Route-boundary tests for ``GET /api/prophet/sector-members/v1``.

The Sector side is the REAL committed bundle published through the REAL
private-store publisher when the lane-1 reader is on this tree; until it lands
on ``main`` the route's one capture seam (``capture_sector_join``) answers the
SYNTHETIC capture of the same shape (``tests/test_prophet_sector_members.py::
synthetic_capture``).  The Prophet side is the committed
``site/prophet/index.json`` unless a test points elsewhere.  These tests pin the
transport boundary only — auth ordering, the exact query grammar, status
framing, private headers and the Sector reader's four serving rules — not the
join semantics (``tests/test_prophet_sector_members.py`` owns those).

The Sector programme COO's reader rules, one test each:
1. Macro authorizes the caller BEFORE anything is read.
2. One reader; the caller never chooses the generation, path or domain.
3. Responses carry ``Cache-Control: private, no-store``.
4. No row from a paying-member-only block (the four ``confluence_universe_*``
   blocks and ``theme_rows``) reaches a caller — this endpoint emits none of
   them, and because it exposes Prophet state it sits behind
   ``require_site_full_user`` (``app.prophet_lab``), the same dependency the
   Prophet Lab routes use: Supabase bearer auth (``app.main.require_user``)
   then ``app.paywall.enforce_site_full(always=True)`` — the paywall
   ``premium.required_feature: site_full`` entitlement (active, non-free tier,
   ``site_full`` in features; ``config/site_access.yml``).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app import prophet_sector_members as route
from tests.test_prophet_sector_members import LANE1, carried_blocks, synthetic_capture

if LANE1:
    from tests.test_prophet_sector_members import PUBLISHED, _publish, _real_bundle

REPO = Path(__file__).resolve().parents[1]
URL = "/api/prophet/sector-members/v1"

PAYING_MEMBER_BLOCKS = ("confluence_universe_baskets", "confluence_universe_nasdaq",
                        "confluence_universe_russell", "confluence_universe_sp500",
                        "theme_rows")
BLOCK_KEY_TOKENS = ("confluence_universe", "theme_rows", "alloc_rank")


@pytest.fixture(scope="module")
def real_root(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("psm-api")
    if not LANE1:
        return tmp  # the synthetic capture is served through the capture seam
    _, result, root = _publish(tmp, _real_bundle(tmp=tmp), generation_id="psm-api-g1",
                               now=PUBLISHED)
    assert result.status == "published", result.detail
    return root


def _synthetic_seam(monkeypatch, real_root):
    """Without lane 1, the route's ONE capture call answers the synthetic capture —
    and only for the configured root (the caller can never choose another)."""
    def capture(root):
        assert Path(root) == Path(real_root)
        population, capture_facts, baskets, central = synthetic_capture()
        return population, {**capture_facts, "generation_id": "psm-api-g1"}, baskets, central
    monkeypatch.setattr(route, "capture_sector_join", capture)


@pytest.fixture
def client(monkeypatch, real_root):
    monkeypatch.setenv("MACRO_SECTOR_GENERATIONS_ROOT", str(real_root))
    if not LANE1:
        _synthetic_seam(monkeypatch, real_root)
    app = FastAPI()
    app.include_router(route.router)
    app.dependency_overrides[route.require_site_full_user] = lambda: {"uid": "fixture"}
    with TestClient(app) as test_client:
        yield test_client


def private(response):
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Authorization"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-robots-tag"] == "noindex, noarchive"


def _walk(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk(item)
    elif isinstance(node, str):
        yield node


# --- rule 1: Macro authorizes the caller BEFORE anything is read ------------------


def test_denied_caller_never_reaches_an_owner_read(monkeypatch, real_root):
    """401 through the REAL dependency (no bearer → immediate denial, no network):
    auth runs, no owner read runs, and the denial carries the private headers."""
    calls: list[str] = []

    def refused(*_args, **_kwargs):
        calls.append("read")
        pytest.fail("an unauthorized caller must not reach any owner read")

    monkeypatch.setattr(route, "capture_sector_join", refused)
    monkeypatch.setattr(route, "read_prophet_index", refused)
    monkeypatch.setenv("MACRO_SECTOR_GENERATIONS_ROOT", str(real_root))
    app = FastAPI()
    app.include_router(route.router)  # NO dependency override: the real one runs
    with TestClient(app) as test_client:
        response = test_client.get(URL)  # no Authorization header, no session cookie
    assert response.status_code == 401, response.text
    assert calls == []
    private(response)


def test_denied_caller_never_reaches_an_owner_read_403(monkeypatch, real_root):
    calls: list[str] = []

    def refused(*_args, **_kwargs):
        calls.append("read")
        pytest.fail("an unauthorized caller must not reach any owner read")

    monkeypatch.setattr(route, "capture_sector_join", refused)
    monkeypatch.setattr(route, "read_prophet_index", refused)
    monkeypatch.setenv("MACRO_SECTOR_GENERATIONS_ROOT", str(real_root))
    app = FastAPI()
    app.include_router(route.router)

    def denied(_authorization=None):
        calls.append("authenticate")
        raise HTTPException(403, "site_full required")

    app.dependency_overrides[route.require_site_full_user] = denied
    with TestClient(app) as test_client:
        response = test_client.get(URL)
    assert response.status_code == 403, response.text
    assert calls == ["authenticate"]  # auth ran, nothing else did


def test_the_route_declares_the_canonical_site_full_dependency():
    import inspect
    source = (REPO / "app/prophet_sector_members.py").read_text()
    assert "Depends(require_site_full_user)" in source
    assert route.require_site_full_user.__module__ == "app.prophet_lab"
    endpoint = route.router.routes[0].endpoint
    default = inspect.signature(endpoint).parameters["_user"].default
    assert getattr(default, "dependency", None) is route.require_site_full_user


def test_route_is_registered_in_the_composed_app():
    """The app/main.py registration lines are load-bearing: through the REAL
    composed app an unauthenticated caller is denied by the real dependency
    (401 + private headers) before any owner read — never an anonymous 404."""
    from app.main import app as composed  # noqa: PLC0415 — the real wiring, heavy import
    with TestClient(composed) as client:
        response = client.get(URL)
    assert response.status_code == 401, response.text
    private(response)


# --- rule 2: one reader; the caller never chooses generation, path or domain ------


@pytest.mark.parametrize("override", [
    "generation=g2", "generation_id=g2", "path=/private/store", "domain=sector",
    "root=/", "members=sectordata/sector_central.json", "content_id=x",
])
def test_caller_cannot_choose_generation_path_or_domain(client, override):
    response = client.get(f"{URL}?{override}")
    assert response.status_code == 422, response.text
    assert response.json()["error"] == "INVALID_QUERY"
    private(response)


def test_unknown_query_parameter_is_rejected(client):
    response = client.get(f"{URL}?format=verbose")
    assert response.status_code == 422
    private(response)


# --- rule 3: private responses everywhere -----------------------------------------


@pytest.mark.parametrize("path", [
    URL,
    f"{URL}?group=us_sector_industrials",
    f"{URL}?symbol=CARR",
])
def test_every_answer_is_private_no_store(client, path):
    response = client.get(path)
    assert response.status_code == 200, response.text
    private(response)


def test_errors_are_private_too(client):
    private(client.get(f"{URL}?group=no_such_group"))
    private(client.get(f"{URL}?group=BAD_ID"))
    private(client.get(f"{URL}?group=g&symbol=CARR"))
    private(client.get(f"{URL}?limit=0"))
    private(client.get(f"{URL}?state=wat"))


# --- rule 4: no paying-member-only row reaches this endpoint ----------------------


def test_no_paying_member_only_block_or_row_is_emitted(client):
    bodies = [client.get(URL).json(),
              client.get(f"{URL}?group=us_sector_industrials&limit=200").json(),
              client.get(f"{URL}?symbol=CARR").json()]
    # Distinctive values ONLY those blocks produce — never fields whose values
    # are shared with the legitimate basket surface (theme ``name`` comes from
    # the same baskets.json the group descriptor names): theme ``chart_key``
    # (``b-<slug>``) and the confluence universes' subsector slugs/universe ids.
    carried = carried_blocks()
    forbidden_strings = set(BLOCK_KEY_TOKENS)
    for row in carried.get("theme_rows", {}).get("rows", [])[:3]:
        if isinstance(row, dict) and isinstance(row.get("chart_key"), str):
            forbidden_strings.add(row["chart_key"])
    for slug in ("sp500", "nasdaq", "russell", "baskets"):
        data = carried.get(f"confluence_universe_{slug}", {}).get("data", {})
        for entry in (data.get("entry_now") or [])[:3]:
            if isinstance(entry, str):
                forbidden_strings.add(entry)
        if isinstance(data.get("universe"), str):
            forbidden_strings.add(data["universe"])
    for body in bodies:
        emitted = set(_walk(body))
        assert not (forbidden_strings & emitted), \
            forbidden_strings & emitted  # no block name, key or distinctive row value


def test_no_rank_or_score_key_is_emitted_anywhere(client):
    body = client.get(f"{URL}?group=us_sector_industrials&limit=200").json()
    forbidden = {"score", "rank", "alloc_rank", "health", "reco", "grade", "signal_strength"}
    assert not (forbidden & set(_walk(body)))  # descriptive only — no rank/score/gate


# --- the three modes over the real store ------------------------------------------


def test_index_mode_shape(client):
    body = client.get(URL).json()
    committed = json.loads((REPO / "site/prophet/index.json").read_bytes())
    assert body["schema"] == "prophet.sector_members/v1" and body["mode"] == "index"
    assert body["sector_ref"]["generation_id"] == "psm-api-g1"
    assert body["prophet_ref"]["plan_count"] == len(committed["plans"])
    assert body["compatibility"]["status"] in ("compatible", "stale_sector",
                                               "stale_prophet", "mixed_basis")
    assert body["disclosure"]["membership_basis"] == "current_roster_with_pit_first_known"
    if LANE1:
        assert len(body["groups"]) >= 40  # the 49 curated baskets
        assert body["totals"]["served"] > 600
    else:
        assert [g["id"] for g in body["groups"]] == sorted(g["id"] for g in body["groups"])
        assert body["totals"]["served"] > 20


def test_group_mode_shape_and_unknown_group(client):
    body = client.get(f"{URL}?group=us_sector_industrials&limit=5").json()
    assert body["mode"] == "group" and body["group"]["id"] == "us_sector_industrials"
    assert body["group"]["kind"] == "basket"
    assert len(body["members"]) == 5 and body["page"]["next_offset"] == 5
    assert body["counts"]["served"] > (50 if LANE1 else 15)  # whole group, not the page
    unknown = client.get(f"{URL}?group=no_such_group")
    assert unknown.status_code == 404
    # A3-2: ``code`` is what the Terminal BFF reads to tell this refusal from an
    # absent endpoint; ``error`` stays for every other Macro client.
    assert unknown.json() == {"error": "unknown_group", "code": "unknown_group"}


def test_symbol_mode_shape(client):
    body = client.get(f"{URL}?symbol=CARR").json()
    assert body["mode"] == "symbol" and body["symbol"] == "CARR"
    assert body["member_of"] and body["prophet"]["state"]


# --- query grammar -----------------------------------------------------------------


@pytest.mark.parametrize("query", [
    "?group=", "?group=BAD_ID", "?group=" + "x" * 81,
    "?symbol=", "?symbol=../private", "?symbol=" + "X" * 17,
    "?group=g&symbol=CARR", "?offset=-1", "?offset=abc", "?offset=" + "1" * 10,
    "?limit=0", "?limit=201", "?limit=1e2", "?q=", "?q=" + "x" * 65,
    "?q=<script>", "?state=wat", "?group=g&group=g",
])
def test_malformed_queries_are_422(client, query):
    response = client.get(URL + query)
    assert response.status_code == 422, query
    assert response.json()["error"] in ("INVALID_QUERY", "INVALID_PAGE")


def test_valid_edge_queries_pass(client):
    assert client.get(f"{URL}?group=us_sector_industrials&offset=0&limit=1").status_code == 200
    assert client.get(f"{URL}?group=us_sector_industrials&limit=200&q=CARR&state=open_plan"
                      ).status_code == 200
    assert client.get(f"{URL}?symbol=BRK.B").status_code == 200  # dot-form listing ticker


# --- fail-closed envelopes ----------------------------------------------------------


def test_sector_unavailable_still_answers_200_with_honest_envelope(monkeypatch):
    monkeypatch.delenv("MACRO_SECTOR_GENERATIONS_ROOT", raising=False)
    app = FastAPI()
    app.include_router(route.router)
    app.dependency_overrides[route.require_site_full_user] = lambda: {"uid": "fixture"}
    with TestClient(app) as test_client:
        index = test_client.get(URL)
        group = test_client.get(f"{URL}?group=us_sector_industrials")
        symbol = test_client.get(f"{URL}?symbol=CARR")
    for response in (index, group, symbol):
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["sector_ref"] is None
        assert body["compatibility"]["status"] == "sector_unavailable"
        private(response)
    assert index.json()["groups"] == []
    group_body = group.json()  # amendment A1-9: group null, empty members, configured null
    assert group_body["group"] is None and group_body["members"] == []
    assert group_body["counts"]["configured"] is None
    assert group_body["unserved"] == []
    symbol_body = symbol.json()
    assert symbol_body["member_of"] == []
    # The top-level Prophet state is the OTHER owner's own answer — available
    # here even though the sector side is not, so it stays the truthful state.
    from engine.prophet_sector_members import digest_index, prophet_state
    committed = json.loads((REPO / "site/prophet/index.json").read_bytes())
    assert symbol_body["prophet"] == prophet_state("CARR", digest_index(committed), None)


def test_prophet_unavailable_degrades_members_not_the_answer(client, monkeypatch):
    monkeypatch.setattr(route, "_INDEX_PATH", REPO / "not-provisioned/index.json")
    body = client.get(f"{URL}?group=us_sector_industrials&limit=5").json()
    assert body["sector_ref"]["generation_id"] == "psm-api-g1"
    assert body["prophet_ref"] is None
    assert body["compatibility"]["status"] == "prophet_unavailable"
    assert all(m["prophet"]["state"] == "unavailable" for m in body["members"])


def test_corrupt_index_fails_closed_not_partially_joined(client, tmp_path, monkeypatch):
    corrupt = tmp_path / "index.json"
    corrupt.write_text('{"plans": [{"asset": "CARR", "closed": false}], "x": NaN}')
    monkeypatch.setattr(route, "_INDEX_PATH", corrupt)
    body = client.get(f"{URL}?group=us_sector_industrials&limit=5").json()
    assert body["prophet_ref"] is None
    assert body["compatibility"]["status"] == "prophet_unavailable"
    assert all(m["prophet"]["state"] == "unavailable" for m in body["members"])


@pytest.mark.skipif(LANE1, reason="the lane-1 Sector reader is on this tree")
def test_without_the_sector_reader_a_configured_root_still_answers_sector_unavailable(
        monkeypatch, tmp_path):
    """Today's main: the generations root is configured but the Sector reader
    (lane 1) has not landed. The REAL capture call fails closed inside the route —
    every mode answers the designed 200 ``sector_unavailable`` envelope, never a
    500 and never an import failure at app start."""
    monkeypatch.setenv("MACRO_SECTOR_GENERATIONS_ROOT", str(tmp_path))
    app = FastAPI()
    app.include_router(route.router)
    app.dependency_overrides[route.require_site_full_user] = lambda: {"uid": "fixture"}
    with TestClient(app) as test_client:
        for path in (URL, f"{URL}?group=us_sector_industrials", f"{URL}?symbol=CARR"):
            response = test_client.get(path)
            assert response.status_code == 200, response.text
            body = response.json()
            assert body["sector_ref"] is None
            assert body["compatibility"]["status"] == "sector_unavailable"
            private(response)
