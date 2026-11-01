"""FIF-2A API tests: HTTP transport, auth, private headers, determinism, error paths."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.forensics as forensics_api
from engine.fundamental_forensics.financial_intelligence_packet import canonical_json
from engine.fundamental_forensics.query import PeriodRequest, QueryBounds, QueryPolicy, BitemporalMetricQueryEngine
from engine.fundamental_forensics.query_service import (
    CanonicalEntityBinding,
    FinancialQueryAdmissionError,
    FinancialQueryDataset,
    FinancialQueryUnavailableError,
    UnavailableFinancialQueryProvider,
    fip1_fixture_dataset,
)

ROOT = Path(__file__).resolve().parents[1]
_QUERY_PATH = "/api/forensics/v1/financial/query"

T0_SOURCE = "2024-01-01T00:00:00Z"
T1_SOURCE = "2024-12-31T23:59:59Z"
T2_SOURCE = "2025-12-31T23:59:59Z"
T2_RECORDED = "2026-08-03T12:00:00Z"
T3_SOURCE = "2025-12-31T23:59:59Z"
T3_RECORDED = "2026-08-05T12:00:02Z"

_EXPECTED_PRIVATE_HEADERS = {
    "cache-control": "private, no-store",
    "vary": "Authorization",
    "x-content-type-options": "nosniff",
    "x-robots-tag": "noindex, noarchive",
}


def _make_request(
    *,
    schema: str = "fundamental_forensics.financial_query_request/v1",
    entity_id: str = "mmx.issuer.fip1",
    policy: dict | None = None,
    metric_ids: list | None = None,
    periods: list | None = None,
) -> bytes:
    if policy is None:
        policy = {
            "selection": "latest_known_as_of",
            "source_snapshot_at": T1_SOURCE,
            "recorded_at": T2_RECORDED,
        }
    if metric_ids is None:
        metric_ids = ["revenue"]
    if periods is None:
        periods = [{"kind": "duration", "start": "2023-01-01", "end": "2023-12-31", "label": "FY2023"}]
    return json.dumps(
        {"schema": schema, "entity_id": entity_id, "policy": policy, "metric_ids": metric_ids, "periods": periods},
        separators=(",", ":"),
    ).encode("utf-8")


def _assert_private_headers(response) -> None:
    for name, expected in _EXPECTED_PRIVATE_HEADERS.items():
        assert response.headers.get(name) == expected, f"Missing or wrong header {name!r}"


def _fip1_provider(resolve_calls: list | None = None):
    dataset = fip1_fixture_dataset(ROOT)

    class _Provider:
        def resolve(self, entity_id: str) -> FinancialQueryDataset:
            if resolve_calls is not None:
                resolve_calls.append(entity_id)
            if entity_id == "mmx.issuer.fip1":
                return dataset
            raise FinancialQueryAdmissionError(400, "unknown entity")

    return _Provider()


def _asgi_post(app, path: str, *, body: bytes, extra_headers: list[tuple[bytes, bytes]]):
    """POST through the ASGI interface so Content-Length can lie or be absent."""
    import asyncio

    messages: list[dict] = []
    sent = {"done": False}

    async def receive():
        if not sent["done"]:
            sent["done"] = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "root_path": "",
        "query_string": b"",
        "headers": extra_headers,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    asyncio.run(app(scope, receive, send))
    start = next(m for m in messages if m["type"] == "http.response.start")
    body_out = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
    header_map = {k.decode().lower(): v.decode() for k, v in start.get("headers", [])}
    return start["status"], header_map, body_out


# ---------------------------------------------------------------------------
# Fixtures: router-only app vs production app
# ---------------------------------------------------------------------------


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
def paid_client(router_app, monkeypatch) -> TestClient:
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {"id": "paid-user"}
    with TestClient(router_app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def fip1_paid_client(router_app, monkeypatch) -> TestClient:
    """Paid client with FIP1 provider injected."""
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {"id": "paid-user"}
    monkeypatch.setattr(forensics_api, "_financial_query_provider", _fip1_provider)
    with TestClient(router_app, raise_server_exceptions=False) as client:
        yield client


# ---------------------------------------------------------------------------
# Auth / entitlement guards
# ---------------------------------------------------------------------------


def test_anonymous_post_returns_401_with_private_headers(anon_client, monkeypatch) -> None:
    resolve_calls: list = []
    monkeypatch.setattr(
        forensics_api,
        "_financial_query_provider",
        lambda: _fip1_provider(resolve_calls),
    )
    response = anon_client.post(
        _QUERY_PATH,
        content=_make_request(),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 401
    _assert_private_headers(response)
    assert resolve_calls == [], "provider.resolve must not be called before auth"


def test_free_user_returns_403_with_private_headers(router_app, monkeypatch) -> None:
    """Free user (require_user ok, enforce_site_full deny) gets 403; private headers apply."""
    from fastapi import HTTPException
    import app.main as app_main
    import app.paywall as paywall_mod

    resolve_calls: list = []
    monkeypatch.setattr(forensics_api, "_financial_query_provider", lambda: _fip1_provider(resolve_calls))

    # Do NOT override require_site_full_user — monkeypatch the underlying callees.
    monkeypatch.setattr(app_main, "require_user", lambda auth: {"id": "free-user", "tier": "free"})
    monkeypatch.setattr(
        paywall_mod,
        "enforce_site_full",
        lambda user, always=False: (_ for _ in ()).throw(HTTPException(status_code=403, detail="site_full required")),
    )

    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = client.post(
            _QUERY_PATH,
            content=_make_request(),
            headers={"content-type": "application/json"},
        )
    assert response.status_code == 403
    _assert_private_headers(response)
    assert resolve_calls == [], "provider.resolve must not be called before entitlement"


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


def test_paid_fip1_200_with_private_headers_and_sha256(fip1_paid_client) -> None:
    response = fip1_paid_client.post(
        _QUERY_PATH,
        content=_make_request(),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 200
    _assert_private_headers(response)
    sha256_header = response.headers.get("x-fif-response-sha256")
    assert sha256_header is not None
    computed = hashlib.sha256(response.content).hexdigest()
    assert sha256_header == computed


def test_paid_fip1_receipt_equals_direct_matrix(fip1_paid_client) -> None:
    response = fip1_paid_client.post(
        _QUERY_PATH,
        content=_make_request(
            metric_ids=["revenue", "gross_margin"],
            periods=[{"kind": "duration", "start": "2023-01-01", "end": "2023-12-31", "label": "FY2023"}],
            policy={"selection": "latest_known_as_of", "source_snapshot_at": T1_SOURCE, "recorded_at": T2_RECORDED},
        ),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 200
    envelope = response.json()

    dataset = fip1_fixture_dataset(ROOT)
    binding = dataset.binding
    policy = QueryPolicy(source_snapshot_at=T1_SOURCE, recorded_at=T2_RECORDED, selection="latest_known_as_of")
    engine = BitemporalMetricQueryEngine(
        ledger=dataset.ledger,
        registry=dataset.registry,
        entities={binding.ticker: binding.source_entity_id},
        filing_metadata=dataset.filing_metadata,
        bounds=QueryBounds(max_tickers=1, max_metrics=50, max_periods=8, max_cells=400),
    )
    matrix = engine.query_matrix(
        tickers=[binding.ticker],
        metrics=["revenue", "gross_margin"],
        periods=[PeriodRequest.duration("2023-01-01", "2023-12-31", label="FY2023")],
        policy=policy,
    )
    assert envelope["receipt"] == matrix.to_dict()
    assert envelope["receipt"]["query_hash"] == matrix.query_hash


def test_http_mixed_duration_instant_receipt_equals_direct_matrix(fip1_paid_client) -> None:
    periods = [
        {"kind": "duration", "start": "2023-01-01", "end": "2023-12-31", "label": "FY2023"},
        {"kind": "instant", "start": None, "end": "2023-12-31", "label": "2023-12-31"},
    ]
    response = fip1_paid_client.post(
        _QUERY_PATH,
        content=_make_request(
            metric_ids=["revenue", "accounts_receivable_net"],
            periods=periods,
            policy={
                "selection": "latest_known_as_of",
                "source_snapshot_at": T3_SOURCE,
                "recorded_at": T3_RECORDED,
            },
        ),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 200, response.text
    envelope = response.json()
    dataset = fip1_fixture_dataset(ROOT)
    binding = dataset.binding
    policy = QueryPolicy(
        source_snapshot_at=T3_SOURCE,
        recorded_at=T3_RECORDED,
        selection="latest_known_as_of",
    )
    engine = BitemporalMetricQueryEngine(
        ledger=dataset.ledger,
        registry=dataset.registry,
        entities={binding.ticker: binding.source_entity_id},
        filing_metadata=dataset.filing_metadata,
        bounds=QueryBounds(max_tickers=1, max_metrics=50, max_periods=8, max_cells=400),
    )
    matrix = engine.query_matrix(
        tickers=[binding.ticker],
        metrics=["revenue", "accounts_receivable_net"],
        periods=[
            PeriodRequest.duration("2023-01-01", "2023-12-31", label="FY2023"),
            PeriodRequest.instant("2023-12-31", label="2023-12-31"),
        ],
        policy=policy,
    )
    assert envelope["receipt"] == matrix.to_dict()
    assert envelope["receipt"]["query_hash"] == matrix.query_hash
    root_ids = set(envelope["receipt"]["root_cell_ids"])
    roots = [n for n in envelope["receipt"]["nodes"] if n["cell_id"] in root_ids]
    by_key = {(n["metric_id"], n["period"]["kind"]): n for n in roots}
    assert by_key[("revenue", "duration")]["value"] == "1060"
    assert by_key[("accounts_receivable_net", "instant")]["value"] == "121"
    assert by_key[("revenue", "instant")]["state"] == "not_evaluable"
    assert by_key[("accounts_receivable_net", "duration")]["state"] == "not_evaluable"


@pytest.mark.parametrize(
    ("selection", "source", "recorded"),
    [
        ("as_reported", T1_SOURCE, T2_RECORDED),
        ("latest_known_as_of", T3_SOURCE, T3_RECORDED),
        ("latest_restated", T3_SOURCE, T3_RECORDED),
    ],
)
def test_http_receipt_equals_direct_matrix_for_each_policy(
    fip1_paid_client, selection: str, source: str, recorded: str
) -> None:
    body = _make_request(
        metric_ids=["revenue"],
        policy={"selection": selection, "source_snapshot_at": source, "recorded_at": recorded},
    )
    response = fip1_paid_client.post(
        _QUERY_PATH,
        content=body,
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 200
    dataset = fip1_fixture_dataset(ROOT)
    binding = dataset.binding
    matrix = BitemporalMetricQueryEngine(
        ledger=dataset.ledger,
        registry=dataset.registry,
        entities={binding.ticker: binding.source_entity_id},
        filing_metadata=dataset.filing_metadata,
        bounds=QueryBounds(max_tickers=1, max_metrics=50, max_periods=8, max_cells=400),
    ).query_matrix(
        tickers=[binding.ticker],
        metrics=["revenue"],
        periods=[PeriodRequest.duration("2023-01-01", "2023-12-31", label="FY2023")],
        policy=QueryPolicy(source_snapshot_at=source, recorded_at=recorded, selection=selection),
    )
    envelope = response.json()
    assert envelope["receipt"] == matrix.to_dict()
    assert envelope["receipt"]["query_hash"] == matrix.query_hash


def test_paid_fip1_response_content_is_canonical_envelope_bytes(fip1_paid_client) -> None:
    response = fip1_paid_client.post(
        _QUERY_PATH,
        content=_make_request(),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 200
    envelope = response.json()
    canonical = canonical_json(envelope).encode("utf-8")
    assert response.content == canonical


def test_repeated_identical_request_produces_identical_bytes_and_sha(fip1_paid_client, monkeypatch) -> None:
    monkeypatch.setattr(time, "time", lambda: 1_700_000_000.0)
    r1 = fip1_paid_client.post(
        _QUERY_PATH,
        content=_make_request(),
        headers={"content-type": "application/json"},
    )
    monkeypatch.setattr(time, "time", lambda: 1_800_000_000.0)
    r2 = fip1_paid_client.post(
        _QUERY_PATH,
        content=_make_request(),
        headers={"content-type": "application/json"},
    )
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.content == r2.content
    assert r1.headers["x-fif-response-sha256"] == r2.headers["x-fif-response-sha256"]


# ---------------------------------------------------------------------------
# 400 error paths
# ---------------------------------------------------------------------------


def _assert_error(response, status_code: int, detail_fragment: str | None = None) -> None:
    assert response.status_code == status_code
    _assert_private_headers(response)
    body = response.json()
    if detail_fragment:
        assert detail_fragment in body.get("detail", "")
    # Must not contain any internal paths, R2 keys, user ids, or stack traces
    detail_str = str(body)
    for forbidden in ("/Users/", "/opt/", "traceback", "Traceback", "R2", "paid-user"):
        assert forbidden not in detail_str, f"Leaked content in error: {forbidden!r}"


def test_malformed_json_returns_400(paid_client) -> None:
    response = paid_client.post(
        _QUERY_PATH,
        content=b"{broken json",
        headers={"content-type": "application/json"},
    )
    _assert_error(response, 400, "malformed")


def test_duplicate_keys_returns_400(paid_client) -> None:
    response = paid_client.post(
        _QUERY_PATH,
        content=b'{"schema":"fundamental_forensics.financial_query_request/v1","entity_id":"mmx.issuer.fip1","entity_id":"dup","policy":{"selection":"latest_known_as_of","source_snapshot_at":"2024-12-31T23:59:59Z","recorded_at":"2026-08-03T12:00:00Z"},"metric_ids":["revenue"],"periods":[{"kind":"duration","start":"2023-01-01","end":"2023-12-31","label":"FY2023"}]}',
        headers={"content-type": "application/json"},
    )
    _assert_error(response, 400, "duplicate json key")


def test_invalid_policy_returns_400(fip1_paid_client) -> None:
    response = fip1_paid_client.post(
        _QUERY_PATH,
        content=_make_request(policy={
            "selection": "invalid_policy",
            "source_snapshot_at": T1_SOURCE,
            "recorded_at": T2_RECORDED,
        }),
        headers={"content-type": "application/json"},
    )
    _assert_error(response, 400, "invalid policy")


def test_missing_cutoff_returns_400(fip1_paid_client) -> None:
    response = fip1_paid_client.post(
        _QUERY_PATH,
        content=_make_request(policy={
            "selection": "latest_known_as_of",
            "source_snapshot_at": "",
            "recorded_at": T2_RECORDED,
        }),
        headers={"content-type": "application/json"},
    )
    _assert_error(response, 400, "missing cutoff")


def test_unsupported_metric_returns_400(fip1_paid_client) -> None:
    response = fip1_paid_client.post(
        _QUERY_PATH,
        content=_make_request(metric_ids=["not_a_real_metric_xyz_9999"]),
        headers={"content-type": "application/json"},
    )
    _assert_error(response, 400, "unsupported metric")


def test_http_future_metric_cutoff_matches_absent_metric(paid_client, monkeypatch) -> None:
    from dataclasses import replace
    from datetime import datetime, timezone

    from engine.fundamental_forensics import metric_registry as registry_module
    from engine.fundamental_forensics.metric_registry import ConceptAlias, KnownConcept

    historical = {
        "selection": "latest_known_as_of",
        "source_snapshot_at": T3_SOURCE,
        "recorded_at": T3_RECORDED,
    }
    body = _make_request(metric_ids=["future_metric"], policy=historical)

    monkeypatch.setattr(forensics_api, "_financial_query_provider", _fip1_provider)
    r1 = paid_client.post(_QUERY_PATH, content=body, headers={"content-type": "application/json"})
    _assert_error(r1, 400, "unsupported metric")

    base = fip1_fixture_dataset(ROOT)
    future_at = datetime(2026, 8, 6, 0, 0, tzinfo=timezone.utc)
    future_concept = "FutureMetricNotYetGoverned"
    monkeypatch.setitem(
        registry_module.KNOWN_CONCEPT_ALLOWLIST,
        ("us-gaap", future_concept),
        KnownConcept(
            taxonomy="us-gaap",
            concept=future_concept,
            taxonomy_version_start=2009,
            taxonomy_version_end=2026,
            period_kind="duration",
            contract_units=("USD",),
        ),
    )
    revenue = base.registry.metric("revenue")
    mapping = revenue.mappings[0]
    future_contract = replace(
        revenue,
        metric_id="future_metric",
        label="FUTURE LEAK LABEL",
        rule=replace(revenue.rule, rule_id="metric.future_metric/v1", available_at=future_at),
        mappings=(
            replace(
                mapping,
                metric_id="future_metric",
                rule=replace(mapping.rule, rule_id="mapping.future_metric/v1", available_at=future_at),
                taxonomy_concept_aliases=(ConceptAlias("us-gaap", future_concept, 10, 2009, 2026),),
            ),
        ),
        formula=None,
        declared_formula_dependencies=(),
    )
    r2_dataset = FinancialQueryDataset(
        binding=base.binding,
        ledger=base.ledger,
        filing_metadata=base.filing_metadata,
        registry=replace(base.registry, contracts=base.registry.contracts + (future_contract,)),
    )

    class _R2:
        def resolve(self, entity_id: str) -> FinancialQueryDataset:
            return r2_dataset

    monkeypatch.setattr(forensics_api, "_financial_query_provider", lambda: _R2())
    r2 = paid_client.post(_QUERY_PATH, content=body, headers={"content-type": "application/json"})
    assert r2.status_code == r1.status_code
    assert r2.json()["detail"] == r1.json()["detail"]
    _assert_error(r2, 400, "unsupported metric")


def test_duplicate_metric_returns_400(paid_client, monkeypatch) -> None:
    monkeypatch.setattr(forensics_api, "_financial_query_provider", _fip1_provider)
    response = paid_client.post(
        _QUERY_PATH,
        content=_make_request(metric_ids=["revenue", "revenue"]),
        headers={"content-type": "application/json"},
    )
    _assert_error(response, 400, "duplicate metric")


def test_duplicate_period_returns_400(paid_client, monkeypatch) -> None:
    monkeypatch.setattr(forensics_api, "_financial_query_provider", _fip1_provider)
    response = paid_client.post(
        _QUERY_PATH,
        content=_make_request(periods=[
            {"kind": "duration", "start": "2023-01-01", "end": "2023-12-31", "label": "FY2023"},
            {"kind": "duration", "start": "2023-01-01", "end": "2023-12-31", "label": "FY2023-copy"},
        ]),
        headers={"content-type": "application/json"},
    )
    _assert_error(response, 400, "duplicate period")


def test_wrong_content_type_returns_400(paid_client) -> None:
    response = paid_client.post(
        _QUERY_PATH,
        content=_make_request(),
        headers={"content-type": "text/plain"},
    )
    _assert_error(response, 400, "malformed request")


def test_wrong_method_returns_405_with_private_headers(fip1_paid_client) -> None:
    response = fip1_paid_client.get(_QUERY_PATH)
    _assert_error(response, 405, "method not allowed")


def test_misbound_provider_returns_503(paid_client, monkeypatch) -> None:
    fip1 = fip1_fixture_dataset(ROOT)

    class _Misbound:
        def resolve(self, entity_id: str) -> FinancialQueryDataset:
            return fip1

    monkeypatch.setattr(forensics_api, "_financial_query_provider", lambda: _Misbound())
    response = paid_client.post(
        _QUERY_PATH,
        content=_make_request(entity_id="mmx.issuer.someoneelse"),
        headers={"content-type": "application/json"},
    )
    _assert_error(response, 503, "financial query temporarily unavailable")
    response = paid_client.post(
        _QUERY_PATH,
        content=_make_request(),
        headers={"content-type": "text/plain"},
    )
    _assert_error(response, 400, "malformed request")


def test_source_misbound_dataset_returns_503_not_another_issuer_matrix(
    paid_client, monkeypatch
) -> None:
    fip1 = fip1_fixture_dataset(ROOT)
    misbound = FinancialQueryDataset(
        binding=CanonicalEntityBinding(
            entity_id="mmx.issuer.fip1",
            cik="0000111111",
            ticker="FIP1",
            source_entity_id="0000111111",
        ),
        ledger=fip1.ledger,
        filing_metadata=fip1.filing_metadata,
        registry=fip1.registry,
    )

    class _SourceMisbound:
        def resolve(self, entity_id: str) -> FinancialQueryDataset:
            return misbound

    monkeypatch.setattr(forensics_api, "_financial_query_provider", lambda: _SourceMisbound())
    response = paid_client.post(
        _QUERY_PATH,
        content=_make_request(entity_id="mmx.issuer.fip1"),
        headers={"content-type": "application/json"},
    )
    _assert_error(response, 503, "financial query temporarily unavailable")
    assert response.status_code != 200
    assert "0000999999" not in response.text or "receipt" not in response.text


# ---------------------------------------------------------------------------
# 413 paths
# ---------------------------------------------------------------------------


def test_oversized_body_returns_413_provider_not_opened(paid_client, monkeypatch) -> None:
    created: list[str] = []
    resolve_calls: list = []

    def _factory():
        created.append("opened")
        return _fip1_provider(resolve_calls)

    monkeypatch.setattr(forensics_api, "_financial_query_provider", _factory)
    big_body = b"x" * 65537
    response = paid_client.post(
        _QUERY_PATH,
        content=big_body,
        headers={"content-type": "application/json", "content-length": str(len(big_body))},
    )
    _assert_error(response, 413)
    assert created == []
    assert resolve_calls == []


def test_no_content_length_oversize_returns_413_without_opening_provider(
    router_app, monkeypatch
) -> None:
    created: list[str] = []

    def _factory():
        created.append("opened")
        return _fip1_provider()

    monkeypatch.setattr(forensics_api, "_financial_query_provider", _factory)
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {"id": "paid-user"}
    status, _headers, body = _asgi_post(
        router_app,
        _QUERY_PATH,
        body=b"x" * 70000,
        extra_headers=[(b"content-type", b"application/json")],
    )
    assert status == 413
    assert b"request body exceeds bound" in body
    assert created == []


def test_lying_content_length_oversize_returns_413_without_opening_provider(
    router_app, monkeypatch
) -> None:
    created: list[str] = []

    def _factory():
        created.append("opened")
        return _fip1_provider()

    monkeypatch.setattr(forensics_api, "_financial_query_provider", _factory)
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {"id": "paid-user"}
    status, _headers, body = _asgi_post(
        router_app,
        _QUERY_PATH,
        body=b"x" * 70000,
        extra_headers=[
            (b"content-type", b"application/json"),
            (b"content-length", b"12"),
        ],
    )
    assert status == 413
    assert b"request body exceeds bound" in body
    assert created == []


def test_exactly_64kib_body_is_not_413(paid_client, monkeypatch) -> None:
    created: list[str] = []

    def _factory():
        created.append("opened")
        return UnavailableFinancialQueryProvider()

    monkeypatch.setattr(forensics_api, "_financial_query_provider", _factory)
    payload = _make_request()
    pad = 65536 - len(payload)
    body = (b" " * pad) + payload
    assert len(body) == 65536
    response = paid_client.post(
        _QUERY_PATH,
        content=body,
        headers={"content-type": "application/json", "content-length": "65536"},
    )
    assert response.status_code != 413
    assert created == ["opened"]
    _assert_error(response, 503, "financial query temporarily unavailable")


# ---------------------------------------------------------------------------
# 503 paths
# ---------------------------------------------------------------------------


def test_default_golden_provider_unknown_entity_returns_400(paid_client) -> None:
    """Paid user, default golden AAPL provider, non-AAPL issuer → private 400."""
    response = paid_client.post(
        _QUERY_PATH,
        content=_make_request(),
        headers={"content-type": "application/json"},
    )
    _assert_error(response, 400, "unknown entity")
    assert "UnavailableFinancialQueryProvider" not in response.text
    assert "FinancialQueryUnavailableError" not in response.text


def test_provider_generic_exception_returns_503_no_leak(paid_client, monkeypatch) -> None:
    class _BrokenProvider:
        def resolve(self, entity_id: str) -> FinancialQueryDataset:
            raise RuntimeError("secret internal path /data/private/stuff")

    monkeypatch.setattr(forensics_api, "_financial_query_provider", lambda: _BrokenProvider())
    response = paid_client.post(
        _QUERY_PATH,
        content=_make_request(),
        headers={"content-type": "application/json"},
    )
    _assert_error(response, 503, "financial query temporarily unavailable")
    assert "secret internal path" not in response.text


def test_unlawful_delivery_returns_private_503(paid_client, monkeypatch) -> None:
    base = fip1_fixture_dataset(ROOT)
    dataset = FinancialQueryDataset(
        binding=base.binding,
        ledger=base.ledger,
        filing_metadata=base.filing_metadata,
        registry=base.registry,
        delivery={
            "kind": "committed_golden_fixture",
            "attested": True,
            "production_issuer_service": False,
        },
    )

    class _Provider:
        def resolve(self, entity_id: str) -> FinancialQueryDataset:
            return dataset

    monkeypatch.setattr(forensics_api, "_financial_query_provider", lambda: _Provider())
    response = paid_client.post(
        _QUERY_PATH,
        content=_make_request(),
        headers={"content-type": "application/json"},
    )
    _assert_error(response, 503, "financial query temporarily unavailable")
    assert "committed_golden_fixture" not in response.text
    assert "attested" not in response.text


# ---------------------------------------------------------------------------
# Production app integration: unauthenticated POST → 401 not 404
# ---------------------------------------------------------------------------


def test_production_app_unauthenticated_post_returns_401() -> None:
    import app.main as main_mod

    client = TestClient(main_mod.app, raise_server_exceptions=False)
    response = client.post(
        _QUERY_PATH,
        content=_make_request(),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 401
    _assert_private_headers(response)


# ---------------------------------------------------------------------------
# No credential / key / user identity leakage in 200 response
# ---------------------------------------------------------------------------


def test_200_response_contains_no_credentials_or_user_id(fip1_paid_client) -> None:
    response = fip1_paid_client.post(
        _QUERY_PATH,
        content=_make_request(),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 200
    text = response.text
    for forbidden in ("paid-user", "R2", "r2.cloudflarestorage", "/opt/", "/Users/", "Bearer", "AKIA"):
        assert forbidden not in text, f"Leaked {forbidden!r} in 200 response"


# ---------------------------------------------------------------------------
# FIF D3: dataset-mode selection, production refusal semantics, health
# ---------------------------------------------------------------------------

from datetime import datetime, timedelta, timezone  # noqa: E402

from engine.fundamental_forensics import production_datasets as PDS  # noqa: E402
from engine.fundamental_forensics.financial_intelligence_packet import EntityInput  # noqa: E402
from engine.fundamental_forensics.production_provider import (  # noqa: E402
    ProductionFinancialQueryProvider,
)

_D3_ADMITTED = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)


def _d3_production_material() -> PDS.ProductionDatasetMaterial:
    base = fip1_fixture_dataset(ROOT)
    return PDS.ProductionDatasetMaterial(
        binding=base.binding,
        entity=EntityInput(
            entity_id=base.binding.entity_id,
            cik=base.binding.cik,
            ticker=base.binding.ticker,
            name="FIP1 Fixture",
            identity_basis="sec-cik",
            source_entity_id=base.binding.source_entity_id,
        ),
        ledger=base.ledger,
        filing_metadata=base.filing_metadata,
        registry_payload=PDS.snapshot_core_registry_payload(ROOT),
        admitted_at=_D3_ADMITTED,
        source_recorded_at_floor=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )


def _d3_production_query_provider() -> ProductionFinancialQueryProvider:
    store = PDS.InMemoryStrictConditionalStore()
    PDS.publish_production_dataset(store, _d3_production_material())
    return ProductionFinancialQueryProvider(store)


def _d3_request(entity_id: str = "mmx.issuer.fip1", recorded_at: str = "2026-10-05T00:00:00Z") -> bytes:
    return json.dumps(
        {
            "schema": "fundamental_forensics.financial_query_request/v1",
            "entity_id": entity_id,
            "policy": {
                "selection": "latest_known_as_of",
                "source_snapshot_at": "2024-12-31T23:59:59Z",
                "recorded_at": recorded_at,
            },
            "metric_ids": ["revenue"],
            "periods": [
                {"kind": "duration", "start": "2023-01-01", "end": "2023-12-31", "label": "FY2023"}
            ],
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _d3_paid_client(router_app, monkeypatch, *, provider_factory=None) -> TestClient:
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {"id": "paid-user"}
    monkeypatch.setenv("FIF_FINANCIAL_DATASET_MODE", "production")
    if provider_factory is not None:
        monkeypatch.setattr(forensics_api, "_production_query_provider", provider_factory)
    return TestClient(router_app, raise_server_exceptions=False)


def test_production_mode_never_falls_back_to_golden(router_app, monkeypatch) -> None:
    forensics_api._reset_production_provider_cache()
    for env_name in (
        "FIF_PRODUCTION_DATASET_LOCAL_STORE",
        "RESEARCH_LOCAL_STORE",
        "R2_RESEARCH_BUCKET",
    ):
        monkeypatch.delenv(env_name, raising=False)
    monkeypatch.setenv("FIF_FINANCIAL_DATASET_MODE", "production")

    # Prove the golden provider class is never even constructed.
    import engine.fundamental_forensics.ixbrl_raw_ledger as ixbrl_module

    def _no_golden(*_args, **_kwargs):
        raise AssertionError("production mode must never construct the golden provider")

    monkeypatch.setattr(ixbrl_module, "GoldenAaplFinancialQueryProvider", _no_golden)

    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {"id": "paid-user"}
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = client.post(
            _QUERY_PATH, content=_d3_request(), headers={"content-type": "application/json"}
        )
    assert response.status_code == 503
    assert "committed_golden_fixture" not in response.text
    forensics_api._reset_production_provider_cache()


def test_selector_default_and_documented_values(router_app, monkeypatch) -> None:
    from engine.fundamental_forensics.ixbrl_raw_ledger import GoldenAaplFinancialQueryProvider
    from engine.fundamental_forensics.production_datasets import ProductionDatasetModeError
    from engine.fundamental_forensics.production_provider import ProductionFinancialQueryProvider

    # Unset => golden factory, byte-for-byte today's wiring.
    monkeypatch.delenv("FIF_FINANCIAL_DATASET_MODE", raising=False)
    assert isinstance(forensics_api._financial_query_provider(), GoldenAaplFinancialQueryProvider)
    from engine.fundamental_forensics.statement_service import GoldenAaplStatementProvider

    assert isinstance(forensics_api._financial_statement_provider(), GoldenAaplStatementProvider)
    from engine.fundamental_forensics.revision_service import UnavailableFinancialPacketProvider

    assert isinstance(forensics_api._financial_revision_provider(), UnavailableFinancialPacketProvider)
    assert isinstance(forensics_api._financial_packet_provider(), UnavailableFinancialPacketProvider)

    # production => the production providers.
    monkeypatch.setenv("FIF_FINANCIAL_DATASET_MODE", "production")
    monkeypatch.setattr(
        forensics_api, "_production_query_provider", _d3_production_query_provider
    )
    assert isinstance(forensics_api._financial_query_provider(), ProductionFinancialQueryProvider)

    # Any other value is a typed refusal, never a silent golden selection.
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {"id": "paid-user"}
    for bad in ("staging", "GOLDEN", "production ", "0"):
        monkeypatch.setenv("FIF_FINANCIAL_DATASET_MODE", bad)
        with pytest.raises(ProductionDatasetModeError):
            forensics_api._financial_dataset_mode()
        with TestClient(router_app, raise_server_exceptions=False) as client:
            response = client.post(
                _QUERY_PATH, content=_d3_request(), headers={"content-type": "application/json"}
            )
        assert response.status_code == 503
        assert "committed_golden_fixture" not in response.text

    # The mode key is documented (an undocumented switch is an undocumented
    # fallback): the operator docs page names it.
    monkeypatch.delenv("FIF_FINANCIAL_DATASET_MODE", raising=False)
    docs = (
        ROOT / "research" / "financial_intelligence_fabric" / "FIF_3A3_REUSE_MAP.md"
    ).read_text(encoding="utf-8")
    assert "FIF_FINANCIAL_DATASET_MODE" in docs
    assert "production_issuer_dataset" in docs


def test_missing_or_damaged_manifest_is_unavailable_503(router_app, monkeypatch) -> None:
    def _tampered(mutate):
        base = fip1_fixture_dataset(ROOT)
        material = PDS.ProductionDatasetMaterial(
            binding=base.binding,
            entity=EntityInput(
                entity_id=base.binding.entity_id,
                cik=base.binding.cik,
                ticker=base.binding.ticker,
                name="FIP1 Fixture",
                identity_basis="sec-cik",
                source_entity_id=base.binding.source_entity_id,
            ),
            ledger=base.ledger,
            filing_metadata=base.filing_metadata,
            registry_payload=PDS.snapshot_core_registry_payload(ROOT),
            admitted_at=_D3_ADMITTED,
            source_recorded_at_floor=datetime(2026, 8, 1, tzinfo=timezone.utc),
        )
        store = PDS.InMemoryStrictConditionalStore()
        publication = PDS.publish_production_dataset(store, material)
        mutate(store, publication)
        return ProductionFinancialQueryProvider(store)

    def _truncate_manifest(store, publication):
        key = PDS.production_manifest_key("mmx.issuer.fip1", publication.generation_id)
        store.raw_put(key, store.get_bytes(key)[:7])

    def _digest_mismatch(store, publication):
        generation = PDS.load_generation(
            store, "mmx.issuer.fip1", publication.generation_id
        )
        row = next(r for r in generation.manifest["objects"] if r["role"] == "ledger_json")
        payload = bytearray(store.get_bytes(row["object_key"]))
        payload[0] = payload[0] ^ 0x01
        store.raw_put(row["object_key"], bytes(payload))

    def _missing_role_object(store, publication):
        generation = PDS.load_generation(
            store, "mmx.issuer.fip1", publication.generation_id
        )
        row = next(r for r in generation.manifest["objects"] if r["role"] == "registry_json")
        store.drop(row["object_key"])

    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {"id": "paid-user"}
    details = set()
    for mutate in (_truncate_manifest, _digest_mismatch, _missing_role_object):
        monkeypatch.setenv("FIF_FINANCIAL_DATASET_MODE", "production")
        monkeypatch.setattr(forensics_api, "_production_query_provider", lambda m=mutate: _tampered(m))
        with TestClient(router_app, raise_server_exceptions=False) as client:
            response = client.post(
                _QUERY_PATH, content=_d3_request(), headers={"content-type": "application/json"}
            )
        assert response.status_code == 503, mutate.__name__
        details.add((response.status_code, response.json()["detail"]))
    # Identical detail for every damage class: no corpus-state oracle.
    assert details == {(503, "financial query temporarily unavailable")}


def test_request_path_performs_no_network_or_extraction(router_app, monkeypatch) -> None:
    import socket

    provider = _d3_production_query_provider()
    monkeypatch.setenv("FIF_FINANCIAL_DATASET_MODE", "production")
    monkeypatch.setattr(forensics_api, "_production_query_provider", lambda: provider)
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {"id": "paid-user"}

    def _forbidden(*_args, **_kwargs):
        raise AssertionError("the production request path must not extract or fetch")

    import collectors.sec_filing_parser as parser_module
    import engine.fundamental_forensics.ixbrl_extraction as extraction_module
    import engine.fundamental_forensics.ixbrl_raw_ledger as ixbrl_module
    import engine.fundamental_forensics.statement_graph as statement_graph_module
    import urllib.request

    monkeypatch.setattr(parser_module, "parse_sec_filing_document", _forbidden)
    monkeypatch.setattr(ixbrl_module, "parse_sec_filing_document", _forbidden)
    monkeypatch.setattr(ixbrl_module, "parse_and_convert_golden_packages", _forbidden)
    monkeypatch.setattr(ixbrl_module, "convert_parsed_filings", _forbidden)
    monkeypatch.setattr(statement_graph_module, "parse_sec_filing_document", _forbidden)
    monkeypatch.setattr(extraction_module, "IxbrlExtraction", _forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", _forbidden)

    # Poison CONNECTS, not construction: asyncio's own event-loop self-pipe
    # legitimately creates an AF_UNIX socketpair inside the raw-ASGI harness,
    # while any real outbound connection from the request path dies loudly.
    class _NoConnectSocket(socket.socket):
        def connect(self, *_args, **_kwargs):
            raise AssertionError("the production request path must not connect a socket")

        def connect_ex(self, *_args, **_kwargs):
            raise AssertionError("the production request path must not connect a socket")

    monkeypatch.setattr(socket, "socket", _NoConnectSocket)

    def _no_create_connection(*_args, **_kwargs):
        raise AssertionError("the production request path must not create a connection")

    monkeypatch.setattr(socket, "create_connection", _no_create_connection)

    body = _d3_request()
    headers = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]
    status, header_map, body_out = _asgi_post(router_app, _QUERY_PATH, body=body, extra_headers=headers)
    assert status == 200, body_out[:400]
    envelope = json.loads(body_out)
    assert envelope["delivery"]["kind"] == "production_issuer_dataset"
    assert envelope["coverage"]["value_cells"] >= 0


def test_provider_not_constructed_before_auth_or_admission(router_app, monkeypatch) -> None:
    constructions = {"query": 0, "revision": 0, "packet": 0, "statement": 0}

    def _count(name, factory):
        def _wrapped():
            constructions[name] += 1
            return factory()

        return _wrapped

    monkeypatch.setattr(
        forensics_api,
        "_financial_query_provider",
        _count("query", _fip1_provider),
    )
    monkeypatch.setattr(
        forensics_api,
        "_financial_revision_provider",
        _count("revision", lambda: UnavailableFinancialQueryProvider()),
    )
    monkeypatch.setattr(
        forensics_api,
        "_financial_packet_provider",
        _count("packet", lambda: UnavailableFinancialQueryProvider()),
    )
    from engine.fundamental_forensics.statement_service import UnavailableFinancialStatementProvider

    monkeypatch.setattr(
        forensics_api,
        "_financial_statement_provider",
        _count("statement", UnavailableFinancialStatementProvider),
    )

    # Anonymous: 401 with the private policy, nothing constructed.
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = client.post(
            _QUERY_PATH, content=_make_request(), headers={"content-type": "application/json"}
        )
    assert response.status_code == 401
    _assert_private_headers(response)
    assert constructions == {"query": 0, "revision": 0, "packet": 0, "statement": 0}

    # Free user: 403 after authentication, still nothing constructed.
    from fastapi import HTTPException

    import app.main as app_main
    import app.paywall as paywall_mod

    monkeypatch.setattr(app_main, "require_user", lambda auth: {"id": "free-user", "tier": "free"})
    monkeypatch.setattr(
        paywall_mod,
        "enforce_site_full",
        lambda user, always=False: (_ for _ in ()).throw(
            HTTPException(status_code=403, detail="site_full required")
        ),
    )
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = client.post(
            _QUERY_PATH, content=_make_request(), headers={"content-type": "application/json"}
        )
    assert response.status_code == 403
    _assert_private_headers(response)
    assert constructions == {"query": 0, "revision": 0, "packet": 0, "statement": 0}


def test_health_reports_mode_and_generation_names_only(router_app, monkeypatch) -> None:
    from engine.fundamental_forensics.health import assert_no_private_leak

    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {"id": "paid-user"}
    monkeypatch.setattr(
        forensics_api,
        "evaluate_health",
        lambda _root, **_kwargs: {
            "schema": "fundamental_forensics.health/v1",
            "status": "current",
            "reason_code": "SOURCE_CURRENT",
            "age_seconds": 1,
            "freshness_budget_seconds": 3600,
            "evaluated_at": "2026-10-11T00:00:00Z",
            "clocks": {"broad_source_at": "2026-10-11T00:00:00Z"},
            "private_object": {"origin": "r2"},
        },
    )
    monkeypatch.delenv("FIF_FINANCIAL_DATASET_MODE", raising=False)
    with TestClient(router_app, raise_server_exceptions=False) as client:
        golden = client.get("/api/forensics/health")
    assert golden.status_code == 200
    assert golden.headers["x-fif-financial-dataset-mode"] == "golden"
    assert "x-fif-dataset-generation-id" not in golden.headers
    assert_no_private_leak(golden.json())

    generation_id = "ffprods_" + "b" * 64
    monkeypatch.setenv("FIF_FINANCIAL_DATASET_MODE", "production")

    import engine.fundamental_forensics.production_datasets as pds_module

    monkeypatch.setattr(
        pds_module,
        "build_production_dataset_store",
        lambda *_, **__: object(),
    )
    monkeypatch.setattr(
        pds_module,
        "latest_generation_summary",
        lambda _store, _issuer: {
            "dataset_generation_id": generation_id,
            "admitted_at": "2026-10-01T00:00:00.000000Z",
        },
    )
    with TestClient(router_app, raise_server_exceptions=False) as client:
        production = client.get("/api/forensics/health")
    assert production.status_code == 200
    assert production.headers["x-fif-financial-dataset-mode"] == "production"
    assert production.headers["x-fif-dataset-generation-id"] == generation_id
    assert production.headers["x-fif-dataset-admitted-at"] == "2026-10-01T00:00:00.000000Z"
    # Names/ids only: the payload itself is unchanged and leak-free.
    assert production.json() == golden.json()
    assert_no_private_leak(production.json())
    rendered = production.text + "".join(
        production.headers.get(k, "") for k in production.headers.keys()
    )
    for token in ("object_key", "STATE_KEY", "R2_ACCESS", "SECRET", "credential"):
        assert token not in rendered

    # An invalid mode refuses health too — never a silent report, and never
    # an unhandled 500: the same private 503 the financial POSTs use (A15).
    monkeypatch.setenv("FIF_FINANCIAL_DATASET_MODE", "nonsense")
    with TestClient(router_app, raise_server_exceptions=False) as client:
        refused = client.get("/api/forensics/health")
    assert refused.status_code == 503
    _assert_private_headers(refused)


# ---------------------------------------------------------------------------
# FIF P1: OPTIONS/TRACE method bypass, health 503, adapter-byte equality
# (A38), and per-user policy isolation (A23).
# ---------------------------------------------------------------------------

_FINANCIAL_PATHS = (
    _QUERY_PATH,
    "/api/forensics/v1/financial/revisions",
    "/api/forensics/v1/financial/packet",
    "/api/forensics/v1/financial/statements",
)


@pytest.mark.parametrize("method", ["OPTIONS", "TRACE"])
@pytest.mark.parametrize("path", _FINANCIAL_PATHS)
def test_options_and_trace_go_through_the_private_wrapper(
    router_app, monkeypatch, method: str, path: str
) -> None:
    """F7: auth dependency first, then the private 405; nothing constructed."""

    def _forbidden_factory(name: str):
        def _factory():
            raise AssertionError(f"{name} provider factory constructed for a method bypass")

        return _factory

    monkeypatch.setattr(forensics_api, "_financial_query_provider", _forbidden_factory("query"))
    monkeypatch.setattr(forensics_api, "_financial_revision_provider", _forbidden_factory("revision"))
    monkeypatch.setattr(forensics_api, "_financial_packet_provider", _forbidden_factory("packet"))
    monkeypatch.setattr(forensics_api, "_financial_statement_provider", _forbidden_factory("statement"))

    # Anonymous: 401 with the private policy, nothing constructed.
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = client.request(method, path)
    assert response.status_code == 401
    _assert_private_headers(response)

    # Entitled: 405 with the private policy, nothing constructed.
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {"id": "paid-user"}
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = client.request(method, path)
    assert response.status_code == 405
    _assert_private_headers(response)


def test_invalid_dataset_mode_refuses_health_with_private_503(router_app, monkeypatch) -> None:
    monkeypatch.setattr(
        forensics_api,
        "evaluate_health",
        lambda _root, **_kwargs: {"schema": "fundamental_forensics.health/v1"},
    )
    monkeypatch.setenv("FIF_FINANCIAL_DATASET_MODE", "staging")
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {"id": "paid-user"}
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = client.get("/api/forensics/health")
    assert response.status_code == 503
    _assert_private_headers(response)
    assert response.json()["detail"] == "forensics health temporarily unavailable"
    assert "x-fif-financial-dataset-mode" not in response.headers


def _p1_aapl_material():
    from engine.fundamental_forensics import production_datasets as PDS
    from engine.fundamental_forensics.financial_intelligence_packet import EntityInput
    from engine.fundamental_forensics.ixbrl_raw_ledger import (
        GOLDEN_AAPL_QUERY_ACCESSIONS,
        parse_and_convert_golden_packages,
    )
    from engine.fundamental_forensics.query_service import CanonicalEntityBinding
    from engine.fundamental_forensics.statement_graph import load_golden_aapl_package

    packages = [
        load_golden_aapl_package(ROOT, accession=accession)
        for accession in GOLDEN_AAPL_QUERY_ACCESSIONS
    ]
    ledger, filing_metadata, _report = parse_and_convert_golden_packages(packages)
    return PDS.ProductionDatasetMaterial(
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
        admitted_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        packages=tuple(packages),
        security_id="SEC:US-XNAS-AAPL",
        listing_key="US-XNAS-AAPL",
    )


def _p1_aapl_body(path: str, *, recorded_at: str = "2026-10-05T00:00:00Z") -> bytes:
    if path.endswith("/statements"):
        payload = {
            "schema": "fundamental_forensics.financial_statement_request/v1",
            "entity_id": "ISS:US-XNAS-AAPL",
            "accession": "0000320193-25-000079",
        }
    else:
        payload = {
            "schema": (
                "fundamental_forensics.financial_revision_request/v1"
                if path.endswith("/revisions")
                else "fundamental_forensics.financial_query_request/v1"
            ),
            "entity_id": "ISS:US-XNAS-AAPL",
            "policy": {
                "selection": "latest_known_as_of",
                "source_snapshot_at": "2025-12-31T23:59:59Z",
                "recorded_at": recorded_at,
            },
            "metric_ids": ["revenue"],
            "periods": [
                {"kind": "duration", "start": "2023-01-01", "end": "2023-12-31", "label": "FY2023"}
            ],
        }
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def _p1_fip1_body(path: str, *, recorded_at: str = "2026-10-05T00:00:00Z") -> bytes:
    """Packet-servable FIP1 request bodies (occurrence-keyed corpus)."""
    payload = {
        "schema": (
            "fundamental_forensics.financial_revision_request/v1"
            if path.endswith("/revisions")
            else "fundamental_forensics.financial_query_request/v1"
        ),
        "entity_id": "mmx.issuer.fip1",
        "policy": {
            "selection": "latest_known_as_of",
            "source_snapshot_at": "2025-12-31T23:59:59Z",
            "recorded_at": recorded_at,
        },
        "metric_ids": ["revenue"],
        "periods": [
            {"kind": "duration", "start": "2023-01-01", "end": "2023-12-31", "label": "FY2023"}
        ],
    }
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def test_production_adapter_bytes_equal_http_bytes(router_app, monkeypatch) -> None:
    """A38: kernel adapter bytes are the HTTP response bytes, sha-for-sha."""
    from engine.fundamental_forensics import production_datasets as PDS
    from engine.fundamental_forensics.production_provider import (
        ProductionFinancialPacketProvider,
        ProductionFinancialQueryProvider,
        ProductionFinancialStatementProvider,
    )
    from engine.fundamental_forensics.query_service import execute_financial_query
    from engine.fundamental_forensics.revision_service import execute_financial_revisions
    from engine.fundamental_forensics.statement_service import execute_financial_statements

    # The FIP1 corpus is occurrence-keyed, so query AND revisions are servable
    # from it; statements need the package-carrying AAPL corpus.
    fip1_store = PDS.InMemoryStrictConditionalStore()
    PDS.publish_production_dataset(fip1_store, _d3_production_material())
    aapl_store = PDS.InMemoryStrictConditionalStore()
    PDS.publish_production_dataset(aapl_store, _p1_aapl_material())

    query_provider = ProductionFinancialQueryProvider(fip1_store)
    packet_provider = ProductionFinancialPacketProvider(fip1_store, repo_root=ROOT)
    statement_provider = ProductionFinancialStatementProvider(aapl_store)

    monkeypatch.setenv("FIF_FINANCIAL_DATASET_MODE", "production")
    monkeypatch.setattr(forensics_api, "_production_query_provider", lambda: query_provider)
    monkeypatch.setattr(forensics_api, "_production_packet_provider", lambda: packet_provider)
    monkeypatch.setattr(forensics_api, "_production_statement_provider", lambda: statement_provider)
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {"id": "paid-user"}

    cases = {
        _QUERY_PATH: (
            _p1_fip1_body(_QUERY_PATH),
            lambda body: execute_financial_query(body=body, provider=query_provider),
        ),
        "/api/forensics/v1/financial/revisions": (
            _p1_fip1_body("/api/forensics/v1/financial/revisions"),
            lambda body: execute_financial_revisions(
                body=body, provider_factory=lambda: packet_provider
            ),
        ),
        "/api/forensics/v1/financial/statements": (
            _p1_aapl_body("/api/forensics/v1/financial/statements"),
            lambda body: execute_financial_statements(
                body=body, repo_root=ROOT, provider_factory=lambda: statement_provider
            ),
        ),
    }
    with TestClient(router_app, raise_server_exceptions=False) as client:
        for path, (body, adapter) in cases.items():
            result = adapter(body)
            response = client.post(path, content=body, headers={"content-type": "application/json"})
            assert response.status_code == 200, (path, response.text[:200])
            _assert_private_headers(response)
            assert result.body == response.content, path
            assert response.headers["x-fif-response-sha256"] == result.sha256, path
            assert (
                response.headers["x-fif-response-sha256"]
                == hashlib.sha256(response.content).hexdigest()
            ), path
            assert json.loads(response.content)["delivery"]["kind"] == "production_issuer_dataset"


def test_two_users_two_policies_share_no_answer_object(router_app, monkeypatch) -> None:
    """A23: one production provider, two entitled users, two recorded_at
    policies — policy-different bodies, both private/no-store, and a repeat
    by the first user is byte-identical (no cross-user answer object)."""
    from engine.fundamental_forensics import production_datasets as PDS
    from engine.fundamental_forensics.production_provider import (
        ProductionFinancialQueryProvider,
    )

    store = PDS.InMemoryStrictConditionalStore()
    PDS.publish_production_dataset(store, _p1_aapl_material())
    # The ONE production provider singleton, shared by every request.
    provider = ProductionFinancialQueryProvider(store)
    monkeypatch.setenv("FIF_FINANCIAL_DATASET_MODE", "production")
    monkeypatch.setattr(forensics_api, "_production_query_provider", lambda: provider)

    bodies: dict[str, bytes] = {}
    with TestClient(router_app, raise_server_exceptions=False) as client:
        for user, recorded_at in (
            ("paid-user-a", "2026-10-05T00:00:00Z"),
            ("paid-user-b", "2026-10-06T00:00:00Z"),
        ):
            router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda u=user: {
                "id": u
            }
            response = client.post(
                _QUERY_PATH,
                content=_p1_aapl_body(_QUERY_PATH, recorded_at=recorded_at),
                headers={"content-type": "application/json"},
            )
            assert response.status_code == 200
            assert response.headers["cache-control"] == "private, no-store"
            bodies[user] = response.content
        # The first user repeats its exact policy: byte-identical answer.
        router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {
            "id": "paid-user-a"
        }
        repeat = client.post(
            _QUERY_PATH,
            content=_p1_aapl_body(_QUERY_PATH, recorded_at="2026-10-05T00:00:00Z"),
            headers={"content-type": "application/json"},
        )
    assert bodies["paid-user-a"] != bodies["paid-user-b"]
    assert repeat.status_code == 200
    assert repeat.content == bodies["paid-user-a"]


# ---------------------------------------------------------------------------
# A22 (Z1 test-gap closure): denied and failed paths log nothing private.
#
# The row requires "no secret/source body in error or logging." The existing
# tests pin the response side (status, private headers, no leak in the body);
# this test pins the LOGGING side: over every denied/failed path, at DEBUG
# level, neither the API's own logger (app/forensics.py:85) nor the root
# logger may carry a forbidden fragment, the request body, or a provider
# class name.
# ---------------------------------------------------------------------------

_FORBIDDEN_LOG_FRAGMENTS = (
    "/Users/",
    "/opt/",
    "traceback",
    "Traceback",
    "R2",
    "paid-user",
    "secret internal path",
    "/data/private",
)


def _record_text(record) -> str:
    """Every textual surface one record can leak through."""
    import traceback as traceback_mod

    parts = [str(record.msg), record.getMessage()]
    if record.args:
        parts.append(" ".join(repr(arg) for arg in record.args))
    if record.exc_info:
        parts.append(record.exc_text or "".join(traceback_mod.format_exception(*record.exc_info)))
    return "\n".join(parts)


def _assert_nothing_private_logged(caplog, *, body: bytes, provider_class: str) -> None:
    records = [
        record
        for record in caplog.records
        if record.name == "fundamental_forensics.api" or record.name == "root"
    ]
    forbidden = list(_FORBIDDEN_LOG_FRAGMENTS) + [body.decode("utf-8"), provider_class]
    for record in records:
        text = _record_text(record)
        for fragment in forbidden:
            assert fragment not in text, (
                f"logger {record.name!r} at {record.levelname} leaked {fragment!r}:\n{text[:400]}"
            )


def test_denied_and_failed_paths_log_nothing_private(router_app, monkeypatch, caplog) -> None:
    import logging

    caplog.set_level(logging.DEBUG)

    # Path 1: anonymous 401 (the :164 shape) — deny before the provider opens.
    resolve_calls: list = []
    monkeypatch.setattr(
        forensics_api,
        "_financial_query_provider",
        lambda: _fip1_provider(resolve_calls),
    )
    body = _make_request()
    with TestClient(router_app, raise_server_exceptions=False) as client:
        caplog.clear()
        response = client.post(
            _QUERY_PATH, content=body, headers={"content-type": "application/json"}
        )
    assert response.status_code == 401
    assert resolve_calls == []
    _assert_nothing_private_logged(caplog, body=body, provider_class="_Provider")

    # Path 2: free user 403 (the :181 shape) — deny before entitlement clears.
    from fastapi import HTTPException
    import app.main as app_main
    import app.paywall as paywall_mod

    monkeypatch.setattr(app_main, "require_user", lambda auth: {"id": "free-user", "tier": "free"})
    monkeypatch.setattr(
        paywall_mod,
        "enforce_site_full",
        lambda user, always=False: (_ for _ in ()).throw(
            HTTPException(status_code=403, detail="site_full required")
        ),
    )
    with TestClient(router_app, raise_server_exceptions=False) as client:
        caplog.clear()
        response = client.post(
            _QUERY_PATH, content=body, headers={"content-type": "application/json"}
        )
    assert response.status_code == 403
    assert resolve_calls == []
    _assert_nothing_private_logged(caplog, body=body, provider_class="_Provider")

    # Path 3: misbound provider 503 (the :562 shape).
    fip1 = fip1_fixture_dataset(ROOT)

    class _Misbound:
        def resolve(self, entity_id: str) -> FinancialQueryDataset:
            return fip1

    monkeypatch.setattr(forensics_api, "_financial_query_provider", lambda: _Misbound())
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {
        "id": "paid-user"
    }
    misbound_body = _make_request(entity_id="mmx.issuer.someoneelse")
    with TestClient(router_app, raise_server_exceptions=False) as client:
        caplog.clear()
        response = client.post(
            _QUERY_PATH, content=misbound_body, headers={"content-type": "application/json"}
        )
    assert response.status_code == 503
    _assert_nothing_private_logged(caplog, body=misbound_body, provider_class="_Misbound")

    # Path 4: generic provider exception 503 (the :726 shape) — the provider
    # raises a RuntimeError whose message IS a secret; neither the message nor
    # its traceback may reach a log record.
    class _BrokenProvider:
        def resolve(self, entity_id: str) -> FinancialQueryDataset:
            raise RuntimeError("secret internal path /data/private/stuff")

    monkeypatch.setattr(forensics_api, "_financial_query_provider", lambda: _BrokenProvider())
    with TestClient(router_app, raise_server_exceptions=False) as client:
        caplog.clear()
        response = client.post(
            _QUERY_PATH, content=body, headers={"content-type": "application/json"}
        )
    assert response.status_code == 503
    _assert_nothing_private_logged(caplog, body=body, provider_class="_BrokenProvider")

    # Path 5: unlawful delivery 503 (the :741 shape) — a dataset whose delivery
    # block names its source provenance must not surface it in a log either.
    base = fip1_fixture_dataset(ROOT)
    unlawful = FinancialQueryDataset(
        binding=base.binding,
        ledger=base.ledger,
        filing_metadata=base.filing_metadata,
        registry=base.registry,
        delivery={
            "kind": "committed_golden_fixture",
            "attested": True,
            "production_issuer_service": False,
        },
    )

    class _Unlawful:
        def resolve(self, entity_id: str) -> FinancialQueryDataset:
            return unlawful

    monkeypatch.setattr(forensics_api, "_financial_query_provider", lambda: _Unlawful())
    with TestClient(router_app, raise_server_exceptions=False) as client:
        caplog.clear()
        response = client.post(
            _QUERY_PATH, content=body, headers={"content-type": "application/json"}
        )
    assert response.status_code == 503
    _assert_nothing_private_logged(caplog, body=body, provider_class="_Unlawful")
