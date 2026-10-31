"""FIF A0: production-mode statements/revisions serve a publisher-built store.

End-to-end chain tests over the REAL publisher path: the staging lane,
capture-members CLI and publish CLI are reused from the production publisher
test module (never a second staging path), the store is served through the
private API with ``FIF_FINANCIAL_DATASET_MODE=production`` and
``FIF_PRODUCTION_DATASET_LOCAL_STORE`` pointed at the built store, and the
responses are asserted on the HTTP boundary the site actually calls.

D-1 (statements): the published package manifest carried no ``entity_id``, so
``execute_financial_statements`` refused every production request with 503.
D-2 (revisions/packet): the production store keys filing metadata by
ACCESSION while the packet assembler looks occurrences up by OCCURRENCE ID,
so ``_assert_entity_isolation`` refused every production request with 503.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.forensics as forensics_api
import scripts.publish_fif_production_datasets as producer
import tests.test_fundamental_forensics_production_publisher as pub
from collectors.sec_request_pacer import SecRequestPacer
from engine.fundamental_forensics.query_service import CanonicalEntityBinding

ROOT = Path(__file__).resolve().parents[1]

_STATEMENTS_PATH = "/api/forensics/v1/financial/statements"
_REVISIONS_PATH = "/api/forensics/v1/financial/revisions"
_PACKET_PATH = "/api/forensics/v1/financial/packet"
_STATEMENT_SCHEMA = "fundamental_forensics.financial_statement_request/v1"
_REVISION_SCHEMA = "fundamental_forensics.financial_revision_request/v1"
_PACKET_SCHEMA = "fundamental_forensics.financial_packet_request/v1"

# FY2024 revenue duration as it exists in the staged AAPL ledger
# (us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax spans).
_REVENUE_PERIOD = {"kind": "duration", "start": "2023-10-01", "end": "2024-09-28", "label": "FY2024"}


@pytest.fixture()
def router_app(monkeypatch) -> FastAPI:
    monkeypatch.setattr(forensics_api, "REPO", ROOT)
    app = FastAPI()
    app.include_router(forensics_api.router)
    return app


@pytest.fixture(scope="session")
def production_lane(tmp_path_factory):
    """One publisher-built store for the whole module, via the REAL CLI path.

    Capture needs the offline collector patch; the publisher tests expose it
    as a function-scoped fixture, so the same two producer-module patches are
    applied here for the duration of the capture CLI call only (undone before
    publish, which reads retained bytes and needs no collector).
    """
    base = tmp_path_factory.mktemp("fif_a0_production_lane")
    lane = pub._materialize_lane(base)
    contract = pub._write_contract(base, lane["identity"], None)
    served = pub._served_members()

    def _pacer_factory(**kwargs):
        return SecRequestPacer(
            min_interval_seconds=kwargs.get("min_interval_seconds", 0.12),
            sleeper=lambda _seconds: None,
            monotonic=lambda: 0.0,
        )

    def _collector_factory(cache_root, **kwargs):
        return pub._FakeCollector(cache_root, served, kwargs["pacer"])

    mp = pytest.MonkeyPatch()
    mp.setattr(producer, "SecFilingArchiveCollector", _collector_factory)
    mp.setattr(producer, "SecRequestPacer", _pacer_factory)
    try:
        assert pub._capture_cli(lane, contract) == 0
    finally:
        mp.undo()
    store = base / "store"
    report = base / "report.json"
    assert pub._publish_cli(lane, contract, store, report) == 0
    return {"identity": lane["identity"], "store": store, "report": report, "base": base}


@pytest.fixture()
def production_client(router_app, monkeypatch, production_lane):
    """Private API client in production mode over the publisher-built store."""
    monkeypatch.setenv("FIF_FINANCIAL_DATASET_MODE", "production")
    monkeypatch.setenv("FIF_PRODUCTION_DATASET_LOCAL_STORE", str(production_lane["store"]))
    forensics_api._reset_production_provider_cache()
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {"id": "paid-user"}
    with TestClient(router_app, raise_server_exceptions=False) as client:
        yield client
    forensics_api._reset_production_provider_cache()


def _statements_body(identity: dict) -> bytes:
    return json.dumps(
        {
            "schema": _STATEMENT_SCHEMA,
            "entity_id": identity["entity_id"],
            "accession": identity["accessions"][0],
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _revisions_body(identity: dict) -> bytes:
    """The page's request shape: templates/fundamental_forensics.js
    ``revisionsRequestBody(latestBody)`` — the query body with the revision
    schema and ``selection: 'latest_known_as_of'``."""
    return json.dumps(
        {
            "schema": _REVISION_SCHEMA,
            "entity_id": identity["entity_id"],
            "policy": {
                "selection": "latest_known_as_of",
                "source_snapshot_at": "2025-12-31T23:59:59Z",
                "recorded_at": pub.RUN_CLOCK,
            },
            "metric_ids": ["revenue"],
            "periods": [dict(_REVENUE_PERIOD)],
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _packet_body(identity: dict) -> bytes:
    """The packet request over the SAME entity/policy/metric/period as
    ``_revisions_body`` (the packet API schema the packet endpoint tests
    use: ``fundamental_forensics.financial_packet_request/v1``)."""
    return json.dumps(
        {
            "schema": _PACKET_SCHEMA,
            "entity_id": identity["entity_id"],
            "policy": {
                "selection": "latest_known_as_of",
                "source_snapshot_at": "2025-12-31T23:59:59Z",
                "recorded_at": pub.RUN_CLOCK,
            },
            "metric_ids": ["revenue"],
            "periods": [dict(_REVENUE_PERIOD)],
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _resolved_revenue_fy2024_cell(packet: dict) -> dict:
    """The packet's selected/resolved revenue cell for the FY2024 duration.

    The packet's valued/unvalued discriminators are ``value`` (decimal text
    or null) and ``non_value_state`` (null iff the cell is valued; the
    unresolved states are ``missing``/``unsupported``) —
    ``financial_intelligence_packet._cell_states``. A null value or a
    non-null state fails the caller's assertion.
    """
    matches = [
        cell
        for cell in packet["cells"]
        if cell["metric_id"] == "revenue"
        and cell["period"]["label"] == _REVENUE_PERIOD["label"]
    ]
    assert len(matches) == 1, ("revenue FY2024 cell count", len(matches))
    cell = matches[0]
    assert cell["period"]["kind"] == _REVENUE_PERIOD["kind"]
    assert cell["period"]["start"] == _REVENUE_PERIOD["start"]
    assert cell["period"]["end"] == _REVENUE_PERIOD["end"]
    assert isinstance(cell["value"], str) and cell["value"], cell
    assert cell["non_value_state"] is None, cell
    return cell


# ---------------------------------------------------------------------------
# T1/T2: production mode serves the publisher-built store (D-1 + D-2)
# ---------------------------------------------------------------------------


def test_t1_production_statements_serve_columns_with_period_starts(
    production_client, production_lane
) -> None:
    identity = production_lane["identity"]
    response = production_client.post(
        _STATEMENTS_PATH,
        content=_statements_body(identity),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["entity"]["entity_id"] == identity["entity_id"]
    assert payload["entity"]["cik"] == identity["cik"]
    assert payload["filing"]["accession"] == identity["accessions"][0]
    statements = payload["statements"]
    assert len(statements) >= 1
    duration_columns = 0
    for statement in statements:
        for column in statement["columns"]:
            if column["kind"] == "duration":
                assert column["start"], f"duration column lost its period start: {column}"
                duration_columns += 1
    assert duration_columns >= 1


def test_t2_production_revisions_page_shape_returns_200(
    production_client, production_lane
) -> None:
    identity = production_lane["identity"]
    response = production_client.post(
        _REVISIONS_PATH,
        content=_revisions_body(identity),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["entity"]["entity_id"] == identity["entity_id"]
    assert payload["entity"]["cik"] == identity["cik"]
    assert isinstance(payload["revisions"], list)
    assert isinstance(payload["packet_ref"]["content_sha256"], str)
    # A0-h1 (MINOR-3): the envelope must ride the SAME frozen packet the
    # packet endpoint serves for the identical request. The publisher-built
    # corpus mints only FILED ledger events (ixbrl_raw_ledger), so its
    # revision rows are structurally empty and the page's revenue
    # resolution is pinned through that shared packet (see T2b), never
    # through a stale or divergent envelope.
    packet_response = production_client.post(
        _PACKET_PATH,
        content=_packet_body(identity),
        headers={"content-type": "application/json"},
    )
    assert packet_response.status_code == 200, packet_response.text
    assert (
        payload["packet_ref"]["content_sha256"]
        == packet_response.json()["content_sha256"]
    )


def test_t2b_production_packet_returns_200_with_resolved_revenue(
    production_client, production_lane
) -> None:
    """A0-h1 (MINOR-3): the production packet endpoint serves the frozen
    assembler's canonical bytes with a RESOLVED revenue FY2024 cell — the
    packet_service execute path (occurrence-keyed metadata normalization
    included) proven on the publisher-built production store."""
    identity = production_lane["identity"]
    response = production_client.post(
        _PACKET_PATH,
        content=_packet_body(identity),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 200, response.text
    packet = response.json()
    assert packet["schema"] == "financial_intelligence_packet.v1"
    assert packet["entity"]["entity_id"] == identity["entity_id"]
    assert packet["entity"]["cik"] == identity["cik"]
    _resolved_revenue_fy2024_cell(packet)
    # The endpoint exposes the HTTP-bytes digest (X-FIF-Response-SHA256):
    # pin the served bytes to it.
    assert (
        response.headers["x-fif-response-sha256"]
        == hashlib.sha256(response.content).hexdigest()
    )


# ---------------------------------------------------------------------------
# T3: the publisher refuses packages whose CIK/entity disagree with the
# issuer binding (R-1 guard rails around the entity_id injection)
# ---------------------------------------------------------------------------


def _foreign_cik(cik: str) -> str:
    return cik[:-1] + str((int(cik[-1]) + 1) % 10)


def test_t3_publisher_refuses_package_whose_cik_differs_from_binding(
    tmp_path, monkeypatch
) -> None:
    """A mis-mastered issuer: the security-master binding claims a CIK the
    retained filings were NOT captured under. Admission of the digest-clean
    packages succeeds (their own identity is true); the publisher must refuse
    to bind them to the wrong issuer and exclude the issuer with the typed
    ``admission_refused:issuer_cik_mismatch`` row, leaving no store object."""
    lane = pub._materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = pub._write_contract(tmp_path, identity, None)
    assert pub._capture_cli(lane, contract) == 0

    real_binding = producer._issuer_binding

    def _cross_claimed_binding(issuer):
        binding = real_binding(issuer)
        if binding is not None and str(issuer["cik"]) == identity["cik"]:
            foreign = _foreign_cik(identity["cik"])
            return CanonicalEntityBinding(
                entity_id=binding.entity_id,
                cik=foreign,
                ticker=binding.ticker,
                source_entity_id=foreign,
            )
        return binding

    monkeypatch.setattr(producer, "_issuer_binding", _cross_claimed_binding)
    store = tmp_path / "store"
    report_path = tmp_path / "report.json"
    assert pub._publish_cli(lane, contract, store, report_path) == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["published"] == []
    assert [row["reason"] for row in report["excluded"]] == [
        "admission_refused:issuer_cik_mismatch"
    ]
    assert not pub._latest_json_path(store, identity["entity_id"]).exists()
    # nothing at all was written for the refused issuer
    assert not list(store.rglob(f"*{identity['entity_id']}*")) if store.exists() else True


def test_t3b_publisher_refuses_package_with_foreign_entity_id(tmp_path, monkeypatch) -> None:
    """A retained manifest that already carries an ``entity_id`` belonging to
    a DIFFERENT issuer is refused (``admission_refused:issuer_entity_mismatch``)
    and never overwritten by the binding's entity."""
    lane = pub._materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = pub._write_contract(tmp_path, identity, None)
    assert pub._capture_cli(lane, contract) == 0

    real_read = producer.read_retained_fif_packages

    def _entity_claimed_read(archive_root, *, cik, accessions):
        packages = real_read(archive_root, cik=cik, accessions=accessions)
        return tuple(
            type(package)(
                cik=package.cik,
                accession=package.accession,
                manifest={**package.manifest, "entity_id": identity["entity_id"] + "-FOREIGN"},
                index_bytes=package.index_bytes,
                members=package.members,
                witness_bytes=package.witness_bytes,
                package_dir=package.package_dir,
            )
            for package in packages
        )

    monkeypatch.setattr(producer, "read_retained_fif_packages", _entity_claimed_read)
    store = tmp_path / "store"
    report_path = tmp_path / "report.json"
    assert pub._publish_cli(lane, contract, store, report_path) == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["published"] == []
    assert [row["reason"] for row in report["excluded"]] == [
        "admission_refused:issuer_entity_mismatch"
    ]
    assert not pub._latest_json_path(store, identity["entity_id"]).exists()


@pytest.mark.parametrize(
    "present_bad_entity_id",
    ["", 123, None, ["x"], {"x": 1}],
    ids=["empty-string", "int", "none", "list", "dict"],
)
def test_t3c_publisher_refuses_package_with_present_non_matching_entity_id(
    tmp_path, monkeypatch, present_bad_entity_id
) -> None:
    """A0-h1 (MINOR-1): a retained manifest whose ``entity_id`` key is
    PRESENT but is not exactly the binding's entity string — an empty
    string, a non-string, or None — is a DISAGREEING package
    (``admission_refused:issuer_entity_mismatch``), never one to silently
    relabel with the binding's entity."""
    lane = pub._materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = pub._write_contract(tmp_path, identity, None)
    assert pub._capture_cli(lane, contract) == 0

    real_read = producer.read_retained_fif_packages

    def _entity_claimed_read(archive_root, *, cik, accessions):
        packages = real_read(archive_root, cik=cik, accessions=accessions)
        return tuple(
            type(package)(
                cik=package.cik,
                accession=package.accession,
                manifest={**package.manifest, "entity_id": present_bad_entity_id},
                index_bytes=package.index_bytes,
                members=package.members,
                witness_bytes=package.witness_bytes,
                package_dir=package.package_dir,
            )
            for package in packages
        )

    monkeypatch.setattr(producer, "read_retained_fif_packages", _entity_claimed_read)
    store = tmp_path / "store"
    report_path = tmp_path / "report.json"
    assert pub._publish_cli(lane, contract, store, report_path) == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["published"] == []
    assert [row["reason"] for row in report["excluded"]] == [
        "admission_refused:issuer_entity_mismatch"
    ]
    assert not pub._latest_json_path(store, identity["entity_id"]).exists()
    # nothing at all was written for the refused issuer
    assert not list(store.rglob(f"*{identity['entity_id']}*")) if store.exists() else True


def test_t3d_publisher_accepts_package_with_present_equal_entity_id(
    tmp_path, monkeypatch
) -> None:
    """A0-h1 (review F3): a retained manifest whose ``entity_id`` is PRESENT
    and exactly the binding's entity string is a matching package — it is
    published, and the publisher does not rewrite its manifest (the stamp
    is only for an ABSENT key)."""
    lane = pub._materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = pub._write_contract(tmp_path, identity, None)
    assert pub._capture_cli(lane, contract) == 0

    real_read = producer.read_retained_fif_packages

    def _entity_claimed_read(archive_root, *, cik, accessions):
        packages = real_read(archive_root, cik=cik, accessions=accessions)
        return tuple(
            type(package)(
                cik=package.cik,
                accession=package.accession,
                manifest={**package.manifest, "entity_id": identity["entity_id"]},
                index_bytes=package.index_bytes,
                members=package.members,
                witness_bytes=package.witness_bytes,
                package_dir=package.package_dir,
            )
            for package in packages
        )

    real_replace = producer.replace
    manifest_rewrites: list[object] = []

    def _spy_replace(obj, /, **changes):
        if "manifest" in changes:
            manifest_rewrites.append(obj)
        return real_replace(obj, **changes)

    monkeypatch.setattr(producer, "read_retained_fif_packages", _entity_claimed_read)
    monkeypatch.setattr(producer, "replace", _spy_replace)
    store = tmp_path / "store"
    report_path = tmp_path / "report.json"
    assert pub._publish_cli(lane, contract, store, report_path) == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert [row["ticker"] for row in report["published"]] == [identity["ticker"]]
    assert report["excluded"] == []
    assert pub._latest_json_path(store, identity["entity_id"]).exists()
    assert manifest_rewrites == []


# ---------------------------------------------------------------------------
# T4: occurrence-keyed filing metadata helper (R-2) — unit semantics
# ---------------------------------------------------------------------------


class _FakeSource:
    def __init__(self, accession: str) -> None:
        self.accession = accession


class _FakeEvent:
    def __init__(self, occurrence_id: str, accession: str) -> None:
        self.occurrence_id = occurrence_id
        self.source = _FakeSource(accession)


class _FakeLedger:
    def __init__(self, events) -> None:
        self.events = tuple(events)


_T4_LEDGER = _FakeLedger(
    [
        _FakeEvent("occ-1", "0000000001-26-000001"),
        _FakeEvent("occ-2", "0000000001-26-000001"),
        _FakeEvent("occ-3", "0000000001-26-000002"),
    ]
)


def _t4_helper():
    from engine.fundamental_forensics.revision_service import (
        occurrence_keyed_filing_metadata,
    )

    return occurrence_keyed_filing_metadata


def test_t4_occurrence_keyed_input_is_returned_unchanged() -> None:
    helper = _t4_helper()
    meta_one = {"accession": "0000000001-26-000001", "source_body_sha256": "a" * 64}
    meta_two = {"accession": "0000000001-26-000002", "source_body_sha256": "b" * 64}
    source = {"occ-1": meta_one, "occ-3": meta_two}
    result = helper(_T4_LEDGER, source)
    assert result == source
    assert result["occ-1"] is meta_one
    assert result["occ-3"] is meta_two


def test_t4_accession_keyed_input_fans_out_to_every_occurrence() -> None:
    helper = _t4_helper()
    meta_one = {"accession": "0000000001-26-000001", "source_body_sha256": "a" * 64}
    meta_two = {"accession": "0000000001-26-000002", "source_body_sha256": "b" * 64}
    result = helper(_T4_LEDGER, {"0000000001-26-000001": meta_one, "occ-3": meta_two})
    assert result == {
        "occ-1": meta_one,
        "occ-2": meta_one,
        "occ-3": meta_two,
    }
    assert result["occ-1"] is meta_one and result["occ-2"] is meta_one


def test_t4_conflicting_double_bind_raises() -> None:
    helper = _t4_helper()
    meta_one = {"accession": "0000000001-26-000001", "source_body_sha256": "a" * 64}
    other = {"accession": "0000000001-26-000001", "source_body_sha256": "c" * 64}
    # occ-1 is bound twice with DIFFERENT metadata: once directly, once via
    # its accession. Fail closed.
    with pytest.raises(ValueError, match="conflicting filing metadata"):
        helper(_T4_LEDGER, {"occ-1": meta_one, "0000000001-26-000001": other})


def test_t4_identical_double_bind_is_lawful() -> None:
    helper = _t4_helper()
    meta_one = {"accession": "0000000001-26-000001", "source_body_sha256": "a" * 64}
    result = helper(_T4_LEDGER, {"occ-1": meta_one, "0000000001-26-000001": dict(meta_one)})
    assert result["occ-1"] == meta_one
    assert result["occ-2"] == meta_one


def test_t4_unknown_key_raises() -> None:
    helper = _t4_helper()
    meta_one = {"accession": "0000000001-26-000009", "source_body_sha256": "a" * 64}
    with pytest.raises(ValueError, match="does not identify"):
        helper(_T4_LEDGER, {"0000000001-26-000009": meta_one})


# ---------------------------------------------------------------------------
# T5: golden mode is untouched — statements bytes stay at the pinned digest
# and the golden revisions boundary stays the typed 503
# ---------------------------------------------------------------------------


def test_t5_golden_mode_statements_bytes_stay_pinned(router_app, monkeypatch) -> None:
    security_master = ROOT / "data" / "reference" / "security_master.parquet"
    if not security_master.is_file():
        # SPARSE LAW: this lane tree deliberately has no data/ beyond
        # data/fundamental_forensics/; the golden statements path binds
        # through data/reference/security_master.parquet and is the typed
        # 503 here (statement_service._load_security_records). The pinned
        # byte assertion runs wherever the checkout is full (CI); the
        # before/after sha256 equality for THIS tree is receipted in the
        # A0 report via the stub-master drive.
        pytest.skip(
            "sparse tree: data/reference/security_master.parquet is absent — "
            "golden statements is the typed 503 here"
        )
    from tests.test_fundamental_forensics_financial_statement_api import (
        _RESPONSE_SHA as pinned,
    )
    import engine.fundamental_forensics.statement_service as statement_service
    from engine.fundamental_forensics.financial_intelligence_packet import load_core_registry

    monkeypatch.delenv("FIF_FINANCIAL_DATASET_MODE", raising=False)
    monkeypatch.delenv("FIF_PRODUCTION_DATASET_LOCAL_STORE", raising=False)
    forensics_api._reset_production_provider_cache()
    # Golden mode reconstructs through statement_service.load_core_registry(REPO).
    # This pin family runs on the committed byte-copy of the 1.0.0 registry
    # (pub.PINNED_REGISTRY_ROOT), so the pinned bytes re-derive unchanged; the
    # live-registry response bytes are pinned in
    # test_fundamental_forensics_financial_statement_api.py.
    monkeypatch.setattr(
        statement_service,
        "load_core_registry",
        lambda _repo_root: load_core_registry(pub.PINNED_REGISTRY_ROOT),
    )
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {"id": "paid-user"}
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = client.post(
            _STATEMENTS_PATH,
            content=json.dumps(
                {
                    "schema": _STATEMENT_SCHEMA,
                    "entity_id": "ISS:US-XNAS-AAPL",
                    "accession": "0000320193-25-000079",
                },
                separators=(",", ":"),
            ).encode("utf-8"),
            headers={"content-type": "application/json"},
        )
    assert response.status_code == 200
    import hashlib

    assert hashlib.sha256(response.content).hexdigest() == pinned


def test_t5_golden_mode_revisions_stay_the_typed_503(router_app, monkeypatch) -> None:
    monkeypatch.delenv("FIF_FINANCIAL_DATASET_MODE", raising=False)
    monkeypatch.delenv("FIF_PRODUCTION_DATASET_LOCAL_STORE", raising=False)
    forensics_api._reset_production_provider_cache()
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {"id": "paid-user"}
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = client.post(
            _REVISIONS_PATH,
            content=json.dumps(
                {
                    "schema": _REVISION_SCHEMA,
                    "entity_id": "ISS:US-XNAS-AAPL",
                    "policy": {
                        "selection": "latest_known_as_of",
                        "source_snapshot_at": "2025-12-31T23:59:59Z",
                        "recorded_at": "2026-08-05T12:00:02Z",
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
            ).encode("utf-8"),
            headers={"content-type": "application/json"},
        )
    assert response.status_code == 503
    assert response.json()["detail"] == "financial revisions temporarily unavailable"
