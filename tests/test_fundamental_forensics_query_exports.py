"""HTTP CSV/Parquet export routes reuse the kernel encoders (A38/A40/A54)."""
from __future__ import annotations

import csv
import functools
import hashlib
import io
import json
import zipfile
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.forensics as forensics_api
from engine.fundamental_forensics.excel_export import response_query_id, to_xlsx_bytes
from engine.fundamental_forensics.metric_registry import load_metric_registry
from engine.fundamental_forensics import query as query_module
from engine.fundamental_forensics import query_snapshots as query_snapshots_module
from engine.fundamental_forensics.not_presented import load_not_presented_pack
from engine.fundamental_forensics.query import (
    QUALIFIED_NOT_PRESENTED_EXPORT_PREFIX,
    BitemporalMetricQueryEngine,
    MetricMatrix,
    QueryEntity,
    _csv_safe,
)
from engine.fundamental_forensics.query_exports import (
    CSV_MEDIA_TYPE,
    PARQUET_MEDIA_TYPE,
    SERIALIZATION_DIFFERENCES,
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
from engine.fundamental_forensics.raw_ledger import (
    FactUnit,
    RawFactLedger,
    canonical_json,
)
from tests.test_fundamental_forensics_formula_not_presented import (
    AFTER as _NP_AFTER,
    BEFORE as _NP_BEFORE,
    DEBT_FACTS,
    INSTANT as _NP_INSTANT,
    NO_DEBT_ARCS,
    NO_DEBT_FACTS,
    _debt_engine,
    _facts as _np_facts,
)
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


# ---------------------------------------------------------------------------
# X1-p (A38/A40): per-cell export parity and the explicit
# SERIALIZATION_DIFFERENCES declaration.
#
# The fixture matrices below are hermetic: they are built with the same
# helpers the rest of this file already imports from
# tests/test_fundamental_forensics_query.py (``_engine``, ``_fact``,
# ``_policy``, ``PERIOD``) over the committed core registry, plus the
# committed qualification registry fixture for the not_applicable cell.
#
# Cell-state coverage: reported direct cells, a derived formula cell with
# dependency_cell_ids, missing cells with reasons, a not_evaluable cell
# (filing form outside the governed contract), an unexpected-unit
# not_evaluable cell (the one reachable state where cell.unit and
# provenance.unit diverge), a not_applicable cell with issuer_class
# provenance, a negative value, and a >15-significant-digit value that does
# not round-trip IEEE-754.
#
# Formula-lead probes: entity_id / accession / document_id are the free-text
# fields through which a leading ``=``, ``+``, ``-`` or ``@`` survives the
# kernel's bounded-text validators end to end.  A leading TAB or CR is
# stripped by ``_require_text``/``_bounded_text`` before export on every
# text field, and ticker is ``[A-Z0-9.-]`` by regex, so those prefixes are
# pinned at the ``_csv_safe`` unit level (see
# test_a40_csv_payload_is_csv_safe_guarded_encoder above) rather than
# end-to-end; test_a40_x1p_no_unguarded_formula_leads below scans every
# text cell of every fixture export regardless.
# ---------------------------------------------------------------------------

_SSML_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_DANGEROUS_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

_X1P_REVENUE_CONCEPT = "RevenueFromContractWithCustomerExcludingAssessedTax"
_X1P_GROSS_PROFIT_CONCEPT = "GrossProfit"
_X1P_QUALIFICATION_ROOT = (
    ROOT / "tests" / "fixtures" / "fundamental_forensics" / "metric_registry_qualification"
)

# The JSON cell-node leaf paths (CellNode.to_dict / CellProvenance.to_dict /
# PeriodRequest.to_dict in engine/fundamental_forensics/query.py).
_X1P_CELL_FIELDS = (
    "cell_id",
    "governance_bundle_id",
    "ticker",
    "entity_id",
    "metric_id",
    "state",
    "status",
    "value",
    "unit",
    "reason",
)
_X1P_PERIOD_FIELDS = (
    "kind",
    "start",
    "end",
    "fiscal_year",
    "fiscal_quarter",
    "calendar_kind",
    "fiscal_year_weeks",
    "week_count",
    "inferred_week_count",
    "semantics",
    "label",
)
_X1P_PROVENANCE_FIELDS = (
    "kind",
    "evaluation_policy",
    "policy",
    "source_snapshot_at",
    "recorded_cutoff_at",
    "source_entity_id",
    "source",
    "accession",
    "document_id",
    "source_url",
    "source_body_sha256",
    "form",
    "filed_at",
    "filing_metadata_available_at",
    "filing_metadata_content_sha256",
    "accepted_at",
    "recorded_at",
    "mapping_available_at",
    "governance_available_at",
    "computed_at",
    "published_at",
    "source_ready_at",
    "system_ready_at",
    "concept_qname",
    "taxonomy",
    "concept",
    "unit",
    "metric_rule_id",
    "metric_rule_version",
    "metric_rule_digest",
    "mapping_rule_id",
    "mapping_rule_version",
    "mapping_digest",
    "mapping_rule_ids",
    "mapping_rule_versions",
    "mapping_digests",
    "formula_rule_id",
    "formula_rule_version",
    "formula_digest",
    "catalog_id",
    "catalog_version",
    "catalog_digest",
    "mapping_pack_version",
    "mapping_pack_digest",
    "formula_pack_version",
    "formula_pack_digest",
    "confidence",
    "alias_priority",
    "source_occurrence_ids",
    "dependency_cell_ids",
    "selected_raw_fact",
    "reason",
    # Conditional keys: present in JSON only on metric-qualification refusals.
    "issuer_class",
    "issuer_class_basis",
    # Conditional keys (step 5, after the not-presented clock): na_basis and
    # not_presented on a direct not-presented N/A cell; qualified_not_presented
    # on a qualified-sum formula VALUE.
    "na_basis",
    "not_presented",
    "qualified_not_presented",
)
_X1P_CONDITIONAL_PROVENANCE_FIELDS = frozenset(
    {
        "issuer_class",
        "issuer_class_basis",
        "na_basis",
        "not_presented",
        "qualified_not_presented",
    }
)
_X1P_FIELD_INVENTORY = frozenset(
    _X1P_CELL_FIELDS
    + tuple(f"period.{name}" for name in _X1P_PERIOD_FIELDS)
    + tuple(f"provenance.{name}" for name in _X1P_PROVENANCE_FIELDS)
)

# JSON field path -> column of the format's per-root-cell rows.  A field with
# no entry here is not carried by that format.  ``status`` maps onto the
# state column and ``provenance.reason`` onto the reason column because
# CellNode emits them as exact duplicates (state/status by construction,
# reason/provenance.reason enforced equal by CellNode.__post_init__).
# ``provenance.qualified_not_presented`` also maps onto the reason column: a
# qualified sum is a VALUE (JSON reason null) whose reason column carries the
# in-row marker naming the omitted operands.
_X1P_CSV_XLSX_COLUMN_BY_FIELD = {
    "cell_id": "root_cell_id",
    "governance_bundle_id": "governance_bundle_id",
    "ticker": "ticker",
    "entity_id": "entity_id",
    "metric_id": "metric_id",
    "period.kind": "period_kind",
    "period.start": "period_start",
    "period.end": "period_end",
    "period.fiscal_year": "period_fiscal_year",
    "period.fiscal_quarter": "period_fiscal_quarter",
    "state": "state",
    "status": "state",
    "value": "value",
    "unit": "unit",
    "reason": "reason",
    "provenance.reason": "reason",
    "provenance.kind": "provenance_kind",
    "provenance.accession": "accession",
    "provenance.document_id": "document_id",
    "provenance.form": "form",
    "provenance.filed_at": "filed_at",
    "provenance.filing_metadata_content_sha256": "filing_metadata_content_sha256",
    "provenance.accepted_at": "accepted_at",
    "provenance.recorded_at": "recorded_at",
    "provenance.mapping_available_at": "mapping_available_at",
    "provenance.governance_available_at": "governance_available_at",
    "provenance.source_ready_at": "source_ready_at",
    "provenance.system_ready_at": "system_ready_at",
    "provenance.concept_qname": "concept_qname",
    "provenance.mapping_rule_id": "mapping_rule_id",
    "provenance.mapping_rule_version": "mapping_rule_version",
    "provenance.mapping_digest": "mapping_digest",
    "provenance.formula_rule_id": "formula_rule_id",
    "provenance.formula_rule_version": "formula_rule_version",
    "provenance.formula_digest": "formula_digest",
    "provenance.confidence": "confidence",
    "provenance.source_occurrence_ids": "source_occurrence_ids",
    "provenance.dependency_cell_ids": "dependency_cell_ids",
    # In-row marker (query._export_reason_text): see _x1p_reason_column_leaf.
    "provenance.qualified_not_presented": "reason",
}
_X1P_PARQUET_COLUMN_BY_FIELD = {
    "cell_id": "root_cell_id",
    "ticker": "ticker",
    "entity_id": "entity_id",
    "metric_id": "metric_id",
    "period.kind": "period_kind",
    "period.start": "period_start",
    "period.end": "period_end",
    "period.fiscal_year": "period_fiscal_year",
    "period.fiscal_quarter": "period_fiscal_quarter",
    "state": "state",
    "status": "state",
    "value": "value",
    "unit": "unit",
    "reason": "reason",
    "provenance.reason": "reason",
    "provenance.kind": "provenance_kind",
    "provenance.accession": "accession",
    "provenance.document_id": "document_id",
    "provenance.concept_qname": "concept_qname",
    "provenance.mapping_rule_id": "mapping_rule_id",
    "provenance.mapping_rule_version": "mapping_rule_version",
    "provenance.formula_rule_id": "formula_rule_id",
    "provenance.formula_rule_version": "formula_rule_version",
    "provenance.accepted_at": "accepted_at",
    "provenance.recorded_at": "recorded_at",
    "provenance.source_ready_at": "source_ready_at",
    "provenance.system_ready_at": "system_ready_at",
    "provenance.source_occurrence_ids": "source_occurrence_ids_json",
    "provenance.dependency_cell_ids": "dependency_cell_ids_json",
    "provenance.qualified_not_presented": "reason",
}
_X1P_COLUMN_MAPS = {
    "csv": _X1P_CSV_XLSX_COLUMN_BY_FIELD,
    "xlsx": _X1P_CSV_XLSX_COLUMN_BY_FIELD,
    "parquet": _X1P_PARQUET_COLUMN_BY_FIELD,
}


def _x1p_fact(concept: str = _X1P_REVENUE_CONCEPT, **kwargs):
    return _fact(concept=concept, **kwargs)


def _x1p_parity_matrix() -> MetricMatrix:
    """Every reachable cell state, negative and non-IEEE values, one matrix."""
    facts = [
        _x1p_fact(entity_id="x1p-a", value="100"),
        _x1p_fact(_X1P_GROSS_PROFIT_CONCEPT, entity_id="x1p-a", value="40"),
        _x1p_fact(entity_id="x1p-b", value="-42"),
        _x1p_fact(entity_id="x1p-c", value="123456789012345678"),
        _x1p_fact(
            entity_id="x1p-d",
            value="7",
            accession="0000000009-26-000009",
            document_id="x1p-8k.htm",
        ),
        _x1p_fact(entity_id="x1p-e", value="-0.1"),
        _x1p_fact(entity_id="x1p-f", value="5", unit=FactUnit("EUR", ["iso4217:EUR"])),
    ]
    entities = {
        "AAA": "x1p-a",
        "BBB": "x1p-b",
        "CCC": "x1p-c",
        "DDD": "x1p-d",
        "EEE": "x1p-e",
        "FFF": "x1p-f",
    }
    metadata = {
        fact.occurrence_id: {
            "accession": fact.source.accession,
            "document_id": fact.source.document_id,
            "source_body_sha256": fact.source.body_sha256,
            "available_at": fact.recorded_at,
            "form": "8-K" if fact.source.entity_id == "x1p-d" else "10-K",
        }
        for fact in facts
    }
    engine = _engine(*facts, entities=entities, filing_metadata=metadata)
    return engine.query_matrix(
        tickers=tuple(entities),
        metrics=("revenue", "gross_profit", "gross_margin"),
        periods=(PERIOD,),
        policy=_policy(),
    )


def _x1p_probe_matrix() -> MetricMatrix:
    """Free-text fields whose values begin with a formula-injection lead."""
    probes = {"P1": "=", "P2": "+", "P3": "-", "P4": "@"}
    facts = []
    entities = {}
    for ticker, lead in probes.items():
        entity_id = f"{lead}x1p-entity"
        facts.append(
            _x1p_fact(
                entity_id=entity_id,
                value="11",
                accession=f"{lead}x1p-acc",
                document_id=f"{lead}x1p-doc.htm",
            )
        )
        entities[ticker] = entity_id
    engine = _engine(*facts, entities=entities)
    return engine.query_matrix(
        tickers=tuple(entities),
        metrics=("revenue",),
        periods=(PERIOD,),
        policy=_policy(),
    )


def _x1p_not_applicable_matrix() -> MetricMatrix:
    """A metric-qualification refusal with issuer_class provenance.

    Uses the committed qualification registry fixture (bank SIC + a
    bank-excluded gross_margin contract) exactly as
    tests/test_fundamental_forensics_query_metric_qualification.py drives it.
    """
    registry = load_metric_registry(
        _X1P_QUALIFICATION_ROOT / "metric_catalog.yaml",
        _X1P_QUALIFICATION_ROOT / "mappings.yaml",
        _X1P_QUALIFICATION_ROOT / "formulas.yaml",
        enforce_core_v1_inventory=False,
    )
    engine = BitemporalMetricQueryEngine(
        RawFactLedger(()),
        registry,
        entities=[QueryEntity(ticker="AAA", entity_id="0000000001", issuer_sic="6020")],
        filing_metadata=None,
    )
    return engine.query_matrix(
        tickers=["AAA"],
        metrics=["gross_margin"],
        periods=[PERIOD],
        policy=_policy(),
    )


@functools.lru_cache(maxsize=None)
def _x1p_not_presented_matrices(recorded: str) -> tuple[MetricMatrix, MetricMatrix]:
    """Step-5 cells over the not-presented fixture filing.

    After the not-presented clock the first matrix holds a qualified sum
    (total_debt omits the not-presented short_term_debt), a consumer that
    inherits the qualifier (net_debt) and the direct not-presented N/A cell;
    the second holds a formula N/A (every operand not presented) beside the
    direct N/A.  Before the clock the same engines answer with ordinary
    absences, so ``recorded`` selects the side of the clock.
    """
    pack = load_not_presented_pack()
    policy = _policy(source=recorded, recorded=recorded)
    debt = _debt_engine(pack).query_matrix(
        tickers=["AAA"],
        metrics=["total_debt", "short_term_debt", "net_debt"],
        periods=[_NP_INSTANT],
        policy=policy,
    )
    no_debt = _debt_engine(pack, NO_DEBT_FACTS, NO_DEBT_ARCS).query_matrix(
        tickers=["AAA"],
        metrics=["total_debt", "short_term_debt"],
        periods=[_NP_INSTANT],
        policy=policy,
    )
    return debt, no_debt


def _x1p_matrices() -> list[MetricMatrix]:
    return [
        _x1p_parity_matrix(),
        _x1p_probe_matrix(),
        _x1p_not_applicable_matrix(),
        *_x1p_not_presented_matrices(_NP_AFTER),
    ]


def _x1p_root_nodes(matrix: MetricMatrix) -> list[dict]:
    receipt = matrix.to_dict()
    nodes = {node["cell_id"]: node for node in receipt["nodes"]}
    return [nodes[cell_id] for cell_id in receipt["root_cell_ids"]]


def _x1p_json_leaf(node: dict, path: str):
    """Leaf value of a dotted JSON path; a conditional absent key is None."""
    value = node
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _x1p_wire_text(leaf, *, csv_safe: bool) -> str | None:
    """The exact wire spelling of a JSON leaf in an export column."""
    if leaf is None:
        return None
    if isinstance(leaf, bool):
        leaf = "true" if leaf else "false"
    elif isinstance(leaf, int):
        leaf = str(leaf)
    if isinstance(leaf, (list, tuple)):
        leaf = canonical_json(list(leaf))
    text = str(leaf)
    return _csv_safe(text) if csv_safe else text


def _x1p_csv_rows(matrix: MetricMatrix) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(matrix.to_csv_bytes().decode("utf-8"))))


def _x1p_parquet_rows(matrix: MetricMatrix) -> list[dict[str, str | None]]:
    """Decode the exact bytes the parquet export route returns.

    The route payload is ``_encode_cells_parquet(matrix)[0]``
    (query_exports.export_query_envelope -> query_snapshots), and
    ``_decode_cells_parquet`` (query_snapshots.py) re-validates those rows
    against the authoritative matrix projection.
    """
    import pyarrow.parquet as pq

    payload, _projection = _encode_cells_parquet(matrix)
    table = pq.read_table(io.BytesIO(payload))
    return [
        {name: table.column(name)[index].as_py() for name in table.column_names}
        for index in range(table.num_rows)
    ]


def _x1p_xlsx_response(matrix: MetricMatrix) -> dict:
    return {
        "schema": "fundamental_forensics.financial_query_response/v1",
        "receipt": matrix.to_dict(),
        "query_hash": matrix.query_hash,
        "sha256": hashlib.sha256(matrix.to_json_bytes()).hexdigest(),
    }


def _x1p_xlsx_sheet(matrix: MetricMatrix) -> tuple[list[str], list[dict[str, str]], dict[str, set[str]]]:
    """Header, per-root-cell records, and which cells are numeric (<v>)."""
    payload = to_xlsx_bytes(_x1p_xlsx_response(matrix))
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    row_elements = root.findall(f"{{{_SSML_NS}}}sheetData/{{{_SSML_NS}}}row")
    header: list[str] = []
    records: list[dict[str, str]] = []
    numeric_by_id: dict[str, set[str]] = {}
    for row_index, row_element in enumerate(row_elements):
        by_column: dict[int, tuple[str, bool]] = {}
        for cell in row_element.findall(f"{{{_SSML_NS}}}c"):
            ref = cell.get("r") or ""
            letters = ref[: len(ref) - len(ref.lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))]
            column = 0
            for character in letters:
                column = column * 26 + ord(character) - 64
            if cell.get("t") == "inlineStr":
                text_element = cell.find(f"{{{_SSML_NS}}}is/{{{_SSML_NS}}}t")
                by_column[column] = (
                    "" if text_element is None else (text_element.text or ""),
                    False,
                )
            else:
                value_element = cell.find(f"{{{_SSML_NS}}}v")
                by_column[column] = (
                    "" if value_element is None else (value_element.text or ""),
                    True,
                )
        width = max(by_column, default=0)
        cells = [by_column.get(index, ("", False)) for index in range(1, width + 1)]
        if row_index == 0:
            header = [text for text, _is_numeric in cells]
            continue
        record: dict[str, str] = {name: "" for name in header}
        numeric_columns: set[str] = set()
        for name, (text, is_numeric) in zip(header, cells):
            record[name] = text
            if is_numeric:
                numeric_columns.add(name)
        cell_id = record.get("root_cell_id", "")
        records.append(record)
        numeric_by_id[cell_id] = numeric_columns
    return header, records, numeric_by_id


def _x1p_xlsx_meta(payload: bytes) -> dict[str, str]:
    """Meta sheet key/value rows, parsed as the excel-export tests do."""
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        root = ET.fromstring(archive.read("xl/worksheets/sheet2.xml"))
    meta: dict[str, str] = {}
    for row_element in root.findall(f"{{{_SSML_NS}}}sheetData/{{{_SSML_NS}}}row"):
        cells = row_element.findall(f"{{{_SSML_NS}}}c")
        if len(cells) < 2:
            continue
        key = cells[0].findtext(f"{{{_SSML_NS}}}is/{{{_SSML_NS}}}t") or ""
        value = cells[1].findtext(f"{{{_SSML_NS}}}is/{{{_SSML_NS}}}t")
        if value is not None:
            meta[key] = value
    return meta


def _x1p_ref_row(ref: str) -> int:
    letters = len(ref) - len(ref.lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
    return int(ref[letters:])


def _x1p_xlsx_value_text_cells(matrix: MetricMatrix) -> dict[str, str]:
    """A1 ref -> inlineStr text of every Response value cell written as text."""
    payload = to_xlsx_bytes(_x1p_xlsx_response(matrix))
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    value_column: int | None = None
    text_cells: dict[str, str] = {}
    for row_element in root.findall(f"{{{_SSML_NS}}}sheetData/{{{_SSML_NS}}}row"):
        row_number = int(row_element.get("r"))
        for cell in row_element.findall(f"{{{_SSML_NS}}}c"):
            if cell.get("t") != "inlineStr":
                continue
            ref = cell.get("r") or ""
            letters = ref[: len(ref) - len(ref.lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))]
            column = 0
            for character in letters:
                column = column * 26 + ord(character) - 64
            text = cell.findtext(f"{{{_SSML_NS}}}is/{{{_SSML_NS}}}t")
            if text is None:
                text = ""
            if row_number == 1:
                if text == "value":
                    value_column = column
                continue
            if column == value_column:
                text_cells[ref] = text
    return text_cells


def _x1p_rows(fmt: str, matrix: MetricMatrix) -> list[dict]:
    if fmt == "csv":
        return _x1p_csv_rows(matrix)
    if fmt == "xlsx":
        return _x1p_xlsx_sheet(matrix)[1]
    if fmt == "parquet":
        return _x1p_parquet_rows(matrix)
    raise AssertionError(f"unknown format {fmt!r}")


_X1P_REASON_COLUMN_FIELDS = frozenset(
    {"reason", "provenance.reason", "provenance.qualified_not_presented"}
)


def _x1p_reason_column_leaf(field: str, leaf, node: dict):
    """What the reason column must spell for ``field``, per the declaration.

    A qualified sum (JSON reason null, provenance.qualified_not_presented
    printed) carries the marker followed by the omitted operand IDs; every
    other cell carries its JSON reason verbatim.  The qualifier field is
    therefore carried exactly when the marker appears on the qualified cells
    and nowhere else, so the reason and the qualifier both stay recoverable.
    """
    qualified = node["provenance"].get("qualified_not_presented")
    if qualified:
        return QUALIFIED_NOT_PRESENTED_EXPORT_PREFIX + ", ".join(qualified)
    if field == "provenance.qualified_not_presented":
        return node["reason"]
    return leaf


def _x1p_field_carried(
    fmt: str, field: str, leaf, row: dict, numeric_columns: set[str], node: dict
) -> bool:
    """Does the format's row carry the JSON leaf exactly, per its encoding?"""
    if field in _X1P_REASON_COLUMN_FIELDS:
        leaf = _x1p_reason_column_leaf(field, leaf, node)
    if fmt == "parquet":
        return row.get(_X1P_PARQUET_COLUMN_BY_FIELD.get(field, "")) == _x1p_wire_text(
            leaf, csv_safe=False
        )
    column = _X1P_CSV_XLSX_COLUMN_BY_FIELD.get(field, "")
    expected = _x1p_wire_text(leaf, csv_safe=field != "value")
    expected_text = "" if expected is None else expected
    if fmt == "csv":
        return row.get(column, "") == expected_text
    # XLSX: the value column is a numeric cell with the exact decimal text,
    # or (non-IEEE-754 values only) an inlineStr cell carrying that exact
    # decimal text verbatim — no _csv_safe apostrophe (excel_export
    # _ExactText), ref listed in the Meta sheet exact_text_cells.
    if field == "value":
        if leaf is None:
            return row.get(column, "") == ""
        if column in numeric_columns:
            return row.get(column, "") == _x1p_wire_text(leaf, csv_safe=False)
        return row.get(column, "") == expected_text
    return row.get(column, "") == expected_text


def _x1p_rows_by_id(fmt: str, matrix: MetricMatrix) -> dict[str, dict]:
    return {row["root_cell_id"]: row for row in _x1p_rows(fmt, matrix)}


@pytest.mark.parametrize("fmt", ("csv", "xlsx", "parquet"))
def test_a38_x1p_every_carried_field_is_identical_per_cell(fmt: str) -> None:
    """(a) JSON vs CSV vs XLSX vs Parquet: exact value, cutoff, basis,
    provenance for EVERY field the format carries."""
    for matrix in _x1p_matrices():
        rows = _x1p_rows_by_id(fmt, matrix)
        numeric_by_id = _x1p_xlsx_sheet(matrix)[2] if fmt == "xlsx" else {}
        assert set(rows) == {node["cell_id"] for node in _x1p_root_nodes(matrix)}
        for node in _x1p_root_nodes(matrix):
            row = rows[node["cell_id"]]
            numeric_columns = numeric_by_id.get(node["cell_id"], set())
            for field in _X1P_FIELD_INVENTORY:
                column = _X1P_COLUMN_MAPS[fmt].get(field)
                if column is None:
                    continue
                leaf = _x1p_json_leaf(node, field)
                assert _x1p_field_carried(fmt, field, leaf, row, numeric_columns, node), (
                    fmt,
                    field,
                    node["cell_id"],
                    leaf,
                    row.get(column, "<missing>"),
                )


def test_a38_x1p_decimal_value_exact_roundtrip_all_formats() -> None:
    """(a) The normalized value compares as an exact Decimal everywhere."""
    for matrix in _x1p_matrices():
        csv_rows = _x1p_rows_by_id("csv", matrix)
        parquet_rows = _x1p_rows_by_id("parquet", matrix)
        _, xlsx_records, numeric_by_id = _x1p_xlsx_sheet(matrix)
        xlsx_rows = {row["root_cell_id"]: row for row in xlsx_records}
        for node in _x1p_root_nodes(matrix):
            cell_id = node["cell_id"]
            json_value = node["value"]
            csv_value = csv_rows[cell_id]["value"]
            parquet_value = parquet_rows[cell_id]["value"]
            xlsx_value = xlsx_rows[cell_id]["value"]
            if json_value is None:
                assert csv_value == ""
                assert parquet_value is None
                assert xlsx_value == ""
                continue
            assert Decimal(csv_value) == Decimal(json_value)
            assert Decimal(parquet_value) == Decimal(json_value)
            assert csv_value == json_value == parquet_value
            if "value" in numeric_by_id[cell_id]:
                assert xlsx_value == json_value
            else:
                # Exact-text value cells carry the same exact decimal with
                # no _csv_safe apostrophe (excel_export._ExactText).
                assert xlsx_value == json_value


def test_a38_x1p_omitted_cell_fields_declaration_is_exact() -> None:
    """(b) Undeclared omissions fail; declared fields that are carried fail."""
    for fmt in ("csv", "xlsx", "parquet"):
        column_map = _X1P_COLUMN_MAPS[fmt]
        omitted: set[str] = set()
        for field in _X1P_FIELD_INVENTORY:
            column = column_map.get(field)
            if column is None:
                omitted.add(field)
                continue
            carried_everywhere = True
            for matrix in _x1p_matrices():
                rows = _x1p_rows_by_id(fmt, matrix)
                numeric_by_id = _x1p_xlsx_sheet(matrix)[2] if fmt == "xlsx" else {}
                for node in _x1p_root_nodes(matrix):
                    if not _x1p_field_carried(
                        fmt,
                        field,
                        _x1p_json_leaf(node, field),
                        rows[node["cell_id"]],
                        numeric_by_id.get(node["cell_id"], set()),
                        node,
                    ):
                        carried_everywhere = False
                        break
                if not carried_everywhere:
                    break
            if not carried_everywhere:
                omitted.add(field)
        declared = set(SERIALIZATION_DIFFERENCES[fmt]["omitted_cell_fields"])
        assert omitted == declared, (
            fmt,
            "undeclared omissions: " + repr(sorted(omitted - declared)),
            "declared but carried: " + repr(sorted(declared - omitted)),
            "unknown declared paths: "
            + repr(sorted(declared - _X1P_FIELD_INVENTORY)),
        )


def test_a38_x1p_field_inventory_matches_json_wire_keys() -> None:
    """The test inventory is the JSON cell wire surface, no drift."""
    conditional = set(_X1P_CONDITIONAL_PROVENANCE_FIELDS)
    conditional_seen: set[str] = set()
    for matrix in _x1p_matrices():
        for node in _x1p_root_nodes(matrix):
            assert set(_X1P_CELL_FIELDS) == {
                key for key in node if key not in ("period", "provenance")
            }
            assert set(_X1P_PERIOD_FIELDS) == set(node["period"])
            provenance_keys = set(node["provenance"])
            inventory_keys = set(_X1P_PROVENANCE_FIELDS)
            assert provenance_keys - inventory_keys == set()
            assert inventory_keys - provenance_keys <= conditional
            conditional_seen |= provenance_keys & conditional
    # The refusal cell (issuer_class*) and the step-5 cells (na_basis,
    # not_presented, qualified_not_presented) must all be in the fixture set,
    # or a conditional key would escape the completeness law.
    assert conditional_seen == conditional, sorted(conditional - conditional_seen)


def test_a40_x1p_no_unguarded_formula_leads_in_csv_or_xlsx() -> None:
    """(c) No text cell begins with a formula lead unless apostrophe-prefixed."""
    for matrix in _x1p_matrices():
        raw_rows = list(csv.reader(io.StringIO(matrix.to_csv_bytes().decode("utf-8"))))
        header = raw_rows[0]
        value_index = header.index("value")
        for row in raw_rows[1:]:
            for index, text in enumerate(row):
                if index == value_index:
                    assert not text.startswith("'"), (row[0], text)
                    if text:
                        assert Decimal(text).is_finite()
                    continue
                assert not text or text[0] not in _DANGEROUS_PREFIXES or text.startswith("'")
        _, xlsx_records, numeric_by_id = _x1p_xlsx_sheet(matrix)
        for record in xlsx_records:
            for name, text in record.items():
                if name in numeric_by_id[record["root_cell_id"]]:
                    continue
                if name == "value":
                    # Same exemption as the CSV loop above: the exact
                    # decimal text of a non-IEEE value is written verbatim
                    # (excel_export._ExactText, no _csv_safe apostrophe).
                    assert not text.startswith("'"), (record["root_cell_id"], text)
                    if text:
                        assert Decimal(text).is_finite()
                    continue
                assert not text or text[0] not in _DANGEROUS_PREFIXES or text.startswith("'")


def test_a40_x1p_negative_and_non_ieee_values() -> None:
    """(c) Negatives stay numeric; non-IEEE values become exact text cells."""
    matrix = _x1p_parity_matrix()
    csv_rows = {
        (row["ticker"], row["metric_id"]): row for row in _x1p_csv_rows(matrix)
    }
    parquet_rows = _x1p_parquet_rows(matrix)
    parquet_by_key = {
        (row["ticker"], row["metric_id"]): row for row in parquet_rows
    }
    _, xlsx_records, numeric_by_id = _x1p_xlsx_sheet(matrix)
    xlsx_by_key = {(row["ticker"], row["metric_id"]): row for row in xlsx_records}

    # IEEE-754-exact negative: numeric everywhere, never apostrophe-prefixed.
    assert csv_rows[("BBB", "revenue")]["value"] == "-42"
    assert parquet_by_key[("BBB", "revenue")]["value"] == "-42"
    bbb_xlsx = xlsx_by_key[("BBB", "revenue")]
    assert "value" in numeric_by_id[bbb_xlsx["root_cell_id"]]
    assert bbb_xlsx["value"] == "-42"

    # Non-IEEE positive (>15 significant digits): exact text cell, no prefix.
    ccc_xlsx = xlsx_by_key[("CCC", "revenue")]
    assert "value" not in numeric_by_id[ccc_xlsx["root_cell_id"]]
    assert ccc_xlsx["value"] == "123456789012345678"

    # Declared exception: a negative non-IEEE value is an inlineStr cell
    # carrying the exact decimal text verbatim — no _csv_safe apostrophe,
    # same spelling as the exempt CSV value column and Parquet — and its
    # A1 reference is listed in the Meta sheet exact_text_cells.
    assert csv_rows[("EEE", "revenue")]["value"] == "-0.1"
    assert parquet_by_key[("EEE", "revenue")]["value"] == "-0.1"
    eee_xlsx = xlsx_by_key[("EEE", "revenue")]
    assert "value" not in numeric_by_id[eee_xlsx["root_cell_id"]]
    assert eee_xlsx["value"] == "-0.1"
    value_texts = _x1p_xlsx_value_text_cells(matrix)
    eee_row = (
        next(
            index
            for index, record in enumerate(xlsx_records)
            if record["ticker"] == "EEE" and record["metric_id"] == "revenue"
        )
        + 2
    )
    eee_ref = next(ref for ref in value_texts if _x1p_ref_row(ref) == eee_row)
    meta = _x1p_xlsx_meta(to_xlsx_bytes(_x1p_xlsx_response(matrix)))
    assert eee_ref in (meta.get("exact_text_cells") or "").split(",")
    joined = " ".join(SERIALIZATION_DIFFERENCES["xlsx"]["encoding"])
    assert "no `'` prefix, negative included" in joined
    assert "exact_text_cells" in joined


def test_a40_x1p_exact_text_cells_list_every_non_ieee_value_cell() -> None:
    """(b) Meta exact_text_cells == the value cells written as exact text."""
    matrix = _x1p_parity_matrix()
    value_texts = _x1p_xlsx_value_text_cells(matrix)
    assert value_texts, "fixture must carry at least one non-IEEE value"
    meta = _x1p_xlsx_meta(to_xlsx_bytes(_x1p_xlsx_response(matrix)))
    listed = (meta.get("exact_text_cells") or "").split(",")
    assert meta.get("exact_text_cells")
    assert set(listed) == set(value_texts)
    raw_rows = list(csv.reader(io.StringIO(matrix.to_csv_bytes().decode("utf-8"))))
    value_index = raw_rows[0].index("value")
    for ref, text in value_texts.items():
        # Byte-for-byte the CSV value-column spelling of the same row, and
        # a parseable Decimal.
        assert text == raw_rows[_x1p_ref_row(ref) - 1][value_index]
        Decimal(text)


def test_a40_x1p_direct_non_ieee_paths_are_exact_text_cells() -> None:
    """(c) Direct int/Decimal paths: exact text, no apostrophe, Meta-listed."""
    response = {
        "schema": "fundamental_forensics.financial_query_response/v1",
        "query_id": "q-x1p-r1",
        "query_hash": "ab" * 32,
        "sha256": "cd" * 32,
        "rows": [
            ["neg_int", "neg_decimal", "nan", "neg_inf"],
            [
                -123456789012345678,
                Decimal("-0.1"),
                Decimal("NaN"),
                Decimal("-Infinity"),
            ],
        ],
    }
    payload = to_xlsx_bytes(response)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    grid: dict[str, tuple[str, str]] = {}
    for cell in root.iter(f"{{{_SSML_NS}}}c"):
        if cell.get("t") == "inlineStr":
            text = cell.findtext(f"{{{_SSML_NS}}}is/{{{_SSML_NS}}}t") or ""
            grid[cell.get("r") or ""] = ("inlineStr", text)
        else:
            text = cell.findtext(f"{{{_SSML_NS}}}v") or ""
            grid[cell.get("r") or ""] = ("v", text)
    assert grid["A2"] == ("inlineStr", "-123456789012345678")
    assert grid["B2"] == ("inlineStr", "-0.1")
    # Non-finite Decimals keep the _csv_safe form (unchanged path).
    assert grid["C2"] == ("inlineStr", _csv_safe(str(Decimal("NaN"))))
    assert grid["D2"] == ("inlineStr", _csv_safe("-Infinity"))
    assert grid["D2"] == ("inlineStr", "'-Infinity")
    meta = _x1p_xlsx_meta(payload)
    assert set((meta.get("exact_text_cells") or "").split(",")) == {"A2", "B2"}


def test_a40_x1p_probe_leads_apostrophe_guarded_end_to_end() -> None:
    """(c) The four survivable leads are guarded in CSV/XLSX, verbatim in Parquet."""
    matrix = _x1p_probe_matrix()
    for fmt in ("csv", "xlsx"):
        for row in _x1p_rows(fmt, matrix):
            stored = row["entity_id"]
            assert stored.startswith("'"), stored
            lead = stored[1]
            assert row["entity_id"] == _csv_safe(f"{lead}x1p-entity")
            assert row["accession"] == _csv_safe(f"{lead}x1p-acc")
            assert row["document_id"] == _csv_safe(f"{lead}x1p-doc.htm")
    for row in _x1p_parquet_rows(matrix):
        # Declared difference: Parquet stores text verbatim (no _csv_safe).
        assert row["entity_id"] in {
            "=x1p-entity",
            "+x1p-entity",
            "-x1p-entity",
            "@x1p-entity",
        }
        assert row["accession"] in {"=x1p-acc", "+x1p-acc", "-x1p-acc", "@x1p-acc"}
    for probe in ("=1+1", "+lead", "-lead", "@cmd", "\tled", "\rled"):
        assert _csv_safe(probe) == f"'{probe}"


def test_a40_x1p_csv_appends_three_provenance_columns_last() -> None:
    """(d) The three S1 columns close the header, in order, carrying JSON."""
    for matrix in _x1p_matrices():
        raw_rows = list(csv.reader(io.StringIO(matrix.to_csv_bytes().decode("utf-8"))))
        header = raw_rows[0]
        assert header[-3:] == [
            "provenance_kind",
            "document_id",
            "filing_metadata_content_sha256",
        ]
        assert header.index("value") == 15
        rows_by_id = {row[header.index("root_cell_id")]: row for row in raw_rows[1:]}
        for node in _x1p_root_nodes(matrix):
            row = rows_by_id[node["cell_id"]]
            provenance = node["provenance"]
            assert row[-3] == _csv_safe(provenance["kind"])
            assert row[-2] == _csv_safe(provenance["document_id"] or "")
            assert row[-1] == _csv_safe(provenance["filing_metadata_content_sha256"] or "")


def test_a40_x1p_every_csv_column_is_mapped_or_receipt_scalar() -> None:
    """(d) A carried CSV column with no column-map entry fails the pin."""
    # Excluded by design: the four receipt-level scalar columns
    # MetricMatrix.to_csv_bytes repeats on every row from the receipt
    # itself (query.py:3859-3862 header, :3909-3912 row values) — they are
    # not per-root-cell JSON fields, so they hold no
    # _X1P_CSV_XLSX_COLUMN_BY_FIELD entry.
    receipt_scalars = {
        "query_hash",
        "receipt_authority",
        "proof_scope",
        "selection_proof",
    }
    mapped = set(_X1P_CSV_XLSX_COLUMN_BY_FIELD.values())
    for matrix in _x1p_matrices():
        header = next(csv.reader(io.StringIO(matrix.to_csv_bytes().decode("utf-8"))))
        unmapped = set(header) - receipt_scalars - mapped
        assert not unmapped, f"CSV columns with no column-map entry: {sorted(unmapped)}"
        phantom = mapped - set(header)
        assert not phantom, f"mapped columns absent from the CSV header: {sorted(phantom)}"


def test_a38_x1p_kernel_exports_are_deterministic() -> None:
    """(e) Two exports of the same matrix are byte-identical."""
    for matrix in _x1p_matrices():
        assert matrix.to_csv_bytes() == matrix.to_csv_bytes()
        response = _x1p_xlsx_response(matrix)
        assert to_xlsx_bytes(response) == to_xlsx_bytes(response)
        assert _encode_cells_parquet(matrix)[0] == _encode_cells_parquet(matrix)[0]


def test_a38_x1p_not_applicable_issuer_class_is_json_only() -> None:
    """The conditional refusal provenance appears in no export column."""
    matrix = _x1p_not_applicable_matrix()
    node = _x1p_root_nodes(matrix)[0]
    assert node["state"] == "not_applicable"
    assert node["provenance"]["issuer_class"] == "bank"
    assert node["provenance"]["issuer_class_basis"] == "sic"
    for fmt in ("csv", "xlsx", "parquet"):
        for row in _x1p_rows(fmt, matrix):
            assert "bank" not in {str(value) for value in row.values()}
        assert "provenance.issuer_class" in SERIALIZATION_DIFFERENCES[fmt][
            "omitted_cell_fields"
        ]
        assert "provenance.issuer_class_basis" in SERIALIZATION_DIFFERENCES[fmt][
            "omitted_cell_fields"
        ]


def test_a38_x1p_provenance_unit_omission_is_genuine() -> None:
    """cell.unit != provenance.unit is reachable; the unit column is the cell's."""
    matrix = _x1p_parity_matrix()
    node = next(
        node
        for node in _x1p_root_nodes(matrix)
        if node["ticker"] == "FFF" and node["metric_id"] == "revenue"
    )
    assert node["state"] == "not_evaluable"
    assert node["unit"] == "USD"
    assert node["provenance"]["unit"] is None
    for fmt in ("csv", "xlsx", "parquet"):
        row = _x1p_rows_by_id(fmt, matrix)[node["cell_id"]]
        assert row["unit"] == "USD"
        assert "provenance.unit" in SERIALIZATION_DIFFERENCES[fmt]["omitted_cell_fields"]


def test_x1p_serialization_differences_declaration_shape() -> None:
    """The declaration is immutable, machine-readable, and covers the laws."""
    assert set(SERIALIZATION_DIFFERENCES) == {"csv", "xlsx", "parquet"}
    required_notes = {
        "csv": ("_csv_safe", "canonical-JSON", "nulls are the empty string"),
        "xlsx": (
            "_csv_safe",
            "canonical-JSON",
            "nulls are the empty string",
            "_fits_ieee754",
        ),
        "parquet": ("STRING", "canonical-JSON", "null STRING", "no _csv_safe"),
    }
    # Every tabular format declares the qualified-sum marker in its reason column.
    required_notes = {
        fmt: (*notes, QUALIFIED_NOT_PRESENTED_EXPORT_PREFIX)
        for fmt, notes in required_notes.items()
    }
    for fmt, notes in required_notes.items():
        entry = SERIALIZATION_DIFFERENCES[fmt]
        assert set(entry) == {"omitted_cell_fields", "encoding"}
        fields = entry["omitted_cell_fields"]
        assert isinstance(fields, tuple)
        assert all(isinstance(item, str) for item in fields)
        assert len(set(fields)) == len(fields)
        assert set(fields) <= _X1P_FIELD_INVENTORY
        encoding = entry["encoding"]
        assert isinstance(encoding, tuple)
        joined = " ".join(encoding)
        for note in notes:
            assert note in joined, (fmt, note)
    with pytest.raises(TypeError):
        SERIALIZATION_DIFFERENCES["csv"] = {}  # type: ignore[index]


# ---------------------------------------------------------------------------
# Step-5 qualified sums: the qualifier survives every tabular export, and the
# marker that carries it changes no byte of any export before the clock.
# ---------------------------------------------------------------------------

_QUALIFIED_MARKER = QUALIFIED_NOT_PRESENTED_EXPORT_PREFIX + "short_term_debt"


@pytest.mark.parametrize("fmt", ("csv", "xlsx", "parquet"))
def test_a38_x1p_qualified_sum_marker_names_the_omitted_operands(fmt: str) -> None:
    """A qualified sum never reads as a plain sum in CSV, XLSX or Parquet.

    total_debt omits the not-presented short_term_debt and net_debt inherits
    the qualifier: both rows must name the omitted operand in the reason
    column, while the direct not-presented cell keeps its own reason and no
    unqualified cell anywhere carries the marker.
    """
    debt, _no_debt = _x1p_not_presented_matrices(_NP_AFTER)
    nodes = {node["metric_id"]: node for node in _x1p_root_nodes(debt)}
    assert nodes["total_debt"]["provenance"]["qualified_not_presented"] == ["short_term_debt"]
    assert nodes["net_debt"]["provenance"]["qualified_not_presented"] == ["short_term_debt"]
    assert nodes["total_debt"]["reason"] is None
    rows = {row["metric_id"]: row for row in _x1p_rows(fmt, debt)}
    for metric_id, value in (("total_debt", "1050"), ("net_debt", "850")):
        assert rows[metric_id]["state"] == "value", (fmt, metric_id)
        assert rows[metric_id]["value"] == value, (fmt, metric_id)
        assert rows[metric_id]["reason"] == _QUALIFIED_MARKER, (fmt, metric_id)
    assert rows["short_term_debt"]["state"] == "not_applicable"
    assert rows["short_term_debt"]["reason"] == "not_presented"
    for matrix in _x1p_matrices():
        for node in _x1p_root_nodes(matrix):
            if node["provenance"].get("qualified_not_presented"):
                continue
            row = _x1p_rows_by_id(fmt, matrix)[node["cell_id"]]
            assert not (row["reason"] or "").startswith(
                QUALIFIED_NOT_PRESENTED_EXPORT_PREFIX
            ), (fmt, node["cell_id"])


def test_a38_x1p_qualified_sum_csv_row_bytes_name_the_operand() -> None:
    """The raw CSV line of the qualified sum spells the omitted operand."""
    debt, _no_debt = _x1p_not_presented_matrices(_NP_AFTER)
    lines = debt.to_csv_bytes().splitlines()
    total_debt = [line for line in lines if b",total_debt," in line]
    assert len(total_debt) == 1
    assert _QUALIFIED_MARKER.encode("utf-8") in total_debt[0]


def _x1p_export_payloads(matrix: MetricMatrix) -> dict[str, bytes]:
    return {
        "csv": matrix.to_csv_bytes(),
        "xlsx": to_xlsx_bytes(_x1p_xlsx_response(matrix)),
        "parquet": _encode_cells_parquet(matrix)[0],
    }


def _x1p_export_digests(matrix: MetricMatrix) -> dict[str, str]:
    """Environment-independent digests of the three tabular exports.

    CSV is pinned as raw bytes.  XLSX is pinned per decompressed member (the
    deflate stream may differ across zlib builds) and Parquet as its decoded
    rows (the file carries writer metadata of the installed pyarrow); the
    raw XLSX and Parquet bytes are compared in-process below instead.
    """
    import pyarrow.parquet as pq

    payloads = _x1p_export_payloads(matrix)
    with zipfile.ZipFile(io.BytesIO(payloads["xlsx"])) as archive:
        members = [
            [name, hashlib.sha256(archive.read(name)).hexdigest()]
            for name in archive.namelist()
        ]
    rows = pq.ParquetFile(io.BytesIO(payloads["parquet"])).read(use_threads=False).to_pylist()
    return {
        "csv": hashlib.sha256(payloads["csv"]).hexdigest(),
        "xlsx_members": hashlib.sha256(canonical_json(members).encode("utf-8")).hexdigest(),
        "parquet_rows": hashlib.sha256(canonical_json(rows).encode("utf-8")).hexdigest(),
    }


def _x1p_pre_clock_matrices() -> dict[str, MetricMatrix]:
    debt, no_debt = _x1p_not_presented_matrices(_NP_BEFORE)
    return {
        "parity": _x1p_parity_matrix(),
        "probe": _x1p_probe_matrix(),
        "not_applicable": _x1p_not_applicable_matrix(),
        "debt_before_clock": debt,
        "no_debt_before_clock": no_debt,
    }


# Produced by the encoder BEFORE the qualifier marker existed (PR #9794 head
# e730669a, reason column = cell.reason), with _x1p_export_digests verbatim.
_X1P_PRE_CLOCK_EXPORT_PINS = {
    "parity": {
        "csv": "b719080fe3637d0cb1cb8a588f1fd8f02f26e553acf5a8fd787fce3e80eaafcd",
        "xlsx_members": "210e9cf17fe206e4aa8a930a88b1df3d189cfe969af66923af3578256f59768a",
        "parquet_rows": "f2d0d66c75914c282ba4cecd09965971beace09623ee5f2edf1e05499fd1bd76",
    },
    "probe": {
        "csv": "50fdd9b65be45c3b1d512a0702c2f8841ec228c06804158c8928b43e4c0e4c7c",
        "xlsx_members": "c2b69955c131af6aff3b34c7d5c1c7462f9d35dd9e8bc3609f5671a30938b65a",
        "parquet_rows": "8769011858d70f73e4367e1db34c916f2d24b9e0d274513120ac72a9a19d4628",
    },
    "not_applicable": {
        "csv": "b6a0cf7f6951d3d1ec4b659ef692264b517cdf265e4bb6d67e9907dcf9ef47cb",
        "xlsx_members": "584460166ba2de7cf3952575f4e403bcdde70bf824c21878f1e45cf2c7fd9442",
        "parquet_rows": "632d466cce7f93b274e88268cc7ef2c54a630e5aa30d6c5bcfa2fbfa0a65970d",
    },
    "debt_before_clock": {
        "csv": "bb3eed597652593f5c86904f81a744553ceefc802c13d241468d67c408bc2966",
        "xlsx_members": "8313050a5414f05e7d77c9e617882a5e0c35855307fd5e82e6fd3bfc7900ef5b",
        "parquet_rows": "75f8ac455d5fb7636f3532585bcfd4ee96a3cc224cbcb4286aca6594444208d1",
    },
    "no_debt_before_clock": {
        "csv": "8deabd254484deef61b797021267322de964ef9bbe7a1bb91d8e9b02c207618e",
        "xlsx_members": "45ed078c8550040fb22c39107b97b40e426c8cf5b7e5cd23e54d5a88f79a6cb0",
        "parquet_rows": "c36b0de4947f5d5454e613c64901f4d1204f4c2e47bce27febdaac20c978e45a",
    },
}


def test_a38_x1p_pre_clock_exports_match_the_pre_marker_pins() -> None:
    """Before the clock every export is the pre-marker encoder's output."""
    digests = {
        name: _x1p_export_digests(matrix)
        for name, matrix in _x1p_pre_clock_matrices().items()
    }
    assert digests == _X1P_PRE_CLOCK_EXPORT_PINS


def test_a38_x1p_marker_changes_only_qualified_sums(monkeypatch) -> None:
    """Raw-byte proof: removing the marker changes nothing before the clock.

    The pre-marker encoder is the reason column spelled ``cell.reason``.
    Every pre-clock CSV, XLSX and Parquet payload is byte-identical under
    both encoders; the post-clock qualified-sum payloads must differ, or the
    marker is not reaching that format at all.
    """
    pre_clock = _x1p_pre_clock_matrices()
    qualified = _x1p_not_presented_matrices(_NP_AFTER)[0]
    with_marker = {name: _x1p_export_payloads(m) for name, m in pre_clock.items()}
    qualified_with_marker = _x1p_export_payloads(qualified)

    def pre_marker_reason(cell):
        return cell.reason

    monkeypatch.setattr(query_module, "_export_reason_text", pre_marker_reason)
    monkeypatch.setattr(query_snapshots_module, "_export_reason_text", pre_marker_reason)
    for name, matrix in pre_clock.items():
        assert _x1p_export_payloads(matrix) == with_marker[name], name
    without_marker = _x1p_export_payloads(qualified)
    for fmt in ("csv", "xlsx", "parquet"):
        assert without_marker[fmt] != qualified_with_marker[fmt], fmt


def test_a38_x1p_pre_clock_not_presented_pack_exports_equal_the_plain_engine() -> None:
    """Before the clock the not-presented pack adds no export byte at all."""
    policy = _policy(source=_NP_BEFORE, recorded=_NP_BEFORE)
    debt, no_debt = _x1p_not_presented_matrices(_NP_BEFORE)
    for matrix, values, metrics in (
        (debt, DEBT_FACTS, ["total_debt", "short_term_debt", "net_debt"]),
        (no_debt, NO_DEBT_FACTS, ["total_debt", "short_term_debt"]),
    ):
        plain = _engine(*_np_facts(values)).query_matrix(
            tickers=["AAA"], metrics=metrics, periods=[_NP_INSTANT], policy=policy
        )
        assert _x1p_export_payloads(matrix) == _x1p_export_payloads(plain)


def test_a54_reissue_after_a_new_generation_binds_the_new_receipt(
    router_app, monkeypatch
) -> None:
    """A re-issued export is bound to the generation latest at re-issue time.

    Export is stateless re-issue: nothing is cached between posts. The CSV and
    Parquet bodies carry cell bytes only, so the generation identity rides the
    receipt header, which is the hash of the JSON receipt that names it.
    """
    import dataclasses
    from datetime import timedelta

    from engine.fundamental_forensics import production_datasets as PDS
    from engine.fundamental_forensics.production_provider import (
        ProductionFinancialQueryProvider,
    )
    from tests.test_fundamental_forensics_production_provider import (
        T_ADMITTED,
        _fip1_material,
        _query_body,
    )

    store = PDS.InMemoryStrictConditionalStore()
    first = _fip1_material()
    PDS.publish_production_dataset(store, first)
    monkeypatch.setattr(
        forensics_api,
        "_financial_query_provider",
        lambda: ProductionFinancialQueryProvider(store),
    )
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {
        "id": "paid-user"
    }

    def issue(client):
        query = _post(client, _JSON_PATH, _query_body())
        assert query.status_code == 200
        receipt = query.headers["x-fif-response-sha256"]
        assert receipt == hashlib.sha256(query.content).hexdigest()
        generation = query.json()["delivery"]["dataset_generation_id"]
        exports = {}
        for path in _EXPORT_PATHS:
            response = _post(client, path, _query_body())
            assert response.status_code == 200
            assert response.headers["x-fif-receipt-sha256"] == receipt
            exports[path] = response
        return generation, receipt, exports

    with TestClient(router_app, raise_server_exceptions=False) as client:
        old_generation, old_receipt, old_exports = issue(client)
        assert old_generation == PDS.load_latest_generation(store, first.binding.entity_id).generation_id

        second = dataclasses.replace(
            first,
            admitted_at=T_ADMITTED + timedelta(days=2),
            source_recorded_at_floor=first.source_recorded_at_floor + timedelta(days=2),
        )
        PDS.publish_production_dataset(store, second)
        new_generation, new_receipt, new_exports = issue(client)

    assert new_generation == PDS.load_latest_generation(store, first.binding.entity_id).generation_id
    assert new_generation != old_generation
    assert new_receipt != old_receipt
    for path in _EXPORT_PATHS:
        assert new_exports[path].headers["x-fif-receipt-sha256"] == new_receipt
        assert old_exports[path].headers["x-fif-receipt-sha256"] == old_receipt
