"""FIF C0-b: the production dataset publisher CLI — end-to-end over a TEMP store.

Drives ``scripts.publish_fif_production_datasets`` through its real ``main()``
with a fake SEC collector (offline), a fake S2-p lineage seam installed in
``sys.modules``, a synthetic coverage contract under ``tmp_path``, and the
repository's ``LocalStore`` adapter. No network, no R2, no env file. Every
issuer identity is derived at runtime from the committed fixture bytes, so no
ticker or CIK literal appears here.
"""
from __future__ import annotations

import ast
import gzip
import hashlib
import json
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

import pytest

from collectors.sec_document_spine import (
    persist_archive_document,
    retain_filing_manifest,
    with_document_retrievals,
)
from collectors.sec_request_pacer import SecRequestPacer
from engine.fundamental_forensics.lineage_evidence import (
    LineageEvidenceError,
    LineageEvidenceReceipt,
)
from engine.fundamental_forensics.production_datasets import (
    load_generation,
    lineage_from_role_payload,
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


def _receipt(system_available_at: datetime) -> LineageEvidenceReceipt:
    return LineageEvidenceReceipt(
        parent_occurrence_id="occ-parent-1",
        child_occurrence_id="occ-child-1",
        logical_key="synthetic:test:key",
        source_known_at=system_available_at,
        system_available_at=system_available_at,
        positive_evidence=None,
        refusal_reason="source_family_mismatch",
        relation_type="no_relation",
    )


def _install_fake_lineage(monkeypatch, receipts_factory=_receipt):
    calls: list[dict] = []
    module = types.ModuleType("engine.fundamental_forensics.production_lineage")

    def mint_production_lineage_evidence(ledger, packages, *, system_available_at):
        calls.append(
            {
                "ledger": ledger,
                "packages": tuple(packages),
                "system_available_at": system_available_at,
            }
        )
        return (receipts_factory(system_available_at),)

    module.mint_production_lineage_evidence = mint_production_lineage_evidence
    module.mint_calls = calls
    monkeypatch.setitem(
        sys.modules, "engine.fundamental_forensics.production_lineage", module
    )
    return module


def _latest_json_path(store: Path, issuer_id: str) -> Path:
    return store / LATEST_KEY_TEMPLATE.format(issuer_id=issuer_id)


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
    seam = _install_fake_lineage(monkeypatch)

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

    # S2-p seam: called exactly once per published issuer with the admitted
    # ledger/packages and system_available_at == material.admitted_at.
    assert len(seam.mint_calls) == 1
    call = seam.mint_calls[0]
    assert len(call["packages"]) == 2
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
        _receipt(call["system_available_at"]).to_dict()
    ]
    assert row["lineage_receipt_count"] == 1

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
    assert len(seam.mint_calls) == 2  # once per publish run, still one issuer


def test_future_clock_refusal_writes_nothing(tmp_path, monkeypatch, offline_collector, capsys) -> None:
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    _install_fake_lineage(monkeypatch)
    assert _capture_cli(lane, contract) == 0
    store = tmp_path / "store"
    report_path = tmp_path / "publish_report.json"

    # A3b: --recorded-at earlier than the CLOCK RULE value refuses the run.
    rc = _publish_cli(lane, contract, store, report_path, clock=EARLY_RUN_CLOCK)
    assert rc == 1
    out = capsys.readouterr().out
    error_lines = [line for line in out.splitlines() if line.startswith("::error")]
    assert error_lines, out
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
    _install_fake_lineage(monkeypatch)
    assert _capture_cli(lane, contract, clock=MID_RULES_CAPTURE) == 0
    rc = _publish_cli(
        lane, contract, tmp_path / "store", tmp_path / "report.json", clock=MID_RULES_RUN
    )
    assert rc == 1
    out = capsys.readouterr().out
    assert any(
        line.startswith("::error") and "admitted_at_after_recorded_at" in line
        for line in out.splitlines()
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
    _install_fake_lineage(monkeypatch)
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
    _install_fake_lineage(monkeypatch)
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
    _install_fake_lineage(monkeypatch)
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
    _install_fake_lineage(monkeypatch)
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


def test_exclusion_member_capture_failed_is_typed(
    tmp_path, monkeypatch, offline_collector
) -> None:
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    _install_fake_lineage(monkeypatch)
    assert _capture_cli(lane, contract) == 0
    for accession in identity["accessions"]:
        members_dir = (
            lane["archive_root"] / "fif-packages" / identity["cik"] / accession / "members"
        )
        victim = sorted(members_dir.iterdir())[0]
        victim.write_bytes(victim.read_bytes()[:-1])
    report_path = tmp_path / "publish_report.json"
    assert _publish_cli(lane, contract, tmp_path / "store", report_path) == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert [row["reason"] for row in report["excluded"]] == [
        "member_capture_failed:package_bytes_mismatch"
    ]


# ---------------------------------------------------------------------------
# A4: hard failures (rc != 0 + line-start ::error, never swallowed)
# ---------------------------------------------------------------------------


def test_untyped_admission_error_hard_fails(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    _install_fake_lineage(monkeypatch)
    assert _capture_cli(lane, contract) == 0

    def _explode(**_kwargs):
        raise RuntimeError("synthetic admission crash")

    monkeypatch.setattr(producer, "admit_retained_filing_package", _explode)
    rc = _publish_cli(lane, contract, tmp_path / "store", tmp_path / "report.json")
    assert rc == 1
    out = capsys.readouterr().out
    assert any(line.startswith("::error") for line in out.splitlines())


def test_lineage_mint_error_hard_fails(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)

    module = types.ModuleType("engine.fundamental_forensics.production_lineage")

    def mint_production_lineage_evidence(_ledger, _packages, *, system_available_at):
        raise LineageEvidenceError(
            f"synthetic mint refusal below the floor: {system_available_at}"
        )

    module.mint_production_lineage_evidence = mint_production_lineage_evidence
    monkeypatch.setitem(
        sys.modules, "engine.fundamental_forensics.production_lineage", module
    )
    assert _capture_cli(lane, contract) == 0
    rc = _publish_cli(lane, contract, tmp_path / "store", tmp_path / "report.json")
    assert rc == 1
    out = capsys.readouterr().out
    lines = [line for line in out.splitlines() if line.startswith("::error")]
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
    _install_fake_lineage(monkeypatch)
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
    out = capsys.readouterr().out
    assert any(line.startswith("::error") for line in out.splitlines())


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
        out = capsys.readouterr().out
        assert any(
            line.startswith("::error") and "golden_input_refused" in line
            for line in out.splitlines()
        )


def test_golden_schema_manifest_is_refused_at_publish(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    _install_fake_lineage(monkeypatch)
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
    out = capsys.readouterr().out
    assert any(
        line.startswith("::error") and "golden_input_refused" in line
        for line in out.splitlines()
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
    out = capsys.readouterr().out
    assert any(
        line.startswith("::error") for line in out.splitlines()
    )


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
    assert len(incumbent) + len(expected) <= 15


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
    # The S2-p seam is present, lazy, and named: the module is imported at
    # call time (importlib) with the frozen mint signature, never at module
    # import time (the module does not exist at this lane's base).
    assert "engine.fundamental_forensics.production_lineage" in source
    assert "mint_production_lineage_evidence" in source
    assert "importlib" in source


def test_producer_import_loads_no_mint_layer_or_golden_provider() -> None:
    sys.modules.pop("scripts.publish_fif_production_datasets", None)
    import scripts.publish_fif_production_datasets as fresh  # noqa: PLC0415

    assert "engine.fundamental_forensics.production_lineage" not in sys.modules
    golden_attrs = [name for name in dir(fresh) if "GOLDEN" in name.upper()]
    assert golden_attrs == []
    assert not hasattr(fresh, "GoldenAaplFinancialQueryProvider")
    assert not hasattr(fresh, "load_golden_aapl_package")
    assert not hasattr(fresh, "derive_confirmation_receipts")
    assert not hasattr(fresh, "derive_chain_confirmation_receipts")


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
