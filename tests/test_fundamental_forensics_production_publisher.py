"""FIF C0-b: the production dataset publisher CLI — end-to-end over a TEMP store.

Drives ``scripts.publish_fif_production_datasets`` through its real ``main()``
with a fake SEC collector (offline), the REAL S2-p lineage seam
(``engine.fundamental_forensics.production_lineage``, imported directly by the
producer since Phase B — no ``sys.modules`` fake anywhere), a synthetic
coverage contract under ``tmp_path``, and the repository's ``LocalStore``
adapter. No network, no R2, no env file. Every issuer identity is derived at
runtime from the committed fixture bytes, so no ticker or CIK literal appears
here.
"""
from __future__ import annotations

import ast
import gzip
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from collectors.sec_document_spine import (
    persist_archive_document,
    retain_filing_manifest,
    with_document_retrievals,
)
from collectors.sec_request_pacer import SecRequestPacer
from engine.fundamental_forensics.admitted_filing_package import (
    admit_retained_filing_package,
)
from engine.fundamental_forensics.fif_member_capture import read_retained_fif_packages
from engine.fundamental_forensics.lineage_evidence import LineageEvidenceError
from engine.fundamental_forensics.production_datasets import (
    load_generation,
    lineage_from_role_payload,
)
from engine.fundamental_forensics.production_lineage import (
    mint_production_lineage_evidence,
)
from engine.fundamental_forensics.sec_document_spine import build_filing_manifests
from engine.fundamental_forensics.statement_graph import GOLDEN_AAPL_FIXTURES
import scripts.publish_fif_production_datasets as producer

ROOT = Path(__file__).resolve().parents[1]

FIRST_ACCEPTED_AT = "2025-10-31T10:01:26.000Z"   # real-shaped: accepted 2025
SECOND_ACCEPTED_AT = "2024-07-31T10:01:26.000Z"  # real-shaped: accepted 2024
CAPTURE_CLOCK = "2026-10-13T02:31:00Z"           # captured AFTER 2026-10-12
RUN_CLOCK = "2026-10-13T02:35:00Z"
NEXT_NIGHT_CAPTURE = "2026-10-14T02:31:00Z"
NEXT_NIGHT_RUN = "2026-10-14T02:35:00Z"
EARLY_RUN_CLOCK = "2026-10-12T00:00:00Z"
MID_RULES_CAPTURE = "2026-09-01T00:00:00Z"
MID_RULES_RUN = "2026-09-01T00:05:00Z"
USER_AGENT = "MastermindX FIF C0-b publisher test bench test@example.invalid"
LATEST_KEY_TEMPLATE = "fundamental_forensics/production-datasets/v1/issuers/{issuer_id}/latest.json"


# ---------------------------------------------------------------------------
# Synthetic lane materializer (identity derived at runtime — no literals)
# ---------------------------------------------------------------------------


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
    (raw_root / cik / "submissions" / "latest.json").parent.mkdir(
        parents=True, exist_ok=True
    )
    (raw_root / cik / "submissions" / "latest.json").write_text(
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
        self.fetched: list[str] = []
        self.pacer_acquires = 0

    def fetch_document(self, document, *, retrieved_at=None, expected_sha256=None, max_document_bytes=None):
        self._pacer.acquire()
        self.pacer_acquires += 1
        url = document["archive_url"]
        accession = url.rsplit("/", 2)[-2].replace("-", "")
        name = url.rsplit("/", 1)[-1]
        self.fetched.append(name)
        return persist_archive_document(
            self.cache_root,
            document,
            self._served[accession][name],
            retrieved_at=retrieved_at,
        )


def _no_sleep_pacer(**kwargs) -> SecRequestPacer:
    return SecRequestPacer(
        min_interval_seconds=kwargs.get("min_interval_seconds", 0.12),
        sleeper=lambda _seconds: None,
        monotonic=lambda: 0.0,
    )


@pytest.fixture()
def offline_collector(monkeypatch):
    """Route the CLI's collector + pacer construction to offline fakes."""
    served = _served_members()
    collectors: list[_FakeCollector] = []
    pacers: list[SecRequestPacer] = []

    def _collector_factory(cache_root, **kwargs):
        pacer = kwargs["pacer"]
        collector = _FakeCollector(cache_root, served, pacer)
        collectors.append(collector)
        return collector

    def _pacer_factory(**kwargs):
        pacer = _no_sleep_pacer(**kwargs)
        pacers.append(pacer)
        return pacer

    monkeypatch.setattr(producer, "SecFilingArchiveCollector", _collector_factory)
    monkeypatch.setattr(producer, "SecRequestPacer", _pacer_factory)
    return {"collectors": collectors, "pacers": pacers, "served": served}


def _write_contract(tmp_path: Path, identity: dict, second_issuer: dict | None) -> Path:
    issuers = [
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
            "accessions": [{"accession": a} for a in identity["accessions"]],
        }
    ]
    if second_issuer is not None:
        issuers.append(second_issuer)
    path = tmp_path / "contract.json"
    path.write_text(
        json.dumps(
            {
                "schema": "fundamental_forensics.coverage_contract/v1",
                "contract_id": "synthetic-c0b-test",
                "issuers": issuers,
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    return path


def _derived_second_issuer(identity: dict, *, binding: bool) -> dict:
    """A second issuer whose identity is DERIVED from the first at runtime."""
    cik = identity["cik"][:-1] + str((int(identity["cik"][-1]) + 1) % 10)
    ticker = identity["ticker"] + "2"
    entity_id = identity["entity_id"] + "2"
    row = {
        "cik": cik,
        "ticker": ticker,
        "legal_name": "Derived Second Issuer",
        "accessions": [
            {"accession": identity["accessions"][0][:-1] + "7"}
        ],
    }
    if binding:
        row["security_master_binding"] = {
            "issuer_id": entity_id,
            "issuer_cik": cik,
            "security_id": identity["security_id"] + "2",
            "listing_key": identity["listing_key"] + "2",
            "mic": "XNAS",
            "effective_at": "2023-05-09T00:00:00",
        }
    return row


def _materialize_lane(tmp_path: Path) -> dict:
    identity = _fixture_identity()
    raw_root = tmp_path / "raw"
    archive_root = tmp_path / "archive"
    raw_root.mkdir(parents=True)
    archive_root.mkdir(parents=True)
    _write_submissions(raw_root, identity)
    _retain_primaries(archive_root, identity)
    return {"identity": identity, "raw_root": raw_root, "archive_root": archive_root}


def _capture_cli(lane: dict, contract: Path, clock: str = CAPTURE_CLOCK) -> int:
    return producer.main(
        [
            "capture-members",
            "--coverage-file", str(contract),
            "--raw-root", str(lane["raw_root"]),
            "--archive-root", str(lane["archive_root"]),
            "--recorded-at", clock,
            "--user-agent", USER_AGENT,
        ]
    )


def _publish_cli(lane: dict, contract: Path, store: Path, report: Path, clock: str = RUN_CLOCK) -> int:
    return producer.main(
        [
            "publish",
            "--coverage-file", str(contract),
            "--raw-root", str(lane["raw_root"]),
            "--archive-root", str(lane["archive_root"]),
            "--recorded-at", clock,
            "--store-dir", str(store),
            "--repo-root", str(ROOT),
            "--report-path", str(report),
        ]
    )


def _spy_on_mint(monkeypatch) -> list[dict]:
    """Observe the producer's DIRECT seam import — the real mint still runs.

    Phase B: the producer imports ``mint_production_lineage_evidence`` at
    module level, so the observation point is the NAME it imported on the
    producer module (never a ``sys.modules`` fake — the guard's tripwire and
    the spec's import-graph law both forbid that shape).
    """
    real_mint = producer.mint_production_lineage_evidence
    calls: list[dict] = []

    def _spy(ledger, packages, *, system_available_at):
        result = real_mint(ledger, packages, system_available_at=system_available_at)
        calls.append(
            {
                "ledger": ledger,
                "packages": tuple(packages),
                "system_available_at": system_available_at,
                "result": tuple(result),
            }
        )
        return result

    monkeypatch.setattr(producer, "mint_production_lineage_evidence", _spy)
    return calls


def _latest_json_path(store: Path, issuer_id: str) -> Path:
    return store / LATEST_KEY_TEMPLATE.format(issuer_id=issuer_id)


def _stderr_error_lines(capsys) -> list[str]:
    """D8: every ::error annotation rides stderr (stdout may be $(...)-captured)."""
    return [
        line for line in capsys.readouterr().err.splitlines() if line.startswith("::error")
    ]


# ---------------------------------------------------------------------------
# A3: publish, pointer read-back, idempotency, REAL-SHAPED clocks
# ---------------------------------------------------------------------------


def test_publishes_names_generation_and_reuses_capture_clocks(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    store = tmp_path / "store"
    report_path = tmp_path / "publish_report.json"
    mint_calls = _spy_on_mint(monkeypatch)

    assert _capture_cli(lane, contract) == 0
    assert len(offline_collector["collectors"]) == 1  # ONE collector...
    assert len(offline_collector["pacers"]) == 1      # ...on ONE shared pacer
    collector = offline_collector["collectors"][0]
    assert collector.pacer_acquires == len(collector.fetched) == 12
    assert collector._pacer is offline_collector["pacers"][0]

    assert _publish_cli(lane, contract, store, report_path) == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert [row["ticker"] for row in report["published"]] == [identity["ticker"]]
    assert report["excluded"] == []
    row = report["published"][0]
    # CLOCK RULE: max(capture clocks, both rule clocks, registry clocks). The
    # capture clock (after 2026-10-12) dominates; printed for the seat report.
    assert datetime.fromisoformat(
        row["admitted_at"].replace("Z", "+00:00")
    ) == datetime(2026, 10, 13, 2, 31, tzinfo=timezone.utc)
    print(f"REAL-SHAPED admitted_at={row['admitted_at']}", flush=True)
    assert row["admitted_accessions"] == sorted(identity["accessions"])

    # A3: latest.json NAMES the generation (pointer, not mere existence).
    latest_path = _latest_json_path(store, identity["entity_id"])
    pointer = json.loads(latest_path.read_text(encoding="utf-8"))
    assert pointer["generation_id"] == row["generation_id"]

    # S2-p seam (Phase B, real): called exactly once per published issuer with
    # the admitted ledger/packages and system_available_at == the material's
    # admitted_at, and its return lands UNCHANGED in the published generation.
    assert len(mint_calls) == 1
    call = mint_calls[0]
    assert len(call["packages"]) == 2
    assert call["ledger"] is not None
    assert call["system_available_at"] == datetime(
        2026, 10, 13, 2, 31, tzinfo=timezone.utc
    )
    generation = load_generation(
        producer.build_production_dataset_store(store), identity["entity_id"], row["generation_id"]
    )
    round_tripped = lineage_from_role_payload(
        generation.role_payloads["lineage_evidence_json"]
    )
    assert [item.to_dict() for item in round_tripped] == [
        item.to_dict() for item in call["result"]
    ]
    assert row["lineage_receipt_count"] == len(call["result"])

    # verify subcommand over the same report + store.
    assert (
        producer.main(
            [
                "verify",
                "--coverage-file", str(contract),
                "--report-path", str(report_path),
                "--store-dir", str(store),
            ]
        )
        == 0
    )

    # Idempotency: a second night skips retained accessions, reuses the prior
    # capture clock, and re-derives the SAME generation id.
    assert _capture_cli(lane, contract, clock=NEXT_NIGHT_CAPTURE) == 0
    second_collector = offline_collector["collectors"][-1]
    assert second_collector.fetched == []
    latest_before = latest_path.read_bytes()
    assert _publish_cli(lane, contract, store, report_path, clock=NEXT_NIGHT_RUN) == 0
    report2 = json.loads(report_path.read_text(encoding="utf-8"))
    assert report2["published"][0]["generation_id"] == row["generation_id"]
    assert report2["published"][0]["admitted_at"] == row["admitted_at"]
    assert latest_path.read_bytes() == latest_before
    assert len(mint_calls) == 2  # once per publish run, still one issuer


def test_future_clock_refusal_writes_nothing(tmp_path, monkeypatch, offline_collector, capsys) -> None:
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    assert _capture_cli(lane, contract) == 0
    store = tmp_path / "store"
    report_path = tmp_path / "publish_report.json"

    # A3b: --recorded-at earlier than the CLOCK RULE value refuses the run.
    rc = _publish_cli(lane, contract, store, report_path, clock=EARLY_RUN_CLOCK)
    assert rc == 1
    error_lines = _stderr_error_lines(capsys)
    assert error_lines
    joined = " ".join(error_lines)
    assert "admitted_at_after_recorded_at" in joined
    assert "2026-10-13T02:31:00" in joined    # the computed admitted_at
    assert "2026-10-12T00:00:00" in joined    # the run clock (--recorded-at)
    assert not store.exists()                 # no store, no generation, no pointer

    # A lawful publish first, then an early-clock run leaves latest.json intact.
    assert _publish_cli(lane, contract, store, report_path) == 0
    latest_path = _latest_json_path(store, identity["entity_id"])
    before = latest_path.read_bytes()
    assert (
        _publish_cli(lane, contract, store, report_path, clock=EARLY_RUN_CLOCK) == 1
    )
    assert latest_path.read_bytes() == before


def test_rule_clock_alone_can_force_the_future_clock_refusal(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    # Captured BETWEEN the two rule clocks: the chain-rule clock (the later
    # one) dominates admitted_at and lands after --recorded-at.
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    assert _capture_cli(lane, contract, clock=MID_RULES_CAPTURE) == 0
    rc = _publish_cli(
        lane, contract, tmp_path / "store", tmp_path / "report.json", clock=MID_RULES_RUN
    )
    assert rc == 1
    assert any(
        "admitted_at_after_recorded_at" in line for line in _stderr_error_lines(capsys)
    )


def test_published_lineage_round_trips_and_equals_a_direct_mint(
    tmp_path, monkeypatch, offline_collector
) -> None:
    """Phase B REAL round-trip: no fakes for the seam anywhere.

    Synthetic admitted packages under ``tmp_path`` -> publish into a TEMP local
    store through the producer's direct seam import -> read the published
    generation's ``lineage_evidence`` back -> it round-trips through
    ``lineage_from_role_payload`` AND equals ``mint_production_lineage_evidence``
    called DIRECTLY on the same ledger + same admitted packages with the
    published ``admitted_at`` as the clock.
    """
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    assert _capture_cli(lane, contract) == 0
    store = tmp_path / "store"
    report_path = tmp_path / "publish_report.json"
    assert _publish_cli(lane, contract, store, report_path) == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    row = report["published"][0]
    published_admitted_at = datetime.fromisoformat(
        row["admitted_at"].replace("Z", "+00:00")
    )

    # Rebuild the SAME admitted set + ledger the producer published from (same
    # retained order, same admission call, same converter composition).
    retained = read_retained_fif_packages(
        lane["archive_root"], cik=identity["cik"], accessions=identity["accessions"]
    )
    admitted = tuple(
        admit_retained_filing_package(
            index_bytes=package.index_bytes,
            manifest=dict(package.manifest),
            members=dict(package.members),
            witness_bytes=package.witness_bytes,
            capture_recorded_at=package.capture_recorded_at,
        )
        for package in retained
    )
    ledger, _filing_metadata, _convert_report = producer._convert_admitted_packages(
        admitted
    )

    expected = mint_production_lineage_evidence(
        ledger, admitted, system_available_at=published_admitted_at
    )
    assert row["lineage_receipt_count"] == len(expected)

    generation = load_generation(
        producer.build_production_dataset_store(store),
        identity["entity_id"],
        row["generation_id"],
    )
    round_tripped = lineage_from_role_payload(
        generation.role_payloads["lineage_evidence_json"]
    )
    assert [item.to_dict() for item in round_tripped] == [
        item.to_dict() for item in expected
    ]
    print(
        f"ROUND-TRIP receipts published={len(round_tripped)} direct_mint={len(expected)}",
        flush=True,
    )


# ---------------------------------------------------------------------------
# A2: publish set + typed exclusions (closed vocabulary, exactly once)
# ---------------------------------------------------------------------------


def test_two_issuer_contract_publishes_and_excludes_exactly_once(
    tmp_path, monkeypatch, offline_collector
) -> None:
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    second = _derived_second_issuer(identity, binding=False)
    contract = _write_contract(tmp_path, identity, second)
    assert _capture_cli(lane, contract) == 0
    store = tmp_path / "store"
    report_path = tmp_path / "publish_report.json"
    assert _publish_cli(lane, contract, store, report_path) == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert [row["ticker"] for row in report["published"]] == [identity["ticker"]]
    assert [row["reason"] for row in report["excluded"]] == ["identity_not_frozen"]
    assert report["excluded"][0]["cik"] == second["cik"]
    seen = [row["cik"] for row in (*report["published"], *report["excluded"])]
    assert sorted(seen) == sorted({identity["cik"], second["cik"]})


def test_exclusion_no_retained_package(tmp_path, monkeypatch, offline_collector) -> None:
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    # Identity frozen, but the only contract accession was never retained.
    original = identity["accessions"][0]
    invented = original[:-1] + ("7" if original[-1] != "7" else "8")
    contract = _write_contract(tmp_path, identity, None)
    document = json.loads(contract.read_text(encoding="utf-8"))
    document["issuers"][0]["accessions"] = [{"accession": invented}]
    contract.write_text(json.dumps(document), encoding="utf-8")
    assert _capture_cli(lane, contract) == 0
    report_path = tmp_path / "publish_report.json"
    assert (
        _publish_cli(lane, contract, tmp_path / "store", report_path) == 0
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["published"] == []
    assert [row["reason"] for row in report["excluded"]] == ["no_retained_package"]


def test_exclusion_identity_not_frozen(tmp_path, monkeypatch, offline_collector) -> None:
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    document = json.loads(contract.read_text(encoding="utf-8"))
    document["issuers"][0].pop("security_master_binding")
    contract.write_text(json.dumps(document), encoding="utf-8")
    assert _capture_cli(lane, contract) == 0
    report_path = tmp_path / "publish_report.json"
    assert _publish_cli(lane, contract, tmp_path / "store", report_path) == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert [row["reason"] for row in report["excluded"]] == ["identity_not_frozen"]


def test_exclusion_admission_refused_is_typed(
    tmp_path, monkeypatch, offline_collector
) -> None:
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    assert _capture_cli(lane, contract) == 0
    # Tamper every package's manifest form: reads stay digest-clean, but the
    # witness bind refuses admission with a typed D1 code.
    for accession in identity["accessions"]:
        manifest_path = (
            lane["archive_root"]
            / "fif-packages"
            / identity["cik"]
            / accession
            / "package_manifest.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["form"] = manifest["form"] + "-X"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    report_path = tmp_path / "publish_report.json"
    assert _publish_cli(lane, contract, tmp_path / "store", report_path) == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["published"] == []
    assert [row["reason"] for row in report["excluded"]] == [
        "admission_refused:witness_mismatch"
    ]


def test_tampered_package_refuses_the_whole_publish_run(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    """ERRATA E1.5: an integrity code is a RUN-level refusal, never an exclusion."""
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    assert _capture_cli(lane, contract) == 0
    for accession in identity["accessions"]:
        members_dir = (
            lane["archive_root"] / "fif-packages" / identity["cik"] / accession / "members"
        )
        victim = sorted(members_dir.iterdir())[0]
        victim.write_bytes(victim.read_bytes()[:-1])
    store = tmp_path / "store"
    report_path = tmp_path / "publish_report.json"
    rc = _publish_cli(lane, contract, store, report_path)
    assert rc == 1
    assert any(
        "retained_package_integrity" in line for line in _stderr_error_lines(capsys)
    )
    # NOTHING was published that night: no report, no store, no pointer.
    assert not report_path.exists()
    assert not store.exists() or not any(store.rglob("latest.json"))


def test_publish_never_emits_an_integrity_member_capture_exclusion(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    """The verify vocabulary KEEPS the member_capture_failed:<code> entry, but
    publish itself can never emit one for an integrity code — those refuse the
    whole run before a report exists (ERRATA E1.5)."""
    # The closed vocabulary still accepts the prefix for non-integrity codes.
    producer.verify_report(
        {
            "published": [],
            "excluded": [
                {
                    "ticker": "derived",
                    "cik": "0000000001",
                    "reason": "member_capture_failed:member_fetch_failed",
                }
            ],
        },
        None,
    )
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    assert _capture_cli(lane, contract) == 0
    members_dir = (
        lane["archive_root"]
        / "fif-packages"
        / identity["cik"]
        / identity["accessions"][0]
        / "members"
    )
    victim = sorted(members_dir.iterdir())[0]
    victim.write_bytes(victim.read_bytes()[:-1])
    report_path = tmp_path / "publish_report.json"
    rc = _publish_cli(lane, contract, tmp_path / "store", report_path)
    assert rc == 1
    # No report was written, so no exclusion row for an integrity code exists.
    assert not report_path.exists()


# ---------------------------------------------------------------------------
# A4: hard failures (rc != 0 + line-start ::error, never swallowed)
# ---------------------------------------------------------------------------


def test_untyped_admission_error_hard_fails(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    assert _capture_cli(lane, contract) == 0

    def _explode(**_kwargs):
        raise RuntimeError("synthetic admission crash")

    monkeypatch.setattr(producer, "admit_retained_filing_package", _explode)
    rc = _publish_cli(lane, contract, tmp_path / "store", tmp_path / "report.json")
    assert rc == 1
    assert _stderr_error_lines(capsys)


def test_lineage_mint_error_hard_fails(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)

    def _explode(_ledger, _packages, *, system_available_at):
        raise LineageEvidenceError(
            f"synthetic mint refusal below the floor: {system_available_at}"
        )

    # Phase B: the seam is the NAME the producer imported — raise through it.
    monkeypatch.setattr(producer, "mint_production_lineage_evidence", _explode)
    assert _capture_cli(lane, contract) == 0
    rc = _publish_cli(lane, contract, tmp_path / "store", tmp_path / "report.json")
    assert rc == 1
    lines = _stderr_error_lines(capsys)
    assert lines
    assert "synthetic mint refusal" in " ".join(lines)
    # Nothing was published: no store content at all.
    assert not (tmp_path / "store").exists() or not any(
        (tmp_path / "store").rglob("latest.json")
    )


def test_verify_refuses_a_report_that_drops_an_issuer(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    second = _derived_second_issuer(identity, binding=False)
    contract = _write_contract(tmp_path, identity, second)
    assert _capture_cli(lane, contract) == 0
    store = tmp_path / "store"
    report_path = tmp_path / "publish_report.json"
    assert _publish_cli(lane, contract, store, report_path) == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["excluded"] = []  # silently drop the excluded issuer
    report_path.write_text(json.dumps(report), encoding="utf-8")
    rc = producer.main(
        [
            "verify",
            "--coverage-file", str(contract),
            "--report-path", str(report_path),
            "--store-dir", str(store),
        ]
    )
    assert rc == 1
    assert _stderr_error_lines(capsys)


# ---------------------------------------------------------------------------
# A5: golden refusal
# ---------------------------------------------------------------------------


def test_fixture_tree_inputs_are_refused(tmp_path, monkeypatch, offline_collector, capsys) -> None:
    identity = _fixture_identity()
    contract = _write_contract(tmp_path, identity, None)
    fixture_root = ROOT / "tests" / "fixtures" / "fundamental_forensics"
    for subcommand in ("capture-members", "publish"):
        argv = [
            subcommand,
            "--coverage-file", str(contract),
            "--raw-root", str(fixture_root),
            "--archive-root", str(fixture_root),
            "--recorded-at", RUN_CLOCK,
        ]
        if subcommand == "capture-members":
            argv += ["--user-agent", USER_AGENT]
        else:
            argv += ["--store-dir", str(tmp_path / "store"), "--repo-root", str(ROOT)]
        rc = producer.main(argv)
        assert rc == 1
        assert any(
            "golden_input_refused" in line for line in _stderr_error_lines(capsys)
        )


def test_golden_schema_manifest_is_refused_at_publish(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    assert _capture_cli(lane, contract) == 0
    # Replace one retained package manifest with a golden-schema manifest.
    accession = identity["accessions"][0]
    manifest_path = (
        lane["archive_root"] / "fif-packages" / identity["cik"] / accession / "package_manifest.json"
    )
    golden = json.loads(
        (ROOT / GOLDEN_AAPL_FIXTURES[accession] / "package_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    manifest_path.write_text(json.dumps(golden), encoding="utf-8")
    rc = _publish_cli(lane, contract, tmp_path / "store", tmp_path / "report.json")
    assert rc == 1
    assert any(
        "golden_input_refused" in line for line in _stderr_error_lines(capsys)
    )


# ---------------------------------------------------------------------------
# A1: targets subcommand (issuer-generic, derived from the contract)
# ---------------------------------------------------------------------------


def _write_targets_file(tmp_path: Path, count: int) -> Path:
    targets = [
        {"ticker": f"T{i:03d}", "cik": f"0000000{i + 1:02d}"} for i in range(count)
    ]
    path = tmp_path / "targets.json"
    path.write_text(
        json.dumps(
            {"schema": "fundamental_forensics.wave2_targets/v1", "targets": targets}
        ),
        encoding="utf-8",
    )
    return path


def test_targets_derives_contract_extras_and_refuses_overflow(tmp_path, capsys) -> None:
    identity = _fixture_identity()
    contract = _write_contract(tmp_path, identity, None)
    targets_file = _write_targets_file(tmp_path, 2)
    rc = producer.main(
        [
            "targets",
            "--coverage-file", str(contract),
            "--targets-file", str(targets_file),
            "--max-tickers", "3",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert out.strip() == f"--target {identity['ticker']}={identity['cik']}"
    rc = producer.main(
        [
            "targets",
            "--coverage-file", str(contract),
            "--targets-file", str(targets_file),
            "--max-tickers", "2",
        ]
    )
    assert rc == 1
    assert _stderr_error_lines(capsys)


def test_targets_over_the_real_contract_within_the_cap(capsys) -> None:
    contract_path = ROOT / "config" / "fundamental_forensics" / "coverage" / "five_issuer_v1.json"
    targets_path = ROOT / "config" / "fundamental_forensics" / "wave2_targets.v1.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    incumbent = json.loads(targets_path.read_text(encoding="utf-8"))["targets"]
    expected = {
        f"--target {issuer['ticker']}={issuer['cik']}"
        for issuer in contract["issuers"]
        if issuer["ticker"] not in {row["ticker"] for row in incumbent}
    }
    rc = producer.main(
        [
            "targets",
            "--coverage-file", str(contract_path),
            "--targets-file", str(targets_path),
            "--max-tickers", "15",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert set(out.split()) >= set(" ".join(expected).split())
    assert set(out.strip().splitlines()) == expected
    # ERRATA E2-R (T8): the REAL configs compute a union of exactly 15 —
    # 12 incumbents + 3 contract extras. Fail closed at 15; growth needs a
    # seat ruling.
    assert len(incumbent) == 12
    assert len(expected) == 3
    assert len(incumbent) + len(expected) == 15


# ---------------------------------------------------------------------------
# A5: import graph (direct imports + sys.modules after import)
# ---------------------------------------------------------------------------


def _direct_import_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
                names.add(alias.asname or alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module)
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return names


def test_producer_direct_imports_are_off_the_golden_and_mint_layers() -> None:
    source = (ROOT / "scripts" / "publish_fif_production_datasets.py").read_text(
        encoding="utf-8"
    )
    names = _direct_import_names(ast.parse(source))
    forbidden = {
        "derive_confirmation_receipts",
        "derive_chain_confirmation_receipts",
        "GoldenAaplFinancialQueryProvider",
        "parse_and_convert_golden_packages",
        "load_golden_aapl_package",
        "GOLDEN_AAPL_QUERY_ACCESSIONS",
        "GOLDEN_AAPL_FIXTURES",
    }
    assert names.isdisjoint(forbidden), sorted(names & forbidden)
    assert not any("GOLDEN_AAPL" in name for name in names)
    # The S2-p seam is imported DIRECTLY by name at module level (spec §3,
    # Phase B): exactly one ImportFrom of the seam module binding exactly the
    # frozen mint symbol, and no lazy importlib fallback anywhere.
    seam_froms = [
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom)
        and node.module == "engine.fundamental_forensics.production_lineage"
    ]
    assert len(seam_froms) == 1
    assert [alias.name for alias in seam_froms[0].names] == [
        "mint_production_lineage_evidence"
    ]
    assert "mint_production_lineage_evidence" in names
    assert "importlib" not in source


# The import-graph probe runs in a SUBPROCESS on purpose: a fresh interpreter
# observes the producer's import graph without ever touching this process's
# sys.modules (the guard's tripwire), and no ``-I`` so the repo root stays
# importable via cwd. Phase B truth: importing the producer DOES bring the
# S2-p seam module in, and never a golden provider or a direct mint layer.
_PRODUCER_IMPORT_PROBE = """
import ast
import json
import sys
from pathlib import Path

import scripts.publish_fif_production_datasets as producer

findings = []
# The DIRECT seam import: present after importing the producer.
if "engine.fundamental_forensics.production_lineage" not in sys.modules:
    findings.append(
        "sys.modules missing: engine.fundamental_forensics.production_lineage"
    )
# No golden provider module ever loads for the producer's import graph.
findings.extend(
    "sys.modules: " + name for name in sys.modules if "golden_aapl" in name.lower()
)
findings.extend(
    "producer attr: " + name
    for name in dir(producer)
    if "GOLDEN" in name.upper()
)
findings.extend(
    "producer attr: " + name
    for name in (
        "GoldenAaplFinancialQueryProvider",
        "load_golden_aapl_package",
        "derive_confirmation_receipts",
        "derive_chain_confirmation_receipts",
    )
    if hasattr(producer, name)
)
# AST scan: the producer and fif_member_capture.py directly import neither
# mint layer nor golden provider (transitive reach through the seam module is
# the lawful S2-p path).
FORBIDDEN = {
    "derive_confirmation_receipts",
    "derive_chain_confirmation_receipts",
    "GoldenAaplFinancialQueryProvider",
    "parse_and_convert_golden_packages",
    "load_golden_aapl_package",
}
root = Path.cwd()
for relative in (
    "scripts/publish_fif_production_datasets.py",
    "engine/fundamental_forensics/fif_member_capture.py",
):
    tree = ast.parse((root / relative).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            imported = [alias.asname or alias.name for alias in node.names]
        else:
            continue
        for name in imported:
            if name in FORBIDDEN or "GOLDEN_AAPL" in name:
                findings.append("direct import " + relative + ": " + name)
print(json.dumps(sorted(findings)))
"""


def test_producer_import_loads_no_mint_layer_or_golden_provider() -> None:
    result = subprocess.run(
        [sys.executable, "-c", _PRODUCER_IMPORT_PROBE],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    findings = json.loads(result.stdout.strip().splitlines()[-1])
    assert findings == [], findings


def test_no_ticker_or_cik_literal_in_producer_or_workflow() -> None:
    contract = json.loads(
        (
            ROOT / "config" / "fundamental_forensics" / "coverage" / "five_issuer_v1.json"
        ).read_text(encoding="utf-8")
    )
    sources = {
        "producer": (
            ROOT / "scripts" / "publish_fif_production_datasets.py"
        ).read_text(encoding="utf-8"),
        "capture_module": (
            ROOT / "engine" / "fundamental_forensics" / "fif_member_capture.py"
        ).read_text(encoding="utf-8"),
        "workflow": (
            ROOT / ".github" / "workflows" / "filing-forensics-sec.yml"
        ).read_text(encoding="utf-8"),
    }
    for name, source in sources.items():
        for issuer in contract["issuers"]:
            assert issuer["ticker"] not in source, (name, issuer["ticker"])
            assert issuer["cik"] not in source, (name, issuer["cik"])


# ---------------------------------------------------------------------------
# ERRATA E1: capture-members fails closed on retained-package integrity
# ---------------------------------------------------------------------------


def _stdout_json(out: str) -> dict:
    """Parse the capture report from stdout (drops trailing ::error lines)."""
    payload = "\n".join(
        line for line in out.splitlines() if not line.startswith("::")
    )
    return json.loads(payload)


def test_capture_members_exits_nonzero_on_tampered_retained_member(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    """T1: tampered restored member -> rc != 0, code retained_package_integrity,
    the package's capture_recorded_at unchanged on disk, no new clock in the report."""
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    assert _capture_cli(lane, contract) == 0
    package_dir = (
        lane["archive_root"] / "fif-packages" / identity["cik"] / identity["accessions"][0]
    )
    manifest_before = (package_dir / "package_manifest.json").read_bytes()
    member = sorted((package_dir / "members").iterdir())[0]
    member.write_bytes(member.read_bytes()[:-1])

    capsys.readouterr()  # drop the first run's output before the refusing run
    rc = _capture_cli(lane, contract, clock=NEXT_NIGHT_CAPTURE)
    assert rc == 1
    captured = capsys.readouterr()
    assert any(
        "retained_package_integrity" in line
        for line in captured.err.splitlines()
        if line.startswith("::error")
    )
    report = _stdout_json(captured.out)
    rows = report["issuers"][0]["accessions"]
    assert rows[0]["outcome"] == "member_capture_failed:package_bytes_mismatch"
    assert rows[1]["outcome"] == "retained_reused"
    # No new clock: no accession row carries tonight's capture clock.
    assert all(row["capture_recorded_at"] != NEXT_NIGHT_CAPTURE for row in rows)
    assert rows[1]["capture_recorded_at"] == CAPTURE_CLOCK
    # The on-disk manifest — capture_recorded_at included — is unchanged.
    assert (package_dir / "package_manifest.json").read_bytes() == manifest_before
    # The re-run fetched nothing (the clean accession reused, the tampered one refused).
    assert offline_collector["collectors"][-1].fetched == []


def test_capture_members_exits_nonzero_on_manifest_less_package_dir(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    """T2: manifest deleted -> package_manifest_malformed, nothing re-captured,
    ZERO fetches for that accession, member files untouched."""
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    assert _capture_cli(lane, contract) == 0
    package_dir = (
        lane["archive_root"] / "fif-packages" / identity["cik"] / identity["accessions"][0]
    )
    members_before = {
        path.name: path.read_bytes() for path in sorted((package_dir / "members").iterdir())
    }
    (package_dir / "package_manifest.json").unlink()

    capsys.readouterr()  # drop the first run's output before the refusing run
    rc = _capture_cli(lane, contract, clock=NEXT_NIGHT_CAPTURE)
    assert rc == 1
    captured = capsys.readouterr()
    assert any(
        "retained_package_integrity" in line
        for line in captured.err.splitlines()
        if line.startswith("::error")
    )
    report = _stdout_json(captured.out)
    rows = report["issuers"][0]["accessions"]
    assert rows[0]["outcome"] == "member_capture_failed:package_manifest_malformed"
    assert rows[1]["outcome"] == "retained_reused"
    # ZERO fetches for the manifest-less accession (and none anywhere this run).
    assert offline_collector["collectors"][-1].fetched == []
    members_after = {
        path.name: path.read_bytes() for path in sorted((package_dir / "members").iterdir())
    }
    assert members_after == members_before
    assert not (package_dir / "package_manifest.json").exists()


def _store_files(store: Path) -> list[str]:
    if not store.exists():
        return []
    return sorted(str(path.relative_to(store)) for path in store.rglob("*") if path.is_file())


def test_publish_over_one_tampered_package_moves_no_latest_json(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    """T3: one tampered package (the issuer's other package clean) -> run-level
    refusal, ZERO generations written, no latest.json moves.

    A synthetic second CIK cannot ride the fixture bytes: admission binds the
    package CIK to the filing's own dei EntityCentralIndexKey, so a derived
    CIK is inadmissible by incumbent law. The run-level claim is proven the
    stronger way instead: the whole STORE's file set is identical after the
    refused run, so nothing was written for any issuer.
    """
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    assert _capture_cli(lane, contract) == 0
    store = tmp_path / "store"
    report_path = tmp_path / "publish_report.json"
    assert _publish_cli(lane, contract, store, report_path) == 0
    first_report = json.loads(report_path.read_text(encoding="utf-8"))
    assert [row["ticker"] for row in first_report["published"]] == [identity["ticker"]]
    latest_path = _latest_json_path(store, identity["entity_id"])
    latest_before = latest_path.read_bytes()
    files_before = _store_files(store)
    assert files_before  # the lawful night actually wrote generations

    # Tamper ONE member of the FIRST package; the second package stays clean.
    members_dir = (
        lane["archive_root"]
        / "fif-packages"
        / identity["cik"]
        / identity["accessions"][0]
        / "members"
    )
    victim = sorted(members_dir.iterdir())[0]
    victim.write_bytes(victim.read_bytes()[:-1])

    capsys.readouterr()  # drop the lawful publish's output
    rc = _publish_cli(lane, contract, store, report_path)
    assert rc == 1
    assert any(
        "retained_package_integrity" in line for line in _stderr_error_lines(capsys)
    )
    # ZERO generations written; no latest.json for ANY issuer moved.
    assert _store_files(store) == files_before
    assert latest_path.read_bytes() == latest_before


# ---------------------------------------------------------------------------
# ERRATA E2-R: one cap value (15), single-sourced, fail-closed at the boundary
# ---------------------------------------------------------------------------

# sha256 of config/fundamental_forensics/wave2_targets.v1.json at the C0-b
# base commit 82830feb (git show 82830feb:...). The incumbent wave file is
# unchanged by C0-b; an edit needs a seat ruling.
WAVE2_TARGETS_BASE_SHA256 = "e80181f72cece207e722c7b7238249a01d533a9e6b845c8b4900f1f49529cf56"


def test_incumbent_wave2_targets_bytes_unchanged_from_base() -> None:
    digest = hashlib.sha256(
        (
            ROOT / "config" / "fundamental_forensics" / "wave2_targets.v1.json"
        ).read_bytes()
    ).hexdigest()
    assert digest == WAVE2_TARGETS_BASE_SHA256


def test_targets_requires_max_tickers() -> None:
    """T6: the publisher carries no second cap literal — the argument is required."""
    with pytest.raises(SystemExit) as caught:
        producer.build_parser().parse_args(
            ["targets", "--coverage-file", "c.json", "--targets-file", "t.json"]
        )
    assert caught.value.code == 2


def test_d11_lineage_mint_error_maps_to_lineage_mint_failed(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    """D11: a LineageEvidenceError from the S2-p seam is the typed
    lineage_mint_failed refusal — the code sat in the closed vocabulary but
    was unreachable, surfacing as generic publish_failed."""
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)

    def _explode(_ledger, _packages, *, system_available_at):
        raise LineageEvidenceError("synthetic mint refusal")

    # The seam is the NAME the producer imported (Phase B shape).
    monkeypatch.setattr(producer, "mint_production_lineage_evidence", _explode)
    assert _capture_cli(lane, contract) == 0
    rc = _publish_cli(lane, contract, tmp_path / "store", tmp_path / "report.json")
    assert rc == 1
    assert any(
        "lineage_mint_failed" in line for line in _stderr_error_lines(capsys)
    )


def test_d10_unparseable_registry_available_at_fails_closed() -> None:
    """D10: a registry ``available_at`` that exists but cannot be parsed is a
    typed contract_malformed refusal — it used to be silently dropped from the
    CLOCK RULE max, letting a malformed registry under-clock a generation."""
    for bogus in ("not-a-date", "2026-13-45T99:99:99Z", "   ", ""):
        with pytest.raises(producer.PublisherError) as caught:
            producer._registry_available_clocks(
                {"rule": {"available_at": bogus}}
            )
        assert caught.value.code == "contract_malformed", bogus
    # A non-string value is the same refusal; lawful clocks still parse.
    with pytest.raises(producer.PublisherError) as caught:
        producer._registry_available_clocks({"available_at": 20260802})
    assert caught.value.code == "contract_malformed"
    assert producer._registry_available_clocks(
        {"available_at": "2026-08-02T00:00:00Z"}
    ) == [datetime(2026, 8, 2, tzinfo=timezone.utc)]


def test_d8_targets_error_annotation_goes_to_stderr(tmp_path, capsys) -> None:
    """D8: the ``targets`` ::error must reach the Actions log even though the
    workflow captures this subcommand's stdout via ``$(...)`` — the annotation
    rides stderr (line-start, bare print); stdout carries no annotation."""
    identity = _fixture_identity()
    contract = _write_contract(tmp_path, identity, None)
    targets_file = _write_targets_file(tmp_path, 2)
    rc = producer.main(
        [
            "targets",
            "--coverage-file", str(contract),
            "--targets-file", str(targets_file),
            "--max-tickers", "1",
        ]
    )
    assert rc == 1
    captured = capsys.readouterr()
    assert not any(
        line.startswith("::error") for line in captured.out.splitlines()
    ), captured.out
    error_lines = [
        line for line in captured.err.splitlines() if line.startswith("::error")
    ]
    assert error_lines, captured.err
    assert "targets_overflow" in " ".join(error_lines)


def test_targets_cap_boundary_fifteen_passes_sixteen_refuses(tmp_path, capsys) -> None:
    """T7: through the REAL targets subcommand with temp config files."""
    identity = _fixture_identity()
    contract = _write_contract(tmp_path, identity, None)  # one contract issuer
    targets15 = _write_targets_file(tmp_path, 14)          # 14 incumbents + 1 = 15
    rc = producer.main(
        [
            "targets",
            "--coverage-file", str(contract),
            "--targets-file", str(targets15),
            "--max-tickers", "15",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert out.strip() == f"--target {identity['ticker']}={identity['cik']}"

    alt = tmp_path / "alt"
    alt.mkdir()
    targets16 = alt / "targets.json"
    targets16.write_text(
        json.dumps(
            {
                "schema": "fundamental_forensics.wave2_targets/v1",
                "targets": [
                    {"ticker": f"U{i:03d}", "cik": f"0000001{i + 1:02d}"}
                    for i in range(15)
                ],
            }
        ),
        encoding="utf-8",
    )  # 15 incumbents + 1 contract issuer = 16 > 15
    rc = producer.main(
        [
            "targets",
            "--coverage-file", str(contract),
            "--targets-file", str(targets16),
            "--max-tickers", "15",
        ]
    )
    assert rc == 1
    assert any(
        "targets_overflow" in line for line in _stderr_error_lines(capsys)
    )
