"""FIF V0-a: no forensics route reaches SEC or R2 while it serves.

A46 acceptance: measured latency SLOs with NO request-time SEC. The five
production-backed routes (health, financial/query, financial/packet,
financial/statements, financial/revisions) are served in-process over a
publisher-built local store — the fixture pattern of
tests/test_fundamental_forensics_production_api_chain.py, copied here in
minimal form rather than imported — while ``socket.socket.connect``,
``socket.socket.connect_ex`` and ``socket.create_connection`` raise
AssertionError("network"). No SEC/R2 reach exists under a local store: every
call must complete with its normal status and the patched constructors must
never run.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import socket
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.forensics as forensics_api
import scripts.publish_fif_production_datasets as producer
from collectors.sec_document_spine import (
    ArchiveResponseTooLarge,
    persist_archive_document,
    retain_filing_manifest,
    with_document_retrievals,
)
from collectors.sec_request_pacer import SecRequestPacer
from engine.fundamental_forensics.sec_document_spine import build_filing_manifests
from engine.fundamental_forensics.statement_graph import GOLDEN_AAPL_FIXTURES

ROOT = Path(__file__).resolve().parents[1]
# Seat ruling R-9761-CLK (b): this is a publisher-family run (the store below is
# built through the REAL publish CLI at a fixed 2026-10-13 clock), so it reads
# the byte-identical 1.0.0 registry copy as --repo-root, exactly like
# test_fundamental_forensics_production_publisher.py. The publisher's CLOCK RULE
# folds every registry available_at into admitted_at; the live registry's later
# rule clocks (2026-10-21) would refuse this fixture run with
# admitted_at_after_recorded_at. The lane under test is request-time network
# reach, not registry content.
PINNED_REGISTRY_ROOT = ROOT / "tests" / "fixtures" / "fundamental_forensics_registry_v1_0_0"

# ---------------------------------------------------------------------------
# Minimal copy of the production-lane fixture pattern (identity derived at
# runtime from the committed fixture bytes; no ticker or CIK literal here).
# ---------------------------------------------------------------------------

FIRST_ACCEPTED_AT = "2025-10-31T10:01:26.000Z"
SECOND_ACCEPTED_AT = "2024-07-31T10:01:26.000Z"
CAPTURE_CLOCK = "2026-10-13T02:31:00Z"
RUN_CLOCK = "2026-10-13T02:35:00Z"
USER_AGENT = "MastermindX FIF V0-a latency lane test bench test@example.invalid"

_STATEMENT_SCHEMA = "fundamental_forensics.financial_statement_request/v1"
_REVISION_SCHEMA = "fundamental_forensics.financial_revision_request/v1"
_PACKET_SCHEMA = "fundamental_forensics.financial_packet_request/v1"
_QUERY_SCHEMA = "fundamental_forensics.financial_query_request/v1"
_REVENUE_PERIOD = {"kind": "duration", "start": "2023-10-01", "end": "2024-09-28", "label": "FY2024"}


def _fixture_identity() -> dict:
    accessions = sorted(GOLDEN_AAPL_FIXTURES)
    manifests = {}
    for accession in accessions:
        fixture = ROOT / GOLDEN_AAPL_FIXTURES[accession]
        manifests[accession] = json.loads(
            (fixture / "package_manifest.json").read_text(encoding="utf-8")
        )
    first = manifests[accessions[0]]
    listing_key = str(first["listing_key"])
    return {
        "cik": str(first["cik"]),
        "ticker": listing_key.rsplit("-", 1)[-1],
        "entity_id": str(first["entity_id"]),
        "security_id": str(first["security_id"]),
        "listing_key": listing_key,
        "accessions": accessions,
        "manifests": manifests,
    }


def _row_value(identity: dict, accession: str, field: str) -> str:
    manifest = identity["manifests"][accession]
    value = str(manifest[field])
    if accession != identity["accessions"][0] and field in (
        "period_of_report",
        "filing_date",
    ):
        value = value.replace("2026-", "2024-")
    return value


def _synthetic_submissions(identity: dict) -> dict:
    recent = {
        "accessionNumber": list(identity["accessions"]),
        "form": [str(identity["manifests"][a]["form"]) for a in identity["accessions"]],
        "filingDate": [_row_value(identity, a, "filing_date") for a in identity["accessions"]],
        "reportDate": [_row_value(identity, a, "period_of_report") for a in identity["accessions"]],
        "acceptanceDateTime": [
            FIRST_ACCEPTED_AT if a == identity["accessions"][0] else SECOND_ACCEPTED_AT
            for a in identity["accessions"]
        ],
        "primaryDocument": [
            str(identity["manifests"][a]["primary_document"]) for a in identity["accessions"]
        ],
        "isXBRL": [True] * len(identity["accessions"]),
        "isInlineXBRL": [True] * len(identity["accessions"]),
    }
    return {
        "cik": int(identity["cik"]),
        "name": "Synthetic Lane Issuer",
        "filings": {"recent": recent},
    }


def _write_submissions(raw_root: Path, identity: dict) -> None:
    cik = identity["cik"]
    payload = json.dumps(_synthetic_submissions(identity)).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    object_path = f"{cik}/submissions/{digest[:32]}.json.gz"
    target = raw_root / object_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(gzip.compress(payload))
    latest = raw_root / cik / "submissions" / "latest.json"
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(
        json.dumps(
            {
                "schema": "fundamental_forensics_retrieval.v1",
                "cik": cik,
                "endpoint": "submissions",
                "url": f"https://data.sec.gov/submissions/CIK{cik}.json",
                "retrieved_at": CAPTURE_CLOCK,
                "sha256": digest,
                "bytes": len(payload),
                "object_path": object_path,
                "http_etag": None,
                "http_last_modified": None,
            }
        ),
        encoding="utf-8",
    )


def _retain_primaries(archive_root: Path, identity: dict) -> None:
    manifests = build_filing_manifests(
        _synthetic_submissions(identity),
        cik=identity["cik"],
        ticker=identity["ticker"],
        recorded_at=CAPTURE_CLOCK,
    )
    by_accession = {m["filing"]["accession"]: m for m in manifests}
    for accession in identity["accessions"]:
        manifest = by_accession[accession]
        primary = next(
            item for item in manifest["documents"] if item["role"] == "primary"
        )
        fixture = ROOT / GOLDEN_AAPL_FIXTURES[accession]
        primary_bytes = (fixture / "members" / primary["document_name"]).read_bytes()
        receipt = persist_archive_document(
            archive_root, primary, primary_bytes, retrieved_at=CAPTURE_CLOCK
        )
        materialized = with_document_retrievals(
            manifest, {str(primary["document_id"]): receipt.to_dict()}
        )
        retain_filing_manifest(archive_root, materialized)


def _served_members() -> dict[str, dict[str, bytes]]:
    served: dict[str, dict[str, bytes]] = {}
    for accession, relative in sorted(GOLDEN_AAPL_FIXTURES.items()):
        fixture = ROOT / relative
        members = {"index.json": (fixture / "index.json").read_bytes()}
        for path in sorted((fixture / "members").iterdir()):
            members[path.name] = path.read_bytes()
        served[accession.replace("-", "")] = members
    return served


class _FakeCollector:
    """Offline SEC stand-in: persists served bytes, paces on the shared pacer."""

    def __init__(self, cache_root: Path, served: dict[str, dict[str, bytes]], pacer) -> None:
        self.cache_root = Path(cache_root)
        self._served = served
        self._pacer = pacer

    def fetch_document(self, document, *, retrieved_at=None, expected_sha256=None, max_document_bytes=None):
        self._pacer.acquire()
        url = document["archive_url"]
        accession = url.rsplit("/", 2)[-2].replace("-", "")
        name = url.rsplit("/", 1)[-1]
        payload = self._served[accession][name]
        if max_document_bytes is not None and len(payload) > max_document_bytes:
            raise ArchiveResponseTooLarge(
                f"forced streamed cap: {name} ({len(payload)} > {max_document_bytes})"
            )
        return persist_archive_document(
            self.cache_root,
            document,
            payload,
            retrieved_at=retrieved_at,
        )

    def fetch_primary_document(self, manifest, *, retrieved_at=None, expected_sha256=None, max_document_bytes=None):
        primary = next(
            item for item in manifest["documents"] if item["role"] == "primary"
        )
        receipt = self.fetch_document(
            primary,
            retrieved_at=retrieved_at,
            expected_sha256=expected_sha256,
            max_document_bytes=max_document_bytes,
        )
        result = receipt.to_dict() if hasattr(receipt, "to_dict") else dict(receipt)
        return with_document_retrievals(manifest, {str(primary["document_id"]): result})


def _write_contract(tmp_path: Path, identity: dict) -> Path:
    path = tmp_path / "contract.json"
    path.write_text(
        json.dumps(
            {
                "schema": "fundamental_forensics.coverage_contract/v1",
                "contract_id": "synthetic-fif-v0a-latency",
                "issuers": [
                    {
                        "cik": identity["cik"],
                        "ticker": identity["ticker"],
                        "legal_name": "Synthetic Lane Issuer",
                        "security_master_binding": {
                            "issuer_id": identity["entity_id"],
                            "issuer_cik": identity["cik"],
                            "security_id": identity["security_id"],
                            "listing_key": identity["listing_key"],
                            "mic": "XNAS",
                            "effective_at": "2023-05-09T00:00:00",
                        },
                        "accessions": [
                            {
                                "accession": a,
                                "form": str(identity["manifests"][a]["form"]),
                                "filing_date": _row_value(identity, a, "filing_date"),
                            }
                            for a in identity["accessions"]
                        ],
                    }
                ],
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    return path


def _materialize_lane(tmp_path: Path) -> dict:
    identity = _fixture_identity()
    raw_root = tmp_path / "raw"
    archive_root = tmp_path / "archive"
    raw_root.mkdir(parents=True)
    archive_root.mkdir(parents=True)
    _write_submissions(raw_root, identity)
    _retain_primaries(archive_root, identity)
    return {"identity": identity, "raw_root": raw_root, "archive_root": archive_root}


def _capture_cli(lane: dict, contract: Path) -> int:
    return producer.main(
        [
            "capture-members",
            "--coverage-file", str(contract),
            "--raw-root", str(lane["raw_root"]),
            "--archive-root", str(lane["archive_root"]),
            "--recorded-at", CAPTURE_CLOCK,
            "--user-agent", USER_AGENT,
        ]
    )


def _publish_cli(lane: dict, contract: Path, store: Path, report: Path) -> int:
    return producer.main(
        [
            "publish",
            "--coverage-file", str(contract),
            "--raw-root", str(lane["raw_root"]),
            "--archive-root", str(lane["archive_root"]),
            "--recorded-at", RUN_CLOCK,
            "--store-dir", str(store),
            "--repo-root", str(PINNED_REGISTRY_ROOT),
            "--report-path", str(report),
        ]
    )


@pytest.fixture(scope="session")
def production_lane(tmp_path_factory):
    """One publisher-built store for the module, via the REAL CLI path."""
    base = tmp_path_factory.mktemp("fif_v0a_no_sec_lane")
    lane = _materialize_lane(base)
    contract = _write_contract(base, lane["identity"])
    served = _served_members()

    def _pacer_factory(**kwargs):
        return SecRequestPacer(
            min_interval_seconds=kwargs.get("min_interval_seconds", 0.12),
            sleeper=lambda _seconds: None,
            monotonic=lambda: 0.0,
        )

    def _collector_factory(cache_root, **kwargs):
        return _FakeCollector(cache_root, served, kwargs["pacer"])

    mp = pytest.MonkeyPatch()
    mp.setattr(producer, "SecFilingArchiveCollector", _collector_factory)
    mp.setattr(producer, "SecRequestPacer", _pacer_factory)
    try:
        assert _capture_cli(lane, contract) == 0
    finally:
        mp.undo()
    store = base / "store"
    report = base / "report.json"
    assert _publish_cli(lane, contract, store, report) == 0
    return {"identity": lane["identity"], "store": store}


@pytest.fixture()
def production_client(monkeypatch, production_lane):
    """Private API client in production mode over the publisher-built store."""
    monkeypatch.setattr(forensics_api, "REPO", ROOT)
    app = FastAPI()
    app.include_router(forensics_api.router)
    monkeypatch.setenv("FIF_FINANCIAL_DATASET_MODE", "production")
    monkeypatch.setenv("FIF_PRODUCTION_DATASET_LOCAL_STORE", str(production_lane["store"]))
    forensics_api._reset_production_provider_cache()
    app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {"id": "paid-user"}
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
    forensics_api._reset_production_provider_cache()


# ---------------------------------------------------------------------------
# Request bodies (the page's shapes, over the staged FY2024 revenue duration)
# ---------------------------------------------------------------------------


def _statements_body(identity: dict) -> bytes:
    return json.dumps(
        {
            "schema": _STATEMENT_SCHEMA,
            "entity_id": identity["entity_id"],
            "accession": identity["accessions"][0],
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _policy_body(schema: str, identity: dict) -> bytes:
    return json.dumps(
        {
            "schema": schema,
            "entity_id": identity["entity_id"],
            "policy": {
                "selection": "latest_known_as_of",
                "source_snapshot_at": "2025-12-31T23:59:59Z",
                "recorded_at": RUN_CLOCK,
            },
            "metric_ids": ["revenue"],
            "periods": [dict(_REVENUE_PERIOD)],
        },
        separators=(",", ":"),
    ).encode("utf-8")


# ---------------------------------------------------------------------------
# The no-network law
# ---------------------------------------------------------------------------


def test_no_forensics_route_opens_a_socket_while_serving(
    production_client, production_lane, monkeypatch
) -> None:
    attempts: list[str] = []

    def _connect(self, address, *args, **kwargs):
        attempts.append(f"socket.socket.connect({address!r})")
        raise AssertionError("network")

    def _connect_ex(self, address, *args, **kwargs):
        attempts.append(f"socket.socket.connect_ex({address!r})")
        raise AssertionError("network")

    def _create_connection(address, *args, **kwargs):
        attempts.append(f"socket.create_connection({address!r})")
        raise AssertionError("network")

    monkeypatch.setattr(socket.socket, "connect", _connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _connect_ex)
    monkeypatch.setattr(socket, "create_connection", _create_connection)

    identity = production_lane["identity"]
    calls = [
        ("health", "GET", "/api/forensics/health", None),
        (
            "financial/query",
            "POST",
            "/api/forensics/v1/financial/query",
            _policy_body(_QUERY_SCHEMA, identity),
        ),
        (
            "financial/packet",
            "POST",
            "/api/forensics/v1/financial/packet",
            _policy_body(_PACKET_SCHEMA, identity),
        ),
        (
            "financial/statements",
            "POST",
            "/api/forensics/v1/financial/statements",
            _statements_body(identity),
        ),
        (
            "financial/revisions",
            "POST",
            "/api/forensics/v1/financial/revisions",
            _policy_body(_REVISION_SCHEMA, identity),
        ),
    ]
    for name, method, path, body in calls:
        if method == "GET":
            response = production_client.get(path)
        else:
            response = production_client.post(
                path, content=body, headers={"content-type": "application/json"}
            )
        assert response.status_code == 200, (name, response.status_code, response.text[:400])
    assert attempts == [], f"request-time network reach attempted: {attempts}"
