# FIF PF r1 server suite: the health pointer header, the entity-id grammar
# parity with lib.dataos.identity, the repeated-parameter rule, and the
# statement-period date strings the server's own parser accepts.
#
# R2: production mode with exactly one well-formed entity_id answers ONE
# names-only header — X-FIF-Dataset-Pointer: admitted | none | unavailable —
# alongside today's generation headers. 'none' means the store was built, the
# lookup did not raise and the pointer is absent; 'unavailable' means the
# store is None or building/reading raised (the provider's own contract: a
# damaged store is temporarily unavailable, not "not published"). The absent
# parameter and golden mode stay byte for byte unchanged: no pointer header.
# The JSON body is identical in every case.
#
# R3: the health id grammar accepts a code exactly when identity's code
# grammar does ('BRK-B' is a real class suffix), under the 128-byte bound.
#
# R4: a repeated entity_id is malformed — no generation or pointer headers,
# status 200, the same body, the store never opened.
from __future__ import annotations

from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.forensics as forensics_api
import lib.dataos.identity as identity

AAPL_ID = "ISS:US-XNAS-AAPL"
MSFT_ID = "ISS:US-XNAS-MSFT"
HEALTH_PATH = "/api/forensics/health"

_HEALTH_BODY = {
    "schema": "fundamental_forensics.health/v1",
    "status": "current",
    "reason_code": "SOURCE_CURRENT",
    "age_seconds": 1,
    "clocks": {"broad_source_at": "2026-10-11T00:00:00Z"},
}

_EXPECTED_PRIVATE_HEADERS = {
    "cache-control": "private, no-store",
    "vary": "Authorization",
    "x-content-type-options": "nosniff",
    "x-robots-tag": "noindex, noarchive",
}


def _assert_private_headers(response) -> None:
    for name, expected in _EXPECTED_PRIVATE_HEADERS.items():
        assert response.headers.get(name) == expected, f"Missing or wrong header {name!r}"


@pytest.fixture
def router_app(monkeypatch) -> FastAPI:
    monkeypatch.setattr(forensics_api, "REPO", "/nonexistent-repo")
    app = FastAPI()
    app.include_router(forensics_api.router)
    app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {"id": "paid-user"}
    return app


class _StoreStub:
    """Stands in for a built production store."""


_BUILD_DEFAULT = object()


def _production_summary_stub(
    monkeypatch,
    summaries: dict[str, dict | None],
    *,
    build: object = _BUILD_DEFAULT,
    builds: list | None = None,
):
    """Patch the production module the route imports; record every issuer id.

    ``build``: a callable/call result for the store (``None`` means the store
    is None), or the sentinel for the default built store.
    ``builds``: when given, every store-builder call appends to it, so a test
    can pin that the store was never built (not only never read).
    """
    import engine.fundamental_forensics.production_datasets as pds_module

    requested: list[str] = []

    def _build(*_args, **_kwargs):
        if builds is not None:
            builds.append("build")
        if build is not _BUILD_DEFAULT:
            return build() if callable(build) else build
        return _StoreStub()

    def _summary(_store, issuer_id: str):
        requested.append(issuer_id)
        summary = summaries.get(issuer_id)
        if callable(summary):
            return summary()
        return summary

    monkeypatch.setattr(pds_module, "build_production_dataset_store", _build)
    monkeypatch.setattr(pds_module, "latest_generation_summary", _summary)
    return requested


def _aapl_summary() -> dict:
    return {
        "dataset_generation_id": "ffprods_" + "a" * 64,
        "admitted_at": "2026-10-13T02:00:00.000000Z",
    }


def _get(client: TestClient, query: str | None):
    url = HEALTH_PATH if query is None else f"{HEALTH_PATH}?{query}"
    return client.get(url)


def _production(monkeypatch) -> None:
    monkeypatch.setattr(forensics_api, "evaluate_health", lambda _root, **_kw: dict(_HEALTH_BODY))
    monkeypatch.setenv("FIF_FINANCIAL_DATASET_MODE", "production")


# ── R2: the three pointer values ────────────────────────────────────────────


def test_pointer_admitted_when_a_summary_is_returned(monkeypatch, router_app):
    _production(monkeypatch)
    _production_summary_stub(monkeypatch, {MSFT_ID: _aapl_summary()})
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = _get(client, f"entity_id={MSFT_ID}")
    assert response.status_code == 200
    _assert_private_headers(response)
    assert response.headers["x-fif-financial-dataset-mode"] == "production"
    assert response.headers["x-fif-dataset-pointer"] == "admitted"
    assert response.headers["x-fif-dataset-generation-id"] == _aapl_summary()["dataset_generation_id"]
    assert response.headers["x-fif-dataset-admitted-at"] == _aapl_summary()["admitted_at"]
    assert response.json() == _HEALTH_BODY


def test_pointer_none_when_the_store_is_built_and_the_pointer_is_absent(monkeypatch, router_app):
    _production(monkeypatch)
    # AAPL has a pointer; the asked-for issuer does not — the store IS built.
    requested = _production_summary_stub(monkeypatch, {AAPL_ID: _aapl_summary()})
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = _get(client, f"entity_id={MSFT_ID}")
    assert response.status_code == 200
    _assert_private_headers(response)
    assert response.headers["x-fif-dataset-pointer"] == "none"
    assert "x-fif-dataset-generation-id" not in response.headers
    assert "x-fif-dataset-admitted-at" not in response.headers
    assert requested == [MSFT_ID], "the lookup did happen; the pointer is genuinely absent"
    assert response.json() == _HEALTH_BODY


def test_pointer_unavailable_when_the_store_is_none(monkeypatch, router_app):
    _production(monkeypatch)
    requested = _production_summary_stub(monkeypatch, {MSFT_ID: _aapl_summary()}, build=None)
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = _get(client, f"entity_id={MSFT_ID}")
    assert response.status_code == 200
    _assert_private_headers(response)
    assert response.headers["x-fif-dataset-pointer"] == "unavailable"
    assert "x-fif-dataset-generation-id" not in response.headers
    assert requested == [], "no store means no lookup"
    assert response.json() == _HEALTH_BODY


def test_pointer_unavailable_when_building_the_store_raises(monkeypatch, router_app):
    _production(monkeypatch)

    def _boom():
        raise OSError("unreadable store directory")

    _production_summary_stub(monkeypatch, {}, build=_boom)
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = _get(client, f"entity_id={MSFT_ID}")
    assert response.status_code == 200
    assert response.headers["x-fif-dataset-pointer"] == "unavailable"
    assert "x-fif-dataset-generation-id" not in response.headers
    assert "OSError" not in response.text
    assert response.json() == _HEALTH_BODY


def test_pointer_unavailable_when_reading_the_summary_raises(monkeypatch, router_app):
    _production(monkeypatch)

    def _damaged_pointer(_store, _issuer_id):
        raise ValueError("damaged pointer")

    import engine.fundamental_forensics.production_datasets as pds_module

    monkeypatch.setattr(pds_module, "build_production_dataset_store", lambda: _StoreStub())
    monkeypatch.setattr(pds_module, "latest_generation_summary", _damaged_pointer)
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = _get(client, f"entity_id={MSFT_ID}")
    assert response.status_code == 200
    assert response.headers["x-fif-dataset-pointer"] == "unavailable", "a damaged pointer is unavailable, not none"
    assert "x-fif-dataset-generation-id" not in response.headers
    assert "ValueError" not in response.text
    assert response.json() == _HEALTH_BODY


# ── R2: the unchanged paths carry no pointer header ─────────────────────────


def test_absent_parameter_serves_generation_headers_but_no_pointer(monkeypatch, router_app):
    _production(monkeypatch)
    requested = _production_summary_stub(monkeypatch, {AAPL_ID: _aapl_summary()})
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = _get(client, None)
    assert response.status_code == 200
    assert response.headers["x-fif-dataset-generation-id"] == _aapl_summary()["dataset_generation_id"]
    assert "x-fif-dataset-pointer" not in response.headers, "the absent path is byte for byte today's"
    assert requested == [AAPL_ID]


def test_golden_mode_with_the_parameter_has_no_pointer_header(monkeypatch, router_app):
    monkeypatch.setattr(forensics_api, "evaluate_health", lambda _root, **_kw: dict(_HEALTH_BODY))
    monkeypatch.delenv("FIF_FINANCIAL_DATASET_MODE", raising=False)
    requested = _production_summary_stub(monkeypatch, {MSFT_ID: _aapl_summary()})
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = _get(client, f"entity_id={MSFT_ID}")
    assert response.status_code == 200
    assert response.headers["x-fif-financial-dataset-mode"] == "golden"
    assert "x-fif-dataset-pointer" not in response.headers
    assert "x-fif-dataset-generation-id" not in response.headers
    assert requested == []
    assert response.json() == _HEALTH_BODY


@pytest.mark.parametrize(
    "query",
    [
        "entity_id=../x",
        "entity_id=",
        "entity_id=" + "A" * 200,
    ],
)
def test_malformed_id_gets_no_pointer_header(monkeypatch, router_app, query):
    _production(monkeypatch)
    requested = _production_summary_stub(monkeypatch, {AAPL_ID: _aapl_summary()})
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = _get(client, query)
    assert response.status_code == 200
    assert response.headers["x-fif-financial-dataset-mode"] == "production"
    assert "x-fif-dataset-pointer" not in response.headers
    assert "x-fif-dataset-generation-id" not in response.headers
    assert requested == []
    assert response.json() == _HEALTH_BODY


def test_the_json_body_is_identical_across_every_pointer_case(monkeypatch, router_app):
    _production(monkeypatch)

    def _store_down():
        raise RuntimeError("store down")

    _production_summary_stub(monkeypatch, {}, build=_store_down)
    with TestClient(router_app, raise_server_exceptions=False) as client:
        cases = [
            _get(client, None).text,
            _get(client, f"entity_id={MSFT_ID}").text,  # unavailable (build raises)
            _get(client, f"entity_id={AAPL_ID}").text,
            _get(client, "entity_id=ISS%3AUS-XNAS-NOPE").text,
            _get(client, "entity_id=../x").text,
            _get(client, f"entity_id={MSFT_ID}&entity_id={AAPL_ID}").text,
        ]
    assert len(set(cases)) == 1, "the body never varies, only the headers do"


# ── R4: a repeated parameter is malformed ───────────────────────────────────


def test_repeated_entity_id_answers_200_with_no_headers_and_never_opens_the_store(
    monkeypatch, router_app
):
    _production(monkeypatch)
    requested = _production_summary_stub(monkeypatch, {AAPL_ID: _aapl_summary(), MSFT_ID: _aapl_summary()})
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = _get(client, f"entity_id={MSFT_ID}&entity_id={AAPL_ID}")
    assert response.status_code == 200, "a repeated key is never a 4xx/5xx"
    _assert_private_headers(response)
    assert response.headers["x-fif-financial-dataset-mode"] == "production"
    assert "x-fif-dataset-generation-id" not in response.headers
    assert "x-fif-dataset-admitted-at" not in response.headers
    assert "x-fif-dataset-pointer" not in response.headers, "no silent choice of one value"
    assert requested == [], "neither value reaches a store key"
    assert response.json() == _HEALTH_BODY


# ── R7: the byte-bound check protects the store key path ────────────────────


def _issuer_grammar_tail(byte_count: int) -> str:
    """Build a grammar-matching issuer id of exactly ``byte_count`` UTF-8 bytes.

    The grammar (``_HEALTH_ENTITY_ID_RE``) is ``ISS:[A-Z]{2}-[A-Z0-9]{4}-
    [A-Z0-9][A-Z0-9.\\-]*``: 12 bytes of head plus a mandatory first
    alphanumeric byte plus any non-empty alphanumeric/./- tail. We round the
    head out to the bound with ``A`` so the value always full-matches the
    grammar (every char is in ``[A-Z0-9.-]``), and the length is read off the
    bound rather than hand-counted.
    """
    head = "ISS:US-XNAS-"
    head_bytes = len(head.encode("utf-8"))  # 12
    mandatory = 1  # the grammar requires one more alphanumeric byte
    minimum = head_bytes + mandatory
    if byte_count < minimum:
        raise ValueError("byte_count must cover the mandatory grammar head")
    tail = "A" * (byte_count - minimum)
    value = head + "A" + tail
    assert len(value.encode("utf-8")) == byte_count
    assert forensics_api._HEALTH_ENTITY_ID_RE.fullmatch(value), (
        "an over-length grammar-matching id must still match the grammar"
    )
    return value


def test_over_length_grammar_matching_id_is_malformed_and_never_opens_the_store(
    monkeypatch, router_app
):
    _production(monkeypatch)
    builds: list[str] = []
    requested = _production_summary_stub(
        monkeypatch, {AAPL_ID: _aapl_summary()}, builds=builds
    )
    over_length = _issuer_grammar_tail(forensics_api._MAX_QUERY_VALUE_BYTES + 1)
    assert len(over_length.encode("utf-8")) > forensics_api._MAX_QUERY_VALUE_BYTES
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = _get(client, f"entity_id={over_length}")
    assert response.status_code == 200, "an over-length id is never a 4xx/5xx"
    _assert_private_headers(response)
    assert response.headers["x-fif-financial-dataset-mode"] == "production"
    assert "x-fif-dataset-pointer" not in response.headers
    assert "x-fif-dataset-generation-id" not in response.headers
    assert "x-fif-dataset-admitted-at" not in response.headers
    assert builds == [], "the byte-bound check runs before the store is built"
    assert requested == [], "the byte-bound check runs before any store key lookup"
    assert response.json() == _HEALTH_BODY


def test_id_exactly_at_the_byte_bound_that_matches_the_grammar_is_accepted(
    monkeypatch, router_app
):
    _production(monkeypatch)
    at_bound = _issuer_grammar_tail(forensics_api._MAX_QUERY_VALUE_BYTES)
    assert len(at_bound.encode("utf-8")) == forensics_api._MAX_QUERY_VALUE_BYTES
    builds: list[str] = []
    requested = _production_summary_stub(
        monkeypatch, {at_bound: _aapl_summary()}, builds=builds
    )
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = _get(client, f"entity_id={at_bound}")
    assert response.status_code == 200
    _assert_private_headers(response)
    assert response.headers["x-fif-financial-dataset-mode"] == "production"
    assert response.headers["x-fif-dataset-pointer"] == "admitted"
    assert (
        response.headers["x-fif-dataset-generation-id"]
        == _aapl_summary()["dataset_generation_id"]
    )
    assert response.headers["x-fif-dataset-admitted-at"] == _aapl_summary()["admitted_at"]
    assert builds == ["build"]
    assert requested == [at_bound]
    assert response.json() == _HEALTH_BODY


# ── R3: parity with the canonical issuer grammar ────────────────────────────


def _health_accepts(value: str) -> bool:
    """The route's own acceptance rule: byte bound first, then a full match."""
    if len(value.encode("utf-8")) > forensics_api._MAX_QUERY_VALUE_BYTES:
        return False
    return bool(forensics_api._HEALTH_ENTITY_ID_RE.fullmatch(value))


@pytest.mark.parametrize(
    "code",
    ["BRK-B", "BRK.B", "MMC.2", "A", "X" * 100],
)
def test_health_id_accepts_exactly_the_identity_code_grammar(code):
    assert bool(identity._CODE_RE.match(code)), "fixture premise: identity accepts this code"
    entity_id = "ISS:US-XNYS-" + code
    assert _health_accepts(entity_id), f"a real class code must reach the store: {entity_id}"
    assert len(entity_id.encode("utf-8")) <= forensics_api._MAX_QUERY_VALUE_BYTES


def test_health_id_grammar_parity_with_identity():
    codes = ["BRK-B", "BRK.B", "MMC.2", "A", "X" * 100, "aapl", "BRK_", "BRK B", "-BRK", "", "B" * 200]
    for code in codes:
        expected = bool(identity._CODE_RE.match(code)) and len(("ISS:US-XNYS-" + code).encode("utf-8")) <= 128
        assert _health_accepts("ISS:US-XNYS-" + code) is expected, f"parity drift for {code!r}"


@pytest.mark.parametrize(
    "value",
    [
        "../x",
        "ISS:US-XNAS-AAPL/../B",
        "",
        "ISS:US-XNYS-" + "A" * 200,
        "iss:us-xnas-aapl",
        "ISS:US-XNAS-aapl",
        "ISS:US-XNAS-AAPL\n",
    ],
)
def test_health_id_refuses_the_adversarial_shapes(value):
    assert not _health_accepts(value)


# ── R6: the period date strings the page emits are the parser's own ─────────


def test_statement_period_dates_are_the_strings_the_servers_parser_accepts():
    # The exact date set the page's statement columns emit (pinned end to end in
    # the page suite); every one must parse through the same date.fromisoformat
    # the server's period admission uses (query_service → _parse_date).
    emitted = [
        "2021-10-01", "2022-09-28", "2022-10-01", "2023-09-30",
        "2023-10-01", "2024-09-28", "2024-09-29", "2025-09-27",
    ]
    for value in emitted:
        assert isinstance(value, str)
        assert date.fromisoformat(value).isoformat() == value
