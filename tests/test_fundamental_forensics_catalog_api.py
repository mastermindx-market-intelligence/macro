"""FIF financial catalog: the statement filings an admitted generation serves.

The page's company panel is a snapshot; this route lists, from the same
immutable generation the statements route resolves against, exactly the
accessions ``/financial/statements`` can serve. Covers the adapter contract,
the production provider over the published AAPL generation, the private HTTP
surface, and the catalog -> statements round trip.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.forensics as forensics_api
from engine.fundamental_forensics.catalog_service import (
    admit_catalog_request,
    execute_financial_catalog,
)
from engine.fundamental_forensics.query_service import (
    FinancialQueryAdmissionError,
    FinancialQueryUnavailableError,
)
from tests.test_fundamental_forensics_financial_query_api import (
    _assert_private_headers,
    _p1_aapl_material,
)

ROOT = Path(__file__).resolve().parents[1]
_CATALOG_PATH = "/api/forensics/v1/financial/catalog"
_STATEMENTS_PATH = "/api/forensics/v1/financial/statements"
_ENTITY = "ISS:US-XNAS-AAPL"
_CIK = "0000320193"


def _body(entity_id: str = _ENTITY, **extra) -> bytes:
    payload = {"schema": "fundamental_forensics.financial_catalog_request/v1", "entity_id": entity_id}
    payload.update(extra)
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


@pytest.fixture(scope="module")
def aapl_store():
    from engine.fundamental_forensics import production_datasets as PDS

    store = PDS.InMemoryStrictConditionalStore()
    PDS.publish_production_dataset(store, _p1_aapl_material())
    return store


@pytest.fixture
def aapl_provider(aapl_store):
    from engine.fundamental_forensics.production_provider import ProductionFinancialStatementProvider

    return ProductionFinancialStatementProvider(aapl_store)


@pytest.fixture
def listing(aapl_provider) -> dict:
    return aapl_provider.catalog(_ENTITY)


class _ListingProvider:
    def __init__(self, listing: dict) -> None:
        self._listing = listing

    def catalog(self, entity_id: str):
        return self._listing


# ---------------------------------------------------------------------------
# Admission
# ---------------------------------------------------------------------------


def test_admission_accepts_exact_contract() -> None:
    assert admit_catalog_request(_body()) == _ENTITY


@pytest.mark.parametrize(
    "body",
    [
        _body(extra_field=1),
        json.dumps({"schema": "fundamental_forensics.financial_statement_request/v1", "entity_id": _ENTITY}).encode(),
        _body(entity_id=""),
        json.dumps({"schema": "fundamental_forensics.financial_catalog_request/v1", "entity_id": 7}).encode(),
        json.dumps({"schema": "fundamental_forensics.financial_catalog_request/v1"}).encode(),
    ],
)
def test_admission_rejects_contract_violations(body: bytes) -> None:
    with pytest.raises(FinancialQueryAdmissionError) as excinfo:
        admit_catalog_request(body)
    assert excinfo.value.status_code == 400


def test_admission_precedes_provider_construction() -> None:
    def _factory():
        raise AssertionError("provider built before admission")

    with pytest.raises(FinancialQueryAdmissionError):
        execute_financial_catalog(body=_body(extra_field=1), provider_factory=_factory)


# ---------------------------------------------------------------------------
# Production provider over the published AAPL generation
# ---------------------------------------------------------------------------


def test_production_catalog_lists_exactly_the_admitted_accessions(aapl_provider) -> None:
    from engine.fundamental_forensics.ixbrl_raw_ledger import GOLDEN_AAPL_QUERY_ACCESSIONS

    listing = aapl_provider.catalog(_ENTITY)
    assert listing["entity_id"] == _ENTITY
    assert listing["cik"] == _CIK
    accessions = [row["accession"] for row in listing["filings"]]
    assert sorted(accessions) == sorted(GOLDEN_AAPL_QUERY_ACCESSIONS)
    for row in listing["filings"]:
        assert row["entity_id"] == _ENTITY and row["cik"] == _CIK
        assert row["form"] and row["period_of_report"] and row["filing_date"]


def test_production_catalog_agrees_with_statement_accessions(aapl_provider) -> None:
    listing = aapl_provider.catalog(_ENTITY)
    generation = aapl_provider._cached_generation(_ENTITY)
    assert generation is not None
    assert generation.generation_id == listing["dataset_generation_id"]
    assert [row["accession"] for row in listing["filings"]] == list(generation.statement_accessions())


def test_production_catalog_unknown_entity_is_400(aapl_provider) -> None:
    with pytest.raises(FinancialQueryAdmissionError) as excinfo:
        aapl_provider.catalog("ISS:US-XNAS-NOPE")
    assert excinfo.value.status_code == 400


# ---------------------------------------------------------------------------
# Adapter contract (fake provider fed the real listing, then damaged)
# ---------------------------------------------------------------------------


def test_adapter_envelope_is_sorted_context_only_and_hashed(listing) -> None:
    shuffled = copy.deepcopy(listing)
    shuffled["filings"] = list(reversed(shuffled["filings"]))
    result = execute_financial_catalog(body=_body(), provider=_ListingProvider(shuffled))
    envelope = json.loads(result.body)
    assert envelope == result.envelope
    assert envelope["schema"] == "fundamental_forensics.financial_catalog_response/v1"
    assert envelope["entity"] == {"entity_id": _ENTITY, "cik": _CIK}
    assert envelope["authority"] == {"class": "context_only", "display_only": True}
    assert envelope["delivery"]["kind"] == "production_issuer_dataset"
    keys = [(row["filing_date"], row["accession"]) for row in envelope["filings"]]
    assert keys == sorted(keys)
    assert result.sha256 == hashlib.sha256(result.body).hexdigest()
    # Deterministic: input order does not leak into the bytes.
    again = execute_financial_catalog(body=_body(), provider=_ListingProvider(listing))
    assert again.body == result.body


def test_adapter_without_provider_or_catalog_is_unavailable() -> None:
    with pytest.raises(FinancialQueryUnavailableError):
        execute_financial_catalog(body=_body())

    class _NoCatalog:
        def resolve(self, entity_id, accession):  # pragma: no cover - never called
            raise AssertionError

    with pytest.raises(FinancialQueryUnavailableError):
        execute_financial_catalog(body=_body(), provider=_NoCatalog())


def _damage_entity(listing):
    listing["entity_id"] = "ISS:US-XNAS-MSFT"


def _damage_row_identity(listing):
    listing["filings"][0]["cik"] = "0000789019"


def _damage_duplicate(listing):
    listing["filings"].append(dict(listing["filings"][0]))


def _damage_missing_field(listing):
    del listing["filings"][0]["form"]


def _damage_accepted_at(listing):
    listing["filings"][0]["source_accepted_at"] = ""


def _damage_no_delivery(listing):
    listing["delivery"] = None


def _damage_bad_delivery(listing):
    listing["delivery"] = {"kind": "production_issuer_dataset"}


def _damage_generation(listing):
    listing["dataset_generation_id"] = ""


def _damage_filings_type(listing):
    listing["filings"] = "0000320193-25-000079"


@pytest.mark.parametrize(
    "damage",
    [
        _damage_entity,
        _damage_row_identity,
        _damage_duplicate,
        _damage_missing_field,
        _damage_accepted_at,
        _damage_no_delivery,
        _damage_bad_delivery,
        _damage_generation,
        _damage_filings_type,
    ],
)
def test_adapter_fail_closes_damaged_listings(listing, damage) -> None:
    damaged = copy.deepcopy(listing)
    damage(damaged)
    with pytest.raises(FinancialQueryUnavailableError):
        execute_financial_catalog(body=_body(), provider=_ListingProvider(damaged))


# ---------------------------------------------------------------------------
# HTTP surface
# ---------------------------------------------------------------------------


@pytest.fixture
def router_app(monkeypatch) -> FastAPI:
    monkeypatch.setattr(forensics_api, "REPO", ROOT)
    app = FastAPI()
    app.include_router(forensics_api.router)
    return app


def test_anonymous_catalog_is_private_401(router_app) -> None:
    with TestClient(router_app, raise_server_exceptions=False) as client:
        for method in ("POST", "GET"):
            response = client.request(method, _CATALOG_PATH, content=_body())
            assert response.status_code == 401, method
            _assert_private_headers(response)


def test_entitled_wrong_methods_are_private_405(router_app) -> None:
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {"id": "paid-user"}
    with TestClient(router_app, raise_server_exceptions=False) as client:
        for method in ("GET", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE"):
            response = client.request(method, _CATALOG_PATH)
            assert response.status_code == 405, method
            _assert_private_headers(response)


def test_golden_wiring_has_no_catalog_and_answers_private_503(router_app, monkeypatch) -> None:
    monkeypatch.delenv("FIF_FINANCIAL_DATASET_MODE", raising=False)
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {"id": "paid-user"}
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = client.post(_CATALOG_PATH, content=_body(), headers={"content-type": "application/json"})
    assert response.status_code == 503
    _assert_private_headers(response)
    assert response.json()["detail"] == "financial catalog temporarily unavailable"


def test_production_catalog_http_bytes_equal_adapter_and_round_trip(router_app, monkeypatch, aapl_provider) -> None:
    from engine.fundamental_forensics.statement_service import execute_financial_statements

    monkeypatch.setenv("FIF_FINANCIAL_DATASET_MODE", "production")
    monkeypatch.setattr(forensics_api, "_production_statement_provider", lambda: aapl_provider)
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {"id": "paid-user"}
    expected = execute_financial_catalog(body=_body(), provider_factory=lambda: aapl_provider)
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = client.post(_CATALOG_PATH, content=_body(), headers={"content-type": "application/json"})
        assert response.status_code == 200, response.text[:200]
        _assert_private_headers(response)
        assert response.content == expected.body
        assert response.headers["x-fif-response-sha256"] == expected.sha256
        assert expected.sha256 == hashlib.sha256(response.content).hexdigest()

        unknown = client.post(
            _CATALOG_PATH, content=_body("ISS:US-XNAS-NOPE"), headers={"content-type": "application/json"}
        )
        assert unknown.status_code == 400
        _assert_private_headers(unknown)

        # Every listed accession is one the statements route serves.
        filings = json.loads(response.content)["filings"]
        assert filings
        for row in filings:
            statement_body = json.dumps(
                {
                    "schema": "fundamental_forensics.financial_statement_request/v1",
                    "entity_id": _ENTITY,
                    "accession": row["accession"],
                },
                separators=(",", ":"),
            ).encode("utf-8")
            served = client.post(_STATEMENTS_PATH, content=statement_body, headers={"content-type": "application/json"})
            assert served.status_code == 200, (row["accession"], served.text[:200])
            adapter = execute_financial_statements(
                body=statement_body, repo_root=ROOT, provider_factory=lambda: aapl_provider
            )
            assert served.content == adapter.body


def test_catalog_request_path_reads_no_member_bytes(router_app, monkeypatch, aapl_provider) -> None:
    """The catalog reads only the index role: no member fetch, no trees, no SEC."""
    import urllib.request

    from engine.fundamental_forensics import production_datasets as PDS

    def _forbidden(*_args, **_kwargs):
        raise AssertionError("the catalog must not read members, trees or the network")

    aapl_provider.catalog(_ENTITY)  # warm the generation cache outside the guard
    monkeypatch.setattr(PDS.ProductionDatasetGeneration, "statement_package", _forbidden)
    monkeypatch.setattr(PDS.ProductionDatasetGeneration, "statement_trees", _forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", _forbidden)
    monkeypatch.setenv("FIF_FINANCIAL_DATASET_MODE", "production")
    monkeypatch.setattr(forensics_api, "_production_statement_provider", lambda: aapl_provider)
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {"id": "paid-user"}
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = client.post(_CATALOG_PATH, content=_body(), headers={"content-type": "application/json"})
    assert response.status_code == 200, response.text[:200]
