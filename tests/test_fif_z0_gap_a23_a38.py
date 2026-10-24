"""FIF Z0 closure-matrix gap tests: A23 and A38 on the production store.

Closes two PARTIAL rows of research/financial_intelligence_fabric/
FIF_Z0_CLOSURE_MATRIX.json over the code as it exists — tests only, no
production change:

- A23 ("different users or temporal query policies hit shared cache") beyond
  the two-users/one-generation case already proven by
  tests/test_fundamental_forensics_financial_query_api.py::
  test_two_users_two_policies_share_no_answer_object: here ONE process, ONE
  store and ONE provider carry TWO admitted generations (S1).
- A38 ("same query in Python / kernel / API / UI / CSV / Parquet / JSON")
  on a PRODUCTION generation, not the fixture provider already proven by
  tests/test_fundamental_forensics_query_exports.py::
  test_a38_decimal_parity_json_csv_parquet (S3/S4).

Helpers are imported from those two modules; they are not copied.
"""
from __future__ import annotations

import hashlib
import io
import json
import zipfile
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.forensics as forensics_api
from engine.fundamental_forensics.excel_export import to_xlsx_bytes
from tests.test_fundamental_forensics_financial_query_api import (
    _QUERY_PATH,
    _assert_private_headers,
    _p1_aapl_body,
    _p1_aapl_material,
)
from tests.test_fundamental_forensics_query_exports import (
    _CSV_PATH,
    _PARQUET_PATH,
    _SSML_NS,
    _XLSX_PATH,
    _csv_rows,
    _parquet_rows,
)

ROOT = Path(__file__).resolve().parents[1]

_ENTITY = "ISS:US-XNAS-AAPL"
_G1_ADMITTED = datetime(2026, 10, 1, tzinfo=timezone.utc)
_G2_ADMITTED = datetime(2026, 10, 10, tzinfo=timezone.utc)
# Fixed policy clocks only — never the wall clock.
_RECORDED_G1_WINDOW = "2026-10-05T00:00:00Z"  # at/after G1 admission, before G2's
_RECORDED_G2 = "2026-10-15T00:00:00Z"  # at/after G2 admission
_RECORDED_G2_ALT = "2026-10-16T00:00:00Z"  # second servable policy on G2


@pytest.fixture
def router_app(monkeypatch) -> FastAPI:
    monkeypatch.setattr(forensics_api, "REPO", ROOT)
    app = FastAPI()
    app.include_router(forensics_api.router)
    return app


@pytest.fixture(scope="module")
def aapl_material():
    """The production AAPL corpus material, built once for the whole module."""
    return _p1_aapl_material()


@pytest.fixture(scope="module")
def g1_publication(aapl_material):
    """One store carrying exactly G1 (the S3/S4 production generation)."""
    from engine.fundamental_forensics import production_datasets as PDS

    store = PDS.InMemoryStrictConditionalStore()
    publication = PDS.publish_production_dataset(store, aapl_material)
    return store, publication


def _post(client: TestClient, path: str, body: bytes):
    return client.post(path, content=body, headers={"content-type": "application/json"})


def _production_provider(router_app, monkeypatch, store):
    """Wire the ONE production provider singleton for this store (A23 shape)."""
    from engine.fundamental_forensics.production_provider import (
        ProductionFinancialQueryProvider,
    )

    provider = ProductionFinancialQueryProvider(store)
    monkeypatch.setenv("FIF_FINANCIAL_DATASET_MODE", "production")
    monkeypatch.setattr(forensics_api, "_production_query_provider", lambda: provider)
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {
        "id": "paid-user-a"
    }
    return provider


def _xlsx_rows(payload: bytes) -> list[dict[str, str]]:
    """Sheet1 rows of an export workbook, keyed by the header row (A1 form)."""
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    row_elements = root.findall(f"{{{_SSML_NS}}}sheetData/{{{_SSML_NS}}}row")
    header: list[str] = []
    records: list[dict[str, str]] = []
    for row_index, row_element in enumerate(row_elements):
        by_column: dict[int, str] = {}
        for cell in row_element.findall(f"{{{_SSML_NS}}}c"):
            ref = cell.get("r") or ""
            letters = ref[: len(ref) - len(ref.lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))]
            column = 0
            for character in letters:
                column = column * 26 + ord(character) - 64
            if cell.get("t") == "inlineStr":
                text = cell.findtext(f"{{{_SSML_NS}}}is/{{{_SSML_NS}}}t") or ""
            else:
                text = cell.findtext(f"{{{_SSML_NS}}}v") or ""
            by_column[column] = text
        width = max(by_column, default=0)
        cells = [by_column.get(index, "") for index in range(1, width + 1)]
        if row_index == 0:
            header = cells
            continue
        records.append(dict(zip(header, cells)))
    return records


def _kernel_matrix(store, publication, body):
    """The provider's own engine for G1: load the generation, rebuild the
    dataset exactly as ProductionFinancialQueryProvider.resolve does, then run
    BitemporalMetricQueryEngine exactly as execute_financial_query builds it
    (engine/fundamental_forensics/query_service.py:673-698)."""
    from engine.fundamental_forensics import production_datasets as PDS
    from engine.fundamental_forensics.issuer_sic import resolve_issuer_sic
    from engine.fundamental_forensics.query import (
        BitemporalMetricQueryEngine,
        QueryBounds,
        QueryEntity,
    )
    from engine.fundamental_forensics.query_service import (
        FinancialQueryDataset,
        admit_financial_request,
    )

    generation = PDS.load_generation(store, _ENTITY, publication.generation_id)
    payloads = PDS.load_query_dataset_payloads(generation)
    binding = generation.binding
    dataset = FinancialQueryDataset(
        binding=binding,
        ledger=payloads["ledger"],
        filing_metadata=payloads["filing_metadata"],
        registry=payloads["registry"],
        delivery=generation.delivery(),
        lineage_evidence=payloads["lineage_evidence"],
        dataset_admitted_at=generation.admitted_at,
    )
    admitted = admit_financial_request(body)
    engine = BitemporalMetricQueryEngine(
        ledger=dataset.ledger,
        registry=dataset.registry,
        entities=[
            QueryEntity(
                ticker=binding.ticker,
                entity_id=binding.source_entity_id,
                issuer_sic=resolve_issuer_sic(binding.source_entity_id),
            )
        ],
        filing_metadata=dataset.filing_metadata,
        # The transport's own synchronous bounds (query_service.py:46-48).
        bounds=QueryBounds(max_tickers=1, max_metrics=50, max_periods=8, max_cells=400),
        lineage_evidence=dataset.lineage_evidence,
    )
    return engine.query_matrix(
        tickers=[binding.ticker],
        metrics=admitted.metric_ids,
        periods=admitted.periods,
        policy=admitted.policy,
    )


# ---------------------------------------------------------------------------
# S1 — A23: two generations, one store, one provider, one process.
# ---------------------------------------------------------------------------


def test_a23_two_generations_one_store_one_provider(router_app, monkeypatch, aapl_material) -> None:
    """FIF Z0 closure matrix case A23: different temporal query policies
    against a shared store that carries two admitted generations never share
    an answer object — per-generation receipts, byte-identical repeats, and
    private/no-store on every answer."""
    from engine.fundamental_forensics import production_datasets as PDS

    store = PDS.InMemoryStrictConditionalStore()
    g1 = PDS.publish_production_dataset(store, aapl_material)
    assert g1.admitted_at.startswith("2026-10-01")
    _production_provider(router_app, monkeypatch, store)

    # -- S1a (first half): while G1 is the latest generation, a recorded_at
    #    inside G1's window is served from G1's bytes.
    with TestClient(router_app, raise_server_exceptions=False) as client:
        r1 = _post(client, _QUERY_PATH, _p1_aapl_body(_QUERY_PATH, recorded_at=_RECORDED_G1_WINDOW))
        assert r1.status_code == 200
        envelope1 = r1.json()
        assert envelope1["delivery"]["dataset_generation_id"] == g1.generation_id
        # -- S1d: private, no-store on the answer itself.
        _assert_private_headers(r1)
        assert r1.headers["cache-control"] == "private, no-store"

        # -- S1b/S1c (repeat + no shared mutable object): the same policy
        #    re-answers byte-identically, even after a caller mutates its own
        #    parsed copy of the receipt.
        repeat1 = _post(client, _QUERY_PATH, _p1_aapl_body(_QUERY_PATH, recorded_at=_RECORDED_G1_WINDOW))
        assert repeat1.content == r1.content
        mutated = json.loads(r1.content)
        mutated["receipt"]["nodes"][0]["value"] = "999999999"
        after_mutation = _post(client, _QUERY_PATH, _p1_aapl_body(_QUERY_PATH, recorded_at=_RECORDED_G1_WINDOW))
        assert after_mutation.content == r1.content

        # Publish G2 into the SAME store: same corpus, later admission clock.
        g2 = PDS.publish_production_dataset(
            store, replace(aapl_material, admitted_at=_G2_ADMITTED)
        )
        assert g2.generation_id != g1.generation_id

        # -- S1a (second half): a recorded_at at/after G2's admission carries
        #    G2's generation id; a recorded_at between the two admissions is
        #    NOT answered from G1 — the provider resolves the latest pointer
        #    only (production_provider.py:84 load_latest_generation) and the
        #    transport applies the dataset admission floor
        #    (query_service.py:265 recorded < admitted_at), so the G1-window
        #    policy now fails closed as a private 503 (see DEVIATIONS).
        r2a = _post(client, _QUERY_PATH, _p1_aapl_body(_QUERY_PATH, recorded_at=_RECORDED_G2))
        assert r2a.status_code == 200
        envelope2a = r2a.json()
        assert envelope2a["delivery"]["dataset_generation_id"] == g2.generation_id
        _assert_private_headers(r2a)
        assert r2a.headers["cache-control"] == "private, no-store"

        r_mid = _post(client, _QUERY_PATH, _p1_aapl_body(_QUERY_PATH, recorded_at=_RECORDED_G1_WINDOW))
        assert r_mid.status_code == 503
        _assert_private_headers(r_mid)
        assert r_mid.json()["detail"] == "financial query temporarily unavailable"

        # A second user, a second servable policy: distinct body, same G2.
        router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda u="paid-user-b": {
            "id": u
        }
        r2b = _post(client, _QUERY_PATH, _p1_aapl_body(_QUERY_PATH, recorded_at=_RECORDED_G2_ALT))
        assert r2b.status_code == 200
        envelope2b = r2b.json()
        assert envelope2b["delivery"]["dataset_generation_id"] == g2.generation_id
        _assert_private_headers(r2b)

        # -- S1b: the two response bodies differ and each repeat is
        #    byte-identical.
        assert r2a.content != r2b.content
        assert r2a.content != r1.content
        router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {
            "id": "paid-user-a"
        }
        repeat2a = _post(client, _QUERY_PATH, _p1_aapl_body(_QUERY_PATH, recorded_at=_RECORDED_G2))
        assert repeat2a.content == r2a.content
        router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda u="paid-user-b": {
            "id": u
        }
        repeat2b = _post(client, _QUERY_PATH, _p1_aapl_body(_QUERY_PATH, recorded_at=_RECORDED_G2_ALT))
        assert repeat2b.content == r2b.content

    # -- S1c: the two parsed receipts are distinct objects with distinct
    #    generation ids and distinct receipt digests.
    receipt1 = envelope1["receipt"]
    receipt2 = envelope2a["receipt"]
    assert receipt1 is not receipt2
    assert receipt1["query_hash"] != receipt2["query_hash"]
    assert envelope1["delivery"]["dataset_generation_id"] != envelope2a["delivery"][
        "dataset_generation_id"
    ]
    assert r1.headers["x-fif-response-sha256"] != r2a.headers["x-fif-response-sha256"]

    # The health surface names the same store's latest generation: the
    # x-fif-dataset-generation-id header (app/forensics.py:336) reports G2,
    # agreeing with every query receipt above.
    import engine.fundamental_forensics.production_datasets as pds_module

    monkeypatch.setattr(pds_module, "build_production_dataset_store", lambda *_, **__: store)
    with TestClient(router_app, raise_server_exceptions=False) as client:
        health = client.get("/api/forensics/health")
    assert health.status_code == 200
    assert health.headers["x-fif-dataset-generation-id"] == g2.generation_id
    assert health.headers["x-fif-dataset-admitted-at"] == g2.admitted_at


# ---------------------------------------------------------------------------
# S3 — A38: one query through kernel, JSON, CSV, Parquet, XLSX and the page
# drawer fields, on ONE production generation.
# ---------------------------------------------------------------------------


def _collect_legs(router_app, monkeypatch, store, publication) -> dict:
    """Issue the ONE query through every HTTP leg and the kernel leg."""
    body = _p1_aapl_body(_QUERY_PATH, recorded_at=_RECORDED_G1_WINDOW)
    _production_provider(router_app, monkeypatch, store)
    legs: dict = {"body": body}
    with TestClient(router_app, raise_server_exceptions=False) as client:
        for name, path in (
            ("json", _QUERY_PATH),
            ("csv", _CSV_PATH),
            ("parquet", _PARQUET_PATH),
            ("xlsx", _XLSX_PATH),
        ):
            legs[name] = _post(client, path, body)
    legs["matrix"] = _kernel_matrix(store, publication, body)
    return legs


def test_a38_one_query_every_leg_on_one_production_generation(
    router_app, monkeypatch, g1_publication
) -> None:
    """FIF Z0 closure matrix case A38: the SAME query on a production
    generation answers identically through the kernel, the API JSON route,
    CSV, Parquet, XLSX, and the page drawer fields — Decimal-exact per root
    cell, one query_hash, one receipt digest on every leg."""
    store, publication = g1_publication
    legs = _collect_legs(router_app, monkeypatch, store, publication)
    json_response = legs["json"]

    for name in ("json", "csv", "parquet", "xlsx"):
        response = legs[name]
        assert response.status_code == 200, (name, response.text[:200])
        _assert_private_headers(response)
        assert response.headers["cache-control"] == "private, no-store"

    envelope = json_response.json()
    receipt = envelope["receipt"]
    query_hash = receipt["query_hash"]

    # Kernel leg: the provider's own engine reproduces the receipt exactly —
    # cell ids, values, policy, query_hash.
    matrix = legs["matrix"]
    assert matrix.to_dict() == receipt
    kernel_nodes = {node["cell_id"]: node for node in matrix.to_dict()["nodes"]}

    # Generation id: the JSON receipt names G1, and every export leg carries
    # the JSON route's response digest as its receipt digest, binding it to
    # the same G1 receipt.
    assert envelope["delivery"]["dataset_generation_id"] == publication.generation_id
    json_digest = json_response.headers["x-fif-response-sha256"]
    assert json_digest == hashlib.sha256(json_response.content).hexdigest()
    for name in ("csv", "parquet", "xlsx"):
        assert legs[name].headers["x-fif-receipt-sha256"] == json_digest

    # Root-cell parity across every leg.
    csv_by_id = {row["root_cell_id"]: row for row in _csv_rows(legs["csv"].content)}
    parquet_by_id = {row["root_cell_id"]: row for row in _parquet_rows(legs["parquet"].content)}
    xlsx_by_id = {row["root_cell_id"]: row for row in _xlsx_rows(legs["xlsx"].content)}
    json_nodes = {node["cell_id"]: node for node in receipt["nodes"]}
    assert set(receipt["root_cell_ids"]) == set(csv_by_id) == set(parquet_by_id) == set(xlsx_by_id)
    for cell_id in receipt["root_cell_ids"]:
        json_value = json_nodes[cell_id]["value"]
        kernel_value = kernel_nodes[cell_id]["value"]
        csv_value = csv_by_id[cell_id]["value"]
        parquet_value = parquet_by_id[cell_id]["value"]
        xlsx_value = xlsx_by_id[cell_id]["value"]
        assert kernel_value == json_value
        if json_value is None:
            assert csv_value == ""
            assert parquet_value is None
            assert xlsx_value == ""
        else:
            assert Decimal(json_value) == Decimal(csv_value)
            assert Decimal(json_value) == Decimal(parquet_value)
            assert Decimal(json_value) == Decimal(xlsx_value)
        assert csv_by_id[cell_id]["query_hash"] == query_hash
        assert parquet_by_id[cell_id]["query_hash"] == query_hash
        assert xlsx_by_id[cell_id]["query_hash"] == query_hash

    # Page drawer leg: the source desk fetches the SAME JSON route
    # (templates/fundamental_forensics.js:12, POSTed at :2212-2214), verifies
    # X-FIF-Response-SHA256 against the raw body (:2044) before parsing, and
    # reads exactly these receipt fields: receipt.nodes[].cell_id/.value
    # (:2091, :1662), receipt.policy (:2225) and delivery.dataset_generation_id
    # (:2230). Assert those fields carry the kernel's answers.
    drawer_nodes = [node for node in receipt["nodes"] if isinstance(node, dict)]
    assert drawer_nodes, "the page drawer reads receipt.nodes; it must be non-empty"
    for node in drawer_nodes:
        assert node["cell_id"] in kernel_nodes
        assert node["value"] == kernel_nodes[node["cell_id"]]["value"]
    assert receipt["policy"]["recorded_at"] == matrix.to_dict()["policy"]["recorded_at"]
    assert str(envelope["delivery"]["dataset_generation_id"] or "") == publication.generation_id


# ---------------------------------------------------------------------------
# S4 — determinism: the full S3 leg set re-run is byte-identical.
# ---------------------------------------------------------------------------


def test_a38_s4_full_leg_rerun_is_byte_identical(router_app, monkeypatch, g1_publication) -> None:
    """FIF Z0 closure matrix case A38 (determinism): re-issuing the S3 query
    through every leg reproduces every byte-level artifact exactly."""
    store, publication = g1_publication
    first = _collect_legs(router_app, monkeypatch, store, publication)
    second = _collect_legs(router_app, monkeypatch, store, publication)

    for name in ("json", "csv", "parquet", "xlsx"):
        assert first[name].content == second[name].content, name
        assert first[name].headers["x-fif-response-sha256"] == second[name].headers[
            "x-fif-response-sha256"
        ]
    for name in ("csv", "parquet", "xlsx"):  # receipt digest is an export header
        assert first[name].headers["x-fif-receipt-sha256"] == second[name].headers[
            "x-fif-receipt-sha256"
        ]
    assert first["matrix"].to_json_bytes() == second["matrix"].to_json_bytes()

    # The XLSX encoder over the JSON envelope reproduces the route's workbook
    # bytes (the leg the page exports, fundamental_forensics.js:15/:3379).
    envelope = dict(first["json"].json())
    envelope["sha256"] = first["json"].headers["x-fif-response-sha256"]
    assert to_xlsx_bytes(envelope) == first["xlsx"].content
