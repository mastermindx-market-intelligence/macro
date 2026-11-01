"""Stdlib financial-query client over a FastAPI TestClient transport."""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.forensics as forensics_api
from engine.fundamental_forensics.api_client import (
    ExportResponse,
    FinancialQueryClient,
    FinancialQueryClientError,
    FinancialQueryIntegrityError,
    QueryResponse,
    encode_query_request,
)
from engine.fundamental_forensics.query_service import (
    MAX_METRIC_IDS,
    MAX_PERIODS,
    MAX_REQUEST_BYTES,
    fip1_fixture_dataset,
)

ROOT = Path(__file__).resolve().parents[1]
_JSON_PATH = "/api/forensics/v1/financial/query"
_TOKEN = "secret-token-xyz-do-not-leak"

_REQUEST = {
    "schema": "fundamental_forensics.financial_query_request/v1",
    "entity_id": "mmx.issuer.fip1",
    "policy": {
        "selection": "latest_known_as_of",
        "source_snapshot_at": "2024-12-31T23:59:59Z",
        "recorded_at": "2026-08-03T12:00:00Z",
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
}


def _fip1_provider():
    dataset = fip1_fixture_dataset(ROOT)

    class _Provider:
        def resolve(self, entity_id: str):
            if entity_id == "mmx.issuer.fip1":
                return dataset
            raise AssertionError(f"unexpected entity {entity_id}")

    return _Provider()


@pytest.fixture
def router_app(monkeypatch) -> FastAPI:
    monkeypatch.setattr(forensics_api, "REPO", ROOT)
    app = FastAPI()
    app.include_router(forensics_api.router)
    app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {
        "id": "paid-user"
    }
    monkeypatch.setattr(forensics_api, "_financial_query_provider", _fip1_provider)
    return app


@pytest.fixture
def paid_client(router_app) -> TestClient:
    with TestClient(router_app, raise_server_exceptions=False) as client:
        yield client


def _transport(client: TestClient, calls: list | None = None):
    def _call(method, url, headers, body, timeout):
        if calls is not None:
            calls.append(
                {
                    "method": method,
                    "url": url,
                    "headers": dict(headers),
                    "body": body,
                    "timeout": timeout,
                }
            )
        parsed = urlparse(url)
        path = parsed.path
        if parsed.query:
            path = f"{path}?{parsed.query}"
        response = client.request(
            method, path, content=body, headers={str(k): str(v) for k, v in headers.items()}
        )
        return (
            response.status_code,
            {str(k): str(v) for k, v in response.headers.items()},
            bytes(response.content),
        )

    return _call


def _client(paid_client: TestClient, **kwargs) -> FinancialQueryClient:
    calls = kwargs.pop("calls", None)
    return FinancialQueryClient(
        "http://testserver",
        transport=_transport(paid_client, calls),
        **kwargs,
    )


def test_query_round_trip_equals_route_body(paid_client) -> None:
    encoded = encode_query_request(_REQUEST)
    direct = paid_client.post(
        _JSON_PATH, content=encoded, headers={"content-type": "application/json"}
    )
    assert direct.status_code == 200
    response = _client(paid_client).query(_REQUEST)
    assert response.body == direct.content
    assert response.sha256 == hashlib.sha256(direct.content).hexdigest()
    assert response.envelope == direct.json()


def test_cell_values_are_decimals_matching_receipt_strings(paid_client) -> None:
    response = _client(paid_client).query(_REQUEST)
    cells = response.cell_values()
    assert cells
    for cell, value in cells:
        raw = cell.get("value")
        if isinstance(raw, str):
            assert value == Decimal(raw)
            assert not isinstance(value, float)
        else:
            assert value is None
        assert not isinstance(raw, float)
        assert not isinstance(value, float)


@pytest.mark.parametrize("fmt", ("csv", "parquet", "xlsx"))
def test_export_payload_sha_matches_header(paid_client, fmt: str) -> None:
    exported = _client(paid_client).export(_REQUEST, fmt)
    assert isinstance(exported, ExportResponse)
    assert exported.fmt == fmt
    assert exported.sha256 == hashlib.sha256(exported.payload).hexdigest()
    assert exported.payload


def test_tampered_body_raises_integrity_error(paid_client) -> None:
    inner = _transport(paid_client)

    def _tamper(method, url, headers, body, timeout):
        status, response_headers, payload = inner(method, url, headers, body, timeout)
        return status, response_headers, payload + b" "

    client = FinancialQueryClient("http://testserver", transport=_tamper)
    with pytest.raises(FinancialQueryIntegrityError):
        client.query(_REQUEST)


def test_non_2xx_mirrors_status_and_detail(paid_client) -> None:
    bad = dict(_REQUEST)
    bad["metric_ids"] = ["not_a_real_metric_xyz_9999"]
    with pytest.raises(FinancialQueryClientError) as exc_info:
        _client(paid_client).query(bad)
    encoded = encode_query_request(bad)
    direct = paid_client.post(
        _JSON_PATH, content=encoded, headers={"content-type": "application/json"}
    )
    assert exc_info.value.status_code == direct.status_code == 400
    assert exc_info.value.detail == direct.json().get("detail", "")
    assert "unsupported metric" in exc_info.value.detail


def test_float_refused_without_transport(paid_client) -> None:
    calls: list = []
    poisoned = dict(_REQUEST)
    poisoned["n"] = 1.5
    with pytest.raises(FinancialQueryClientError) as exc_info:
        _client(paid_client, calls=calls).query(poisoned)
    assert exc_info.value.status_code == 0
    assert "malformed" in exc_info.value.detail
    assert calls == []


def test_nan_refused_without_transport(paid_client) -> None:
    calls: list = []
    poisoned = dict(_REQUEST)
    poisoned["n"] = float("nan")
    with pytest.raises(FinancialQueryClientError) as exc_info:
        _client(paid_client, calls=calls).export(poisoned, "csv")
    assert exc_info.value.status_code == 0
    assert calls == []


def test_oversize_refused_without_transport(paid_client) -> None:
    calls: list = []
    huge = dict(_REQUEST)
    huge["metric_ids"] = ["revenue"]
    huge["pad"] = "x" * (MAX_REQUEST_BYTES + 1)
    with pytest.raises(FinancialQueryClientError) as exc_info:
        _client(paid_client, calls=calls).query(huge)
    assert exc_info.value.status_code == 0
    assert "exceeds" in exc_info.value.detail
    assert calls == []


def test_too_many_metrics_refused_without_transport(paid_client) -> None:
    calls: list = []
    huge = dict(_REQUEST)
    huge["metric_ids"] = [f"metric_{index}" for index in range(MAX_METRIC_IDS + 1)]
    with pytest.raises(FinancialQueryClientError) as exc_info:
        _client(paid_client, calls=calls).query(huge)
    assert exc_info.value.status_code == 0
    assert calls == []


def test_too_many_periods_refused_without_transport(paid_client) -> None:
    calls: list = []
    huge = dict(_REQUEST)
    huge["periods"] = list(_REQUEST["periods"]) * (MAX_PERIODS + 1)
    with pytest.raises(FinancialQueryClientError) as exc_info:
        _client(paid_client, calls=calls).query(huge)
    assert exc_info.value.status_code == 0
    assert calls == []


def test_canonical_encoding_is_key_order_independent_and_byte_stable() -> None:
    reversed_request = {
        "periods": _REQUEST["periods"],
        "metric_ids": _REQUEST["metric_ids"],
        "policy": {
            "recorded_at": _REQUEST["policy"]["recorded_at"],
            "source_snapshot_at": _REQUEST["policy"]["source_snapshot_at"],
            "selection": _REQUEST["policy"]["selection"],
        },
        "entity_id": _REQUEST["entity_id"],
        "schema": _REQUEST["schema"],
    }
    first = encode_query_request(_REQUEST)
    second = encode_query_request(reversed_request)
    assert first == second
    assert first == encode_query_request(_REQUEST)
    parsed = json.loads(first.decode("utf-8"))
    assert parsed["entity_id"] == "mmx.issuer.fip1"


def test_bearer_header_sent_and_absent_from_repr_and_exceptions(paid_client) -> None:
    calls: list = []
    client = _client(paid_client, bearer_token=_TOKEN, calls=calls)
    assert _TOKEN not in repr(client)
    client.query(_REQUEST)
    assert calls
    header_map = {str(k).lower(): str(v) for k, v in calls[0]["headers"].items()}
    assert header_map.get("authorization") == f"Bearer {_TOKEN}"
    assert _TOKEN not in calls[0]["url"]
    inner = _transport(paid_client)

    def _unauthorized(method, url, headers, body, timeout):
        status, response_headers, payload = inner(method, url, headers, body, timeout)
        return 401, response_headers, b'{"detail":"unauthorized"}'

    failing = FinancialQueryClient(
        "http://testserver",
        bearer_token=_TOKEN,
        transport=_unauthorized,
    )
    with pytest.raises(FinancialQueryClientError) as exc_info:
        failing.query(_REQUEST)
    text = f"{exc_info.value!s}{exc_info.value!r}{failing!r}"
    assert _TOKEN not in text


def test_missing_digest_header_raises_integrity_error(paid_client) -> None:
    inner = _transport(paid_client)

    def _strip(method, url, headers, body, timeout):
        status, response_headers, payload = inner(method, url, headers, body, timeout)
        stripped = {
            key: value
            for key, value in response_headers.items()
            if str(key).lower() != "x-fif-response-sha256"
        }
        return status, stripped, payload

    client = FinancialQueryClient("http://testserver", transport=_strip)
    with pytest.raises(FinancialQueryIntegrityError):
        client.query(_REQUEST)


def test_query_without_bearer_omits_authorization(paid_client) -> None:
    calls: list = []
    _client(paid_client, calls=calls).query(_REQUEST)
    header_map = {str(k).lower() for k in calls[0]["headers"]}
    assert "authorization" not in header_map


def test_sidecar_binds_csv_export(paid_client) -> None:
    client = _client(paid_client)
    exported = client.export(_REQUEST, "csv")
    sidecar = client.sidecar(_REQUEST, exported)
    assert isinstance(sidecar, QueryResponse)
    assert sidecar.sha256 == exported.receipt_sha256


@pytest.mark.parametrize("fmt", ("parquet", "xlsx"))
def test_sidecar_binds_header_only_formats(paid_client, fmt: str) -> None:
    client = _client(paid_client)
    exported = client.export(_REQUEST, fmt)
    sidecar = client.sidecar(_REQUEST, exported)
    assert sidecar.sha256 == exported.receipt_sha256
    assert sidecar.envelope["receipt"]["query_hash"]


def test_export_with_sidecar_returns_pair(paid_client) -> None:
    exported, sidecar = _client(paid_client).export_with_sidecar(_REQUEST, "csv")
    assert isinstance(exported, ExportResponse)
    assert isinstance(sidecar, QueryResponse)
    assert exported.receipt_sha256 == sidecar.sha256


def test_tampered_receipt_header_raises_sidecar_digest_mismatch(paid_client) -> None:
    inner = _transport(paid_client)

    def _retag(method, url, headers, body, timeout):
        status, response_headers, payload = inner(method, url, headers, body, timeout)
        tampered = {
            str(k): ("a" * 64 if str(k).lower() == "x-fif-receipt-sha256" else str(v))
            for k, v in response_headers.items()
        }
        return status, tampered, payload

    client = FinancialQueryClient("http://testserver", transport=_retag)
    exported = client.export(_REQUEST, "csv")
    assert exported.receipt_sha256 == "a" * 64
    with pytest.raises(FinancialQueryIntegrityError) as exc_info:
        client.sidecar(_REQUEST, exported)
    assert exc_info.value.detail == "sidecar receipt digest mismatch"


def test_empty_receipt_digest_refuses_without_second_call(paid_client) -> None:
    calls: list = []
    inner = _transport(paid_client, calls)

    def _strip(method, url, headers, body, timeout):
        status, response_headers, payload = inner(method, url, headers, body, timeout)
        stripped = {
            str(k): str(v)
            for k, v in response_headers.items()
            if str(k).lower() != "x-fif-receipt-sha256"
        }
        return status, stripped, payload

    client = FinancialQueryClient("http://testserver", transport=_strip)
    exported = client.export(_REQUEST, "csv")
    assert exported.receipt_sha256 == ""
    before = len(calls)
    with pytest.raises(FinancialQueryIntegrityError) as exc_info:
        client.sidecar(_REQUEST, exported)
    assert exc_info.value.detail == "export carries no receipt digest"
    assert len(calls) == before


def test_tampered_csv_row_query_hash_raises_sidecar_mismatch(paid_client) -> None:
    inner = _transport(paid_client)

    def _relabel_first_row(method, url, headers, body, timeout):
        status, response_headers, payload = inner(method, url, headers, body, timeout)
        if urlparse(url).path.endswith(".csv"):
            lines = payload.decode("utf-8").split("\n")
            first_row = lines[1]
            lines[1] = "f" * 64 + first_row[first_row.index(",") :]
            payload = "\n".join(lines).encode("utf-8")
            # Recompute the payload digest so ONLY the row-level check can catch this.
            response_headers = {
                str(k): (
                    hashlib.sha256(payload).hexdigest()
                    if str(k).lower() == "x-fif-response-sha256"
                    else str(v)
                )
                for k, v in response_headers.items()
            }
        return status, response_headers, payload

    client = FinancialQueryClient("http://testserver", transport=_relabel_first_row)
    exported = client.export(_REQUEST, "csv")
    assert exported.sha256 == hashlib.sha256(exported.payload).hexdigest()
    with pytest.raises(FinancialQueryIntegrityError) as exc_info:
        client.sidecar(_REQUEST, exported)
    assert exc_info.value.detail == "sidecar query_hash mismatch"


def test_cell_values_malformed_decimal_raises_malformed_response() -> None:
    response = QueryResponse(
        body=b"",
        sha256="0" * 64,
        envelope={"receipt": {"nodes": [{"cell_id": "c1", "value": "not-a-decimal"}]}},
    )
    with pytest.raises(FinancialQueryClientError) as exc_info:
        response.cell_values()
    assert exc_info.value.status_code == 0
    assert exc_info.value.detail == "malformed response"
