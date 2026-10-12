"""HTTP CSV/Parquet export routes reuse the kernel encoders (A38/A40/A54)."""
from __future__ import annotations

import csv
import hashlib
import io
import json
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.forensics as forensics_api
from engine.fundamental_forensics.excel_export import response_query_id, to_xlsx_bytes
from engine.fundamental_forensics.query import MetricMatrix, _csv_safe
from engine.fundamental_forensics.query_exports import (
    CSV_MEDIA_TYPE,
    PARQUET_MEDIA_TYPE,
    QueryExportError,
    export_query_envelope,
    matrix_from_envelope,
)
from engine.fundamental_forensics.query_service import (
    FinancialQueryUnavailableError,
    UnavailableFinancialQueryProvider,
    fip1_fixture_dataset,
)
from engine.fundamental_forensics.query_snapshots import _encode_cells_parquet
from tests.test_fundamental_forensics_query import PERIOD, _engine, _fact, _policy

ROOT = Path(__file__).resolve().parents[1]
_JSON_PATH = "/api/forensics/v1/financial/query"
_CSV_PATH = "/api/forensics/v1/financial/query.csv"
_PARQUET_PATH = "/api/forensics/v1/financial/query.parquet"
_XLSX_PATH = "/api/forensics/v1/financial/query.xlsx"
_EXPORT_PATHS = (_CSV_PATH, _PARQUET_PATH)
_BLOCKED_METHODS = ("GET", "PUT", "DELETE")

T1_SOURCE = "2024-12-31T23:59:59Z"
T2_RECORDED = "2026-08-03T12:00:00Z"

_EXPECTED_PRIVATE_HEADERS = {
    "cache-control": "private, no-store",
    "vary": "Authorization",
    "x-content-type-options": "nosniff",
    "x-robots-tag": "noindex, noarchive",
}

_FLOAT_BODY = (
    b'{"schema":"fundamental_forensics.financial_query_request/v1",'
    b'"entity_id":"mmx.issuer.fip1",'
    b'"policy":{"selection":"latest_known_as_of",'
    b'"source_snapshot_at":"2024-12-31T23:59:59Z",'
    b'"recorded_at":"2026-08-03T12:00:00Z"},'
    b'"metric_ids":["revenue"],'
    b'"periods":[{"kind":"duration","start":1.5,"end":"2023-12-31","label":"FY2023"}]}'
)


def _make_request() -> bytes:
    return json.dumps(
        {
            "schema": "fundamental_forensics.financial_query_request/v1",
            "entity_id": "mmx.issuer.fip1",
            "policy": {
                "selection": "latest_known_as_of",
                "source_snapshot_at": T1_SOURCE,
                "recorded_at": T2_RECORDED,
            },
            "metric_ids": ["revenue"],
            "periods": [
                {
                    "kind": "duration",
                    "start": "2023-01-01",
                    "end": "2023-12-31",
                    "label": "FY2023",
                }
            ],
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _assert_private_headers(response) -> None:
    for name, expected in _EXPECTED_PRIVATE_HEADERS.items():
        assert response.headers.get(name) == expected, f"wrong header {name!r}"


def _fip1_provider(resolve_calls: list | None = None):
    dataset = fip1_fixture_dataset(ROOT)

    class _Provider:
        def resolve(self, entity_id: str):
            if resolve_calls is not None:
                resolve_calls.append(entity_id)
            if entity_id == "mmx.issuer.fip1":
                return dataset
            raise AssertionError(f"unexpected entity {entity_id}")

    return _Provider()


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
def fip1_paid_client(router_app, monkeypatch) -> TestClient:
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {
        "id": "paid-user"
    }
    monkeypatch.setattr(forensics_api, "_financial_query_provider", _fip1_provider)
    with TestClient(router_app, raise_server_exceptions=False) as client:
        yield client


def _post(client: TestClient, path: str, body: bytes | None = None):
    return client.post(
        path,
        content=body if body is not None else _make_request(),
        headers={"content-type": "application/json"},
    )


def _csv_rows(payload: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(payload.decode("utf-8"))))


def _parquet_rows(payload: bytes) -> list[dict[str, str | None]]:
    import pyarrow.parquet as pq

    table = pq.read_table(io.BytesIO(payload))
    columns = table.column_names
    rows: list[dict[str, str | None]] = []
    for index in range(table.num_rows):
        rows.append(
            {
                name: (None if table.column(name)[index].as_py() is None else str(table.column(name)[index].as_py()))
                for name in columns
            }
        )
    return rows


def test_matrix_from_envelope_round_trip(fip1_paid_client) -> None:
    response = _post(fip1_paid_client, _JSON_PATH)
    assert response.status_code == 200
    envelope = response.json()
    matrix = matrix_from_envelope(envelope)
    assert matrix.to_dict() == envelope["receipt"]


def test_http_csv_bytes_match_kernel_export(fip1_paid_client) -> None:
    json_response = _post(fip1_paid_client, _JSON_PATH)
    csv_response = _post(fip1_paid_client, _CSV_PATH)
    assert json_response.status_code == 200
    assert csv_response.status_code == 200
    matrix = MetricMatrix.from_dict(json_response.json()["receipt"])
    assert csv_response.content == matrix.export("csv").payload
    assert csv_response.headers.get("content-type", "").startswith(CSV_MEDIA_TYPE)


def test_http_parquet_bytes_match_snapshot_encoder(fip1_paid_client) -> None:
    json_response = _post(fip1_paid_client, _JSON_PATH)
    parquet_response = _post(fip1_paid_client, _PARQUET_PATH)
    assert json_response.status_code == 200
    assert parquet_response.status_code == 200
    matrix = MetricMatrix.from_dict(json_response.json()["receipt"])
    assert parquet_response.content == _encode_cells_parquet(matrix)[0]
    assert parquet_response.headers.get("content-type", "").startswith(PARQUET_MEDIA_TYPE)


def test_a38_decimal_parity_json_csv_parquet(fip1_paid_client) -> None:
    json_response = _post(fip1_paid_client, _JSON_PATH)
    csv_response = _post(fip1_paid_client, _CSV_PATH)
    parquet_response = _post(fip1_paid_client, _PARQUET_PATH)
    assert json_response.status_code == 200
    assert csv_response.status_code == 200
    assert parquet_response.status_code == 200
    receipt = json_response.json()["receipt"]
    query_hash = receipt["query_hash"]
    nodes = {node["cell_id"]: node for node in receipt["nodes"]}
    csv_by_id = {row["root_cell_id"]: row for row in _csv_rows(csv_response.content)}
    parquet_by_id = {row["root_cell_id"]: row for row in _parquet_rows(parquet_response.content)}
    assert set(receipt["root_cell_ids"]) == set(csv_by_id) == set(parquet_by_id)
    for cell_id in receipt["root_cell_ids"]:
        json_value = nodes[cell_id]["value"]
        csv_value = csv_by_id[cell_id]["value"]
        parquet_value = parquet_by_id[cell_id]["value"]
        if json_value is None:
            assert csv_value == ""
            assert parquet_value is None
        else:
            assert Decimal(json_value) == Decimal(csv_value) == Decimal(parquet_value)
        assert csv_by_id[cell_id]["query_hash"] == query_hash
        assert parquet_by_id[cell_id]["query_hash"] == query_hash


def test_response_sha256_matches_payload(fip1_paid_client) -> None:
    for path in _EXPORT_PATHS:
        response = _post(fip1_paid_client, path)
        assert response.status_code == 200
        assert response.headers.get("x-fif-response-sha256") == hashlib.sha256(
            response.content
        ).hexdigest()


def test_receipt_sha256_matches_json_route_digest(fip1_paid_client) -> None:
    json_response = _post(fip1_paid_client, _JSON_PATH)
    assert json_response.status_code == 200
    json_digest = json_response.headers.get("x-fif-response-sha256")
    for path in _EXPORT_PATHS:
        response = _post(fip1_paid_client, path)
        assert response.status_code == 200
        assert response.headers.get("x-fif-receipt-sha256") == json_digest


def test_private_headers_present_on_exports(fip1_paid_client) -> None:
    for path in _EXPORT_PATHS:
        response = _post(fip1_paid_client, path)
        assert response.status_code == 200
        _assert_private_headers(response)


def test_content_disposition_stem_is_response_query_id(fip1_paid_client) -> None:
    json_response = _post(fip1_paid_client, _JSON_PATH)
    envelope = dict(json_response.json())
    envelope["sha256"] = json_response.headers.get("x-fif-response-sha256")
    stem = response_query_id(envelope)
    for path, fmt in ((_CSV_PATH, "csv"), (_PARQUET_PATH, "parquet")):
        response = _post(fip1_paid_client, path)
        assert response.status_code == 200
        disposition = response.headers.get("content-disposition", "")
        assert disposition == f'attachment; filename="{stem}.{fmt}"'


def test_a54_identical_csv_posts_are_byte_identical(fip1_paid_client) -> None:
    first = _post(fip1_paid_client, _CSV_PATH)
    second = _post(fip1_paid_client, _CSV_PATH)
    assert first.status_code == second.status_code == 200
    assert first.content == second.content
    assert dict(first.headers) == dict(second.headers)


def test_a54_identical_parquet_posts_are_byte_identical(fip1_paid_client) -> None:
    first = _post(fip1_paid_client, _PARQUET_PATH)
    second = _post(fip1_paid_client, _PARQUET_PATH)
    assert first.status_code == second.status_code == 200
    assert first.content == second.content
    assert dict(first.headers) == dict(second.headers)


def test_a54_reissue_without_auth_is_401_and_skips_provider(
    router_app, monkeypatch
) -> None:
    factory_calls: list[int] = []

    def _factory():
        factory_calls.append(1)
        return _fip1_provider()

    monkeypatch.setattr(forensics_api, "_financial_query_provider", _factory)
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {
        "id": "paid-user"
    }
    with TestClient(router_app, raise_server_exceptions=False) as client:
        paid = _post(client, _CSV_PATH)
        assert paid.status_code == 200
        assert factory_calls == [1]
        router_app.dependency_overrides.pop(forensics_api.require_site_full_user, None)
        denied = _post(client, _CSV_PATH)
        assert denied.status_code == 401
        _assert_private_headers(denied)
        assert factory_calls == [1]


@pytest.mark.parametrize("path", _EXPORT_PATHS)
@pytest.mark.parametrize("method", _BLOCKED_METHODS)
def test_unauthenticated_export_methods_return_401(
    anon_client, path: str, method: str
) -> None:
    response = anon_client.request(method, path)
    assert response.status_code == 401
    _assert_private_headers(response)


@pytest.mark.parametrize("path", _EXPORT_PATHS)
@pytest.mark.parametrize("method", _BLOCKED_METHODS)
def test_authenticated_export_methods_return_405(
    fip1_paid_client, path: str, method: str
) -> None:
    response = fip1_paid_client.request(method, path)
    assert response.status_code == 405
    _assert_private_headers(response)
    assert "method not allowed" in response.json().get("detail", "")


@pytest.mark.parametrize("path", _EXPORT_PATHS)
def test_float_admission_matches_json_route(fip1_paid_client, path: str) -> None:
    json_response = _post(fip1_paid_client, _JSON_PATH, _FLOAT_BODY)
    export_response = _post(fip1_paid_client, path, _FLOAT_BODY)
    assert json_response.status_code == export_response.status_code == 400
    assert json_response.json() == export_response.json()
    _assert_private_headers(export_response)


@pytest.mark.parametrize("path", _EXPORT_PATHS)
def test_unavailable_provider_returns_503(router_app, monkeypatch, path: str) -> None:
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {
        "id": "paid-user"
    }

    def _boom():
        raise FinancialQueryUnavailableError()

    monkeypatch.setattr(forensics_api, "_financial_query_provider", _boom)
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = _post(client, path)
    assert response.status_code == 503
    assert response.json().get("detail") == "financial query temporarily unavailable"
    _assert_private_headers(response)


def test_unavailable_provider_resolve_returns_503(router_app, monkeypatch) -> None:
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {
        "id": "paid-user"
    }
    monkeypatch.setattr(
        forensics_api,
        "_financial_query_provider",
        lambda: UnavailableFinancialQueryProvider(),
    )
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = _post(client, _PARQUET_PATH)
    assert response.status_code == 503
    assert response.json().get("detail") == "financial query temporarily unavailable"


def test_a40_csv_payload_is_csv_safe_guarded_encoder(fip1_paid_client) -> None:
    json_response = _post(fip1_paid_client, _JSON_PATH)
    csv_response = _post(fip1_paid_client, _CSV_PATH)
    matrix = MetricMatrix.from_dict(json_response.json()["receipt"])
    assert csv_response.content == matrix.export("csv").payload
    escaped = _engine(
        _fact(entity_id="=2+2", accession="@evil", value="-42"),
        entities={"AAA": "=2+2"},
    ).query_matrix(
        tickers=("AAA",),
        metrics=("revenue",),
        periods=(PERIOD,),
        policy=_policy(),
    )
    row = next(csv.DictReader(io.StringIO(escaped.export("csv").payload.decode("utf-8"))))
    assert row["entity_id"] == _csv_safe("=2+2") == "'=2+2"
    assert row["accession"] == _csv_safe("@evil") == "'@evil"
    assert row["value"] == "-42"
    for probe in ("=1+1", "+lead", "@cmd", "\tled", "\rled"):
        assert _csv_safe(probe) == f"'{probe}"


def test_export_query_envelope_rejects_unknown_format(fip1_paid_client) -> None:
    envelope = _post(fip1_paid_client, _JSON_PATH).json()
    with pytest.raises(QueryExportError):
        export_query_envelope(envelope, "json")


def test_matrix_from_envelope_rejects_missing_receipt() -> None:
    with pytest.raises(QueryExportError):
        matrix_from_envelope({"schema": "no-receipt"})


def test_xlsx_receipt_sha256_matches_json_route_digest(fip1_paid_client) -> None:
    json_response = _post(fip1_paid_client, _JSON_PATH)
    assert json_response.status_code == 200
    json_digest = json_response.headers.get("x-fif-response-sha256")
    xlsx_response = _post(fip1_paid_client, _XLSX_PATH)
    assert xlsx_response.status_code == 200
    assert xlsx_response.headers.get("x-fif-receipt-sha256") == json_digest
    assert xlsx_response.headers.get("x-fif-response-sha256") == hashlib.sha256(
        xlsx_response.content
    ).hexdigest()
    _assert_private_headers(xlsx_response)


def test_xlsx_provider_construction_failure_returns_private_503(
    router_app, monkeypatch
) -> None:
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {
        "id": "paid-user"
    }

    def _boom():
        raise RuntimeError("provider construction failed")

    monkeypatch.setattr(forensics_api, "_financial_query_provider", _boom)
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = _post(client, _XLSX_PATH)
    assert response.status_code == 503
    assert response.json().get("detail") == "financial query temporarily unavailable"
    _assert_private_headers(response)


def test_xlsx_payload_bytes_equal_encoder_output(fip1_paid_client) -> None:
    json_response = _post(fip1_paid_client, _JSON_PATH)
    xlsx_response = _post(fip1_paid_client, _XLSX_PATH)
    assert json_response.status_code == xlsx_response.status_code == 200
    envelope = json_response.json()
    envelope["sha256"] = hashlib.sha256(json_response.content).hexdigest()
    assert xlsx_response.content == to_xlsx_bytes(envelope)
