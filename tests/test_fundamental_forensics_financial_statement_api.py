"""FIF-3A1 API tests: auth, private headers, golden AAPL statement consumer."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.forensics as forensics_api
from engine.fundamental_forensics.statement_service import GoldenAaplStatementProvider

ROOT = Path(__file__).resolve().parents[1]
_PATH = "/api/forensics/v1/financial/statements"
_SCHEMA = "fundamental_forensics.financial_statement_request/v1"
# Response bytes on the committed byte-copy of the 1.0.0 registry
# (tests/fixtures/fundamental_forensics_registry_v1_0_0). They re-derive
# unchanged; test_registry_v1_0_0_rederives_the_pinned_response_bytes proves it.
_RESPONSE_SHA = "25e5562e81cb80bd42d0feb544c212c4471e11736601aaee418a60981a457184"
# Response bytes on the live registry (mapping pack 1.1.0).
_RESPONSE_SHA_LIVE = "1edd5a13635308930f19634896e196b2362d79562f34e5aad91cb939d189478d"

_EXPECTED_PRIVATE_HEADERS = {
    "cache-control": "private, no-store",
    "vary": "Authorization",
    "x-content-type-options": "nosniff",
    "x-robots-tag": "noindex, noarchive",
}


def _body(
    *,
    entity_id: str = "ISS:US-XNAS-AAPL",
    accession: str = "0000320193-25-000079",
) -> bytes:
    return json.dumps(
        {"schema": _SCHEMA, "entity_id": entity_id, "accession": accession},
        separators=(",", ":"),
    ).encode("utf-8")


def _assert_private_headers(response) -> None:
    for name, expected in _EXPECTED_PRIVATE_HEADERS.items():
        assert response.headers.get(name) == expected, name


def _assert_error(response, status: int, detail: str | None = None) -> None:
    assert response.status_code == status
    _assert_private_headers(response)
    payload = response.json()
    assert "detail" in payload
    if detail is not None:
        assert detail in payload["detail"] or payload["detail"] == detail


@pytest.fixture
def router_app(monkeypatch) -> FastAPI:
    monkeypatch.setattr(forensics_api, "REPO", ROOT)
    app = FastAPI()
    app.include_router(forensics_api.router)
    return app


@pytest.fixture
def anon_client(router_app) -> TestClient:
    with TestClient(router_app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def paid_client(router_app) -> TestClient:
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {"id": "paid-user"}
    with TestClient(router_app, raise_server_exceptions=False) as client:
        yield client


def test_anonymous_post_returns_401_with_private_headers(anon_client, monkeypatch) -> None:
    calls: list[str] = []

    class _P(GoldenAaplStatementProvider):
        def resolve(self, entity_id: str, accession: str):
            calls.append(entity_id)
            raise AssertionError("provider opened before auth")

    monkeypatch.setattr(forensics_api, "_financial_statement_provider", lambda: _P(ROOT))
    response = anon_client.post(_PATH, content=_body(), headers={"content-type": "application/json"})
    assert response.status_code == 401
    _assert_private_headers(response)
    assert calls == []


def test_free_user_returns_403_with_private_headers(router_app, monkeypatch) -> None:
    from fastapi import HTTPException
    import app.main as app_main
    import app.paywall as paywall_mod

    calls: list[str] = []

    class _P(GoldenAaplStatementProvider):
        def resolve(self, entity_id: str, accession: str):
            calls.append(entity_id)
            raise AssertionError("provider opened before entitlement")

    monkeypatch.setattr(forensics_api, "REPO", ROOT)
    monkeypatch.setattr(forensics_api, "_financial_statement_provider", lambda: _P(ROOT))
    monkeypatch.setattr(app_main, "require_user", lambda auth: {"id": "free-user", "tier": "free"})
    monkeypatch.setattr(
        paywall_mod,
        "enforce_site_full",
        lambda user, always=False: (_ for _ in ()).throw(
            HTTPException(status_code=403, detail="site_full required")
        ),
    )
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = client.post(_PATH, content=_body(), headers={"content-type": "application/json"})
    assert response.status_code == 403
    _assert_private_headers(response)
    assert calls == []


def test_paid_golden_aapl_returns_three_statement_trees(paid_client) -> None:
    response = paid_client.post(_PATH, content=_body(), headers={"content-type": "application/json"})
    assert response.status_code == 200
    _assert_private_headers(response)
    assert response.headers.get("x-fif-response-sha256") == _RESPONSE_SHA_LIVE
    assert hashlib.sha256(response.content).hexdigest() == _RESPONSE_SHA_LIVE
    # #9761 follow-up (minor 5): this live pin is the no-cutoff body's bytes —
    # recorded_at stays optional, and absent means the live registry view.
    assert b"recorded_at" not in _body()
    payload = response.json()
    assert payload["schema"] == "fundamental_forensics.financial_statement_response/v1"
    assert payload["entity"]["entity_id"] == "ISS:US-XNAS-AAPL"
    assert payload["entity"]["cik"] == "0000320193"
    assert payload["entity"]["entity_id"] != payload["entity"]["cik"]
    assert payload["filing"]["accession"] == "0000320193-25-000079"
    assert len(payload["statements"]) == 3
    by_type = {item["statement_type"]: item for item in payload["statements"]}
    assert by_type["income_statement"]["row_count"] == 24
    assert by_type["balance_sheet"]["row_count"] == 35
    assert by_type["cash_flow"]["row_count"] == 35
    sales = next(
        row
        for row in by_type["income_statement"]["rows"]
        if row["as_reported_label"] == "Total net sales"
    )
    assert sales["cells"][0]["source_receipt"]["source_span"]
    assert sales["cells"][0]["value"] == "416161000000"
    products = next(
        row
        for row in by_type["income_statement"]["rows"]
        if row["as_reported_label"] == "Products"
        and "RevenueFromContractWithCustomerExcludingAssessedTax" in (row["concept"] or "")
    )
    assert products["cells"][0]["value"] == "307003000000"
    assert products["cells"][0]["dimensions"]
    assert products["standardized_metric_id"] is None
    assert products["mapping_state"] == "unmapped"
    assert sales["standardized_metric_id"] == "revenue"
    assert payload["authority"] == {"class": "context_only", "display_only": True}
    assert payload["delivery"]["kind"] == "committed_golden_fixture"
    assert payload["delivery"]["attested"] is False
    assert payload["delivery"]["production_issuer_service"] is False
    assert "authority" not in payload["delivery"]
    sga = next(
        row
        for row in by_type["income_statement"]["rows"]
        if row["as_reported_label"] == "Selling, general and administrative"
    )
    assert sga["mapping_state"] == "unmapped"
    assert "/api/forensics/v1/financial/trace" not in json.dumps(payload)
    assert "related_event_ref" not in payload
    assert "related_event_ref" not in payload


def test_malformed_json_is_private_400_and_does_not_open_provider(paid_client, monkeypatch) -> None:
    calls: list[str] = []

    class _P(GoldenAaplStatementProvider):
        def resolve(self, entity_id: str, accession: str):
            calls.append(entity_id)
            return super().resolve(entity_id, accession)

    monkeypatch.setattr(forensics_api, "_financial_statement_provider", lambda: _P(ROOT))
    response = paid_client.post(_PATH, content=b"{nope", headers={"content-type": "application/json"})
    _assert_error(response, 400, "malformed")
    assert calls == []


@pytest.mark.parametrize("method", ["GET", "PUT", "PATCH", "DELETE", "HEAD"])
def test_non_post_is_private_405(paid_client, method: str) -> None:
    response = paid_client.request(method, _PATH)
    assert response.status_code == 405
    _assert_private_headers(response)


_Q3_ACCESSION = "0000320193-26-000020"
_Q3_RESPONSE_SHA = "b98602a299996ff7ea58b842364031547df795d1458b51134eef0e37159b7918"
_Q3_RESPONSE_SHA_LIVE = "b55b1592610b436d918b6ded55ed5673a41af2be8673af20ea058ed3bd89ac0a"
_Q3_EVENT_ID = "evt_cik0000320193_2026q3_results"
_Q3_8K_ACCESSION = "0000320193-26-000018"


def test_paid_q3_returns_quarterly_trees_and_event_ref(paid_client) -> None:
    response = paid_client.post(
        _PATH,
        content=_body(accession=_Q3_ACCESSION),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 200
    _assert_private_headers(response)
    assert response.headers.get("x-fif-response-sha256") == _Q3_RESPONSE_SHA_LIVE
    payload = response.json()
    assert payload["filing"]["accession"] == _Q3_ACCESSION
    assert payload["filing"]["form"] == "10-Q"
    by_type = {item["statement_type"]: item for item in payload["statements"]}
    assert by_type["income_statement"]["row_count"] == 24
    assert by_type["balance_sheet"]["row_count"] == 36
    assert by_type["cash_flow"]["row_count"] == 35
    income = by_type["income_statement"]
    assert len(income["columns"]) == 4
    assert income["columns"][0]["end"] == income["columns"][2]["end"]
    assert income["columns"][0]["start"] != income["columns"][2]["start"]
    ref = payload["related_event_ref"]
    assert ref["event_id"] == _Q3_EVENT_ID
    assert ref["source_filing_distinction"]["earnings_release_8k_accession"] == _Q3_8K_ACCESSION
    assert ref["source_filing_distinction"]["periodic_report_accession"] == _Q3_ACCESSION
    assert "generation_id" not in ref
    assert payload["authority"] == {"class": "context_only", "display_only": True}
    assert payload["delivery"]["attested"] is False
    assert payload["delivery"]["production_issuer_service"] is False
    a1 = paid_client.post(_PATH, content=_body(), headers={"content-type": "application/json"})
    assert a1.headers.get("x-fif-response-sha256") == _RESPONSE_SHA_LIVE


def test_paid_results_eight_k_is_unknown_filing(paid_client) -> None:
    response = paid_client.post(
        _PATH,
        content=_body(accession=_Q3_8K_ACCESSION),
        headers={"content-type": "application/json"},
    )
    _assert_error(response, 400, "unknown filing")


# ---------------------------------------------------------------------------
# FIF P1: production statements serve precomputed trees, never a request-path
# parse (F1 remainder / A15+A16 at the HTTP seam).
# ---------------------------------------------------------------------------

from engine.fundamental_forensics import production_datasets as PDS  # noqa: E402
from engine.fundamental_forensics.financial_intelligence_packet import EntityInput  # noqa: E402
from engine.fundamental_forensics.ixbrl_raw_ledger import (  # noqa: E402
    GOLDEN_AAPL_QUERY_ACCESSIONS,
    parse_and_convert_golden_packages,
)
from engine.fundamental_forensics.production_provider import (  # noqa: E402
    ProductionFinancialStatementProvider,
)
from engine.fundamental_forensics.query_service import CanonicalEntityBinding  # noqa: E402
from engine.fundamental_forensics.statement_graph import load_golden_aapl_package  # noqa: E402

_P1_ADMITTED = datetime(2026, 10, 1, tzinfo=timezone.utc)
_P1_ACCESSION = "0000320193-25-000079"


def _p1_statement_provider() -> ProductionFinancialStatementProvider:
    packages = [
        load_golden_aapl_package(ROOT, accession=accession)
        for accession in GOLDEN_AAPL_QUERY_ACCESSIONS
    ]
    ledger, filing_metadata, _report = parse_and_convert_golden_packages(packages)
    material = PDS.ProductionDatasetMaterial(
        binding=CanonicalEntityBinding(
            entity_id="ISS:US-XNAS-AAPL",
            cik="0000320193",
            ticker="AAPL",
            source_entity_id="0000320193",
        ),
        entity=EntityInput(
            entity_id="ISS:US-XNAS-AAPL",
            cik="0000320193",
            ticker="AAPL",
            name="Apple Inc.",
            identity_basis="sec-cik",
            source_entity_id="0000320193",
        ),
        ledger=ledger,
        filing_metadata=filing_metadata,
        registry_payload=PDS.snapshot_core_registry_payload(ROOT),
        admitted_at=_P1_ADMITTED,
        packages=tuple(packages),
        security_id="SEC:US-XNAS-AAPL",
        listing_key="US-XNAS-AAPL",
    )
    store = PDS.InMemoryStrictConditionalStore()
    PDS.publish_production_dataset(store, material)
    return ProductionFinancialStatementProvider(store)


def _p1_paid_statement_client(router_app, monkeypatch, provider) -> TestClient:
    monkeypatch.setenv("FIF_FINANCIAL_DATASET_MODE", "production")
    monkeypatch.setattr(forensics_api, "_production_statement_provider", lambda: provider)
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {"id": "paid-user"}
    return TestClient(router_app, raise_server_exceptions=False)


def test_production_statements_serve_precomputed_trees_without_parsing(
    router_app, monkeypatch
) -> None:
    provider = _p1_statement_provider()

    # Prove the golden factory is never constructed in production mode.
    import engine.fundamental_forensics.statement_service as statement_service_module

    golden_constructions = []

    def _no_golden(*_args, **_kwargs):
        golden_constructions.append(1)
        raise AssertionError("production mode must never construct the golden provider")

    monkeypatch.setattr(statement_service_module, "GoldenAaplStatementProvider", _no_golden)

    # Poison EVERY parse surface after publication has done its work.
    def _forbidden(*_args, **_kwargs):
        raise AssertionError("the production request path must not parse iXBRL")

    import collectors.sec_filing_parser as parser_module
    import engine.fundamental_forensics.statement_graph as statement_graph_module

    monkeypatch.setattr(parser_module, "parse_sec_filing_document", _forbidden)
    monkeypatch.setattr(statement_graph_module, "parse_sec_filing_document", _forbidden)

    with _p1_paid_statement_client(router_app, monkeypatch, provider) as client:
        response = client.post(
            _PATH, content=_body(accession=_P1_ACCESSION), headers={"content-type": "application/json"}
        )
    assert response.status_code == 200, response.text[:400]
    _assert_private_headers(response)
    assert response.headers.get("x-fif-response-sha256") == hashlib.sha256(response.content).hexdigest()
    payload = response.json()
    assert payload["delivery"]["kind"] == "production_issuer_dataset"
    assert payload["delivery"]["attested"] is False
    assert payload["delivery"]["production_issuer_service"] is True
    # Identity is the manifest admission-time block, not a live master.
    assert payload["entity"]["legal_name"] == "Apple Inc."
    assert payload["entity"]["security_id"] == "SEC:US-XNAS-AAPL"
    assert payload["entity"]["listing_key"] == "US-XNAS-AAPL"
    # The trees are the precomputed ones: same three statements the golden
    # fixture reconstructs for this accession.
    by_type = {item["statement_type"]: item for item in payload["statements"]}
    assert by_type["income_statement"]["row_count"] == 24
    assert by_type["balance_sheet"]["row_count"] == 35
    assert by_type["cash_flow"]["row_count"] == 35
    assert golden_constructions == []


def test_production_statements_unknown_entity_is_400(router_app, monkeypatch) -> None:
    provider = _p1_statement_provider()
    with _p1_paid_statement_client(router_app, monkeypatch, provider) as client:
        response = client.post(
            _PATH,
            content=_body(entity_id="ISS:US-XNAS-NOPE"),
            headers={"content-type": "application/json"},
        )
    _assert_error(response, 400, "unknown entity")


def test_production_statement_trees_damage_is_identical_503(router_app, monkeypatch) -> None:
    def _damaged(mutate):
        provider = _p1_statement_provider()
        generation = provider._cached_generation("ISS:US-XNAS-AAPL")
        assert generation is not None
        mutate(provider, generation)
        return provider

    def _drop_trees_object(provider, generation):
        row = next(
            r for r in generation.manifest["objects"] if r["role"] == "statement_trees_json"
        )
        store = provider._store
        store.drop(row["object_key"])

    def _tamper_trees_bytes(provider, generation):
        row = next(
            r for r in generation.manifest["objects"] if r["role"] == "statement_trees_json"
        )
        store = provider._store
        payload = bytearray(store.get_bytes(row["object_key"]))
        payload[0] = payload[0] ^ 0x01
        store.raw_put(row["object_key"], bytes(payload))

    def _legacy_generation_without_role(provider, generation):
        # A generation published before the role existed (or whose payload
        # was lost): servable packages, no trees — never a parse fallback.
        del generation.role_payloads["statement_trees_json"]

    details = set()
    for mutate in (_drop_trees_object, _tamper_trees_bytes, _legacy_generation_without_role):
        provider = _damaged(mutate)
        with _p1_paid_statement_client(router_app, monkeypatch, provider) as client:
            response = client.post(
                _PATH,
                content=_body(accession=_P1_ACCESSION),
                headers={"content-type": "application/json"},
            )
        assert response.status_code == 503, mutate.__name__
        details.add((response.status_code, response.json()["detail"]))
    # Identical detail for every damage class: no corpus-state oracle.
    assert details == {(503, "financial statements temporarily unavailable")}


# ---------------------------------------------------------------------------
# Registry drift: the 1.0.0 registry re-derives the pinned bytes, and the live
# registry differs from it in exactly one leaf per golden filing.
# ---------------------------------------------------------------------------

_REGISTRY_V1_0_0_ROOT = ROOT / "tests" / "fixtures" / "fundamental_forensics_registry_v1_0_0"
_LSE_RECEIPT = {
    "concept": "LiabilitiesAndStockholdersEquity",
    "governing_concept": "Assets",
    "governing_priority": 10,
    "metric_id": "total_assets",
    "priority": 20,
    "reason": "alias_priority",
    "taxonomy": "us-gaap",
}


def _leaf_diff(old, new, path, out) -> None:
    if type(old) is not type(new):
        out.append((path, old, new))
    elif isinstance(old, dict):
        for key in sorted(set(old) | set(new)):
            if key not in old or key not in new:
                out.append((f"{path}.{key}", old.get(key, "<absent>"), new.get(key, "<absent>")))
            else:
                _leaf_diff(old[key], new[key], f"{path}.{key}", out)
    elif isinstance(old, list):
        if len(old) != len(new):
            out.append((f"{path}[len]", len(old), len(new)))
        for index, (a, b) in enumerate(zip(old, new)):
            _leaf_diff(a, b, f"{path}[{index}]", out)
    elif old != new:
        out.append((path, old, new))


@pytest.mark.parametrize(
    ("accession", "pinned", "live", "row"),
    [
        (None, _RESPONSE_SHA, _RESPONSE_SHA_LIVE, 34),
        (_Q3_ACCESSION, _Q3_RESPONSE_SHA, _Q3_RESPONSE_SHA_LIVE, 35),
    ],
)
def test_registry_v1_0_0_rederives_the_pinned_response_bytes(
    paid_client, monkeypatch, accession, pinned, live, row
) -> None:
    import engine.fundamental_forensics.statement_service as statement_service
    from engine.fundamental_forensics.financial_intelligence_packet import load_core_registry

    body = _body() if accession is None else _body(accession=accession)
    headers = {"content-type": "application/json"}
    live_response = paid_client.post(_PATH, content=body, headers=headers)
    assert live_response.status_code == 200
    assert hashlib.sha256(live_response.content).hexdigest() == live
    monkeypatch.setattr(
        statement_service,
        "load_core_registry",
        lambda _repo_root: load_core_registry(_REGISTRY_V1_0_0_ROOT),
    )
    old_response = paid_client.post(_PATH, content=body, headers=headers)
    assert old_response.status_code == 200
    assert old_response.headers.get("x-fif-response-sha256") == pinned
    assert hashlib.sha256(old_response.content).hexdigest() == pinned
    old_payload, live_payload = old_response.json(), live_response.json()
    diffs: list = []
    _leaf_diff(old_payload, live_payload, "$", diffs)
    assert diffs == [(f"$.statements[1].rows[{row}].mapping_receipt", None, _LSE_RECEIPT)]
    assert live_payload["statements"][1]["statement_type"] == "balance_sheet"
    assert live_payload["statements"][1]["rows"][row]["concept"] == (
        "us-gaap:LiabilitiesAndStockholdersEquity"
    )
