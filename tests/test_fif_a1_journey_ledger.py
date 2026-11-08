"""FIF A1 journey + refusal ledger tests (hermetic, no network).

The local store fixture is built with the EXISTING publish path over EXISTING
AAPL test fixtures — the same material assembly
``tests/test_fundamental_forensics_production_dataset_store.py`` uses
(``_aapl_packages_material``, lines 343-377: ``admit_golden_aapl_package`` +
``parse_and_convert_golden_packages`` + ``ProductionDatasetMaterial`` +
``publish_production_dataset``), with the fixture inputs COPIED into
``tmp_path`` first so no recorded locator points at the repository.  The
lineage-cause cases reuse the synthetic-fact builder shape of
``tests/test_fundamental_forensics_cross_filing_lineage.py:517-556`` and
``tests/test_fundamental_forensics_multi_filing_lineage.py:80-127``
(``make_raw_fact`` over ``SourceIdentity``/``FactContext``/``FactUnit``) and
call the REAL kernel guards — ``evaluate_confirmation`` and
``classify_filing_chain`` are never mocked.
"""
from __future__ import annotations

import argparse
import errno
import json
import os
import re
import shutil
import subprocess
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SCRIPT = ROOT / "scripts" / "fif_a1_journey_ledger.py"

_AAPL_ENTITY = "ISS:US-XNAS-AAPL"
_AAPL_CIK = "0000320193"
_T_ADMITTED = datetime(2026, 10, 14, tzinfo=timezone.utc)

# Synthetic-chain clocks, copied from the multi-filing lineage test's shape
# (tests/test_fundamental_forensics_multi_filing_lineage.py:65-73).
_CHAIN_ACCEPTED = (
    "2025-10-31T10:00:00Z",
    "2026-01-31T10:00:00Z",
    "2026-07-31T10:00:00Z",
)
_URI_2025 = "http://fasb.org/us-gaap/2025"
_URI_2026 = "http://fasb.org/us-gaap/2026"
_UNLINKED = "unlinked source vintages require an explicit typed revision lineage"


# ---------------------------------------------------------------------------
# Module-scoped local store + report/contract fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def a1_store(tmp_path_factory):
    """A local production-dataset store built by the existing publish path."""
    from engine.fundamental_forensics import production_datasets as PDS
    from engine.fundamental_forensics.financial_intelligence_packet import EntityInput
    from engine.fundamental_forensics.ixbrl_raw_ledger import (
        GOLDEN_AAPL_QUERY_ACCESSIONS,
        parse_and_convert_golden_packages,
    )
    from engine.fundamental_forensics.production_lineage import (
        mint_production_lineage_evidence,
    )
    from engine.fundamental_forensics.query_service import CanonicalEntityBinding
    from engine.fundamental_forensics.statement_graph import (
        GOLDEN_AAPL_FIXTURES,
        admit_golden_aapl_package,
    )

    base = tmp_path_factory.mktemp("a1-store")
    fixture_root = base / "fixture-inputs"
    packages = []
    manifests = {}
    for accession in GOLDEN_AAPL_QUERY_ACCESSIONS:
        source = ROOT / GOLDEN_AAPL_FIXTURES[accession]
        copied = fixture_root / source.name
        shutil.copytree(source, copied)
        package = admit_golden_aapl_package(copied)
        packages.append(package)
        manifests[accession] = package.manifest
    ledger, filing_metadata, _report = parse_and_convert_golden_packages(packages)
    lineage = mint_production_lineage_evidence(
        ledger, tuple(packages), system_available_at=_T_ADMITTED
    )
    material = PDS.ProductionDatasetMaterial(
        binding=CanonicalEntityBinding(
            entity_id=_AAPL_ENTITY,
            cik=_AAPL_CIK,
            ticker="AAPL",
            source_entity_id=_AAPL_CIK,
        ),
        entity=EntityInput(
            entity_id=_AAPL_ENTITY,
            cik=_AAPL_CIK,
            ticker="AAPL",
            name="Apple Inc.",
            identity_basis="sec-cik",
            source_entity_id=_AAPL_CIK,
        ),
        ledger=ledger,
        filing_metadata=filing_metadata,
        registry_payload=PDS.snapshot_core_registry_payload(ROOT),
        admitted_at=_T_ADMITTED,
        packages=tuple(packages),
        lineage_evidence=lineage,
        security_id="SEC:US-XNAS-AAPL",
        listing_key="US-XNAS-AAPL",
    )
    store_dir = base / "store"
    store = PDS.build_production_dataset_store(store_dir)
    publication = PDS.publish_production_dataset(store, material)
    return {
        "base": base,
        "store_dir": store_dir,
        "generation_id": publication.generation_id,
        "manifest_key": publication.manifest_key,
        "accessions": list(GOLDEN_AAPL_QUERY_ACCESSIONS),
        "manifests": manifests,
        "lineage_count": len(lineage),
    }


def _aapl_contract_issuer() -> dict:
    return {
        "ticker": "AAPL",
        "cik": _AAPL_CIK,
        "security_master_binding": {"issuer_id": _AAPL_ENTITY},
        "accessions": [
            {
                "accession": "0000320193-25-000079",
                "form": "10-K",
                "filing_date": "2025-10-31",
                "period_of_report": "2025-09-27",
                "retention_state": "retained_golden_fixture",
            },
            {
                "accession": "0000320193-26-000020",
                "form": "10-Q",
                "filing_date": "2026-07-31",
                "period_of_report": "2026-06-27",
                "retention_state": "retained_golden_fixture",
            },
        ],
    }


def _second_contract_issuer() -> dict:
    """A second synthetic contract issuer, listed in report excluded[]."""
    return {
        "ticker": "SECOND",
        "cik": "0000999999",
        "security_master_binding": {"issuer_id": "ISS:US-XNAS-SECOND"},
        "accessions": [
            {
                "accession": "0000999999-26-000001",
                "form": "10-K",
                "filing_date": "2026-02-02",
                "period_of_report": "2025-12-31",
                "retention_state": "not_retained",
            }
        ],
    }


def _third_contract_issuer() -> dict:
    """A third synthetic contract issuer, in neither report section."""
    return {
        "ticker": "THIRD",
        "cik": "0000888888",
        "security_master_binding": {"issuer_id": "ISS:US-XNAS-THIRD"},
        "accessions": [
            {
                "accession": "0000888888-26-000001",
                "form": "10-Q",
                "filing_date": "2026-05-05",
                "period_of_report": "2026-03-31",
                "retention_state": "not_retained",
            }
        ],
    }


def _contract_document(*, extra_issuers: bool = False) -> dict:
    issuers = [_aapl_contract_issuer()]
    if extra_issuers:
        issuers.append(_second_contract_issuer())
        issuers.append(_third_contract_issuer())
    return {
        "schema": "fundamental_forensics.coverage_contract/v1",
        "contract_id": "a1_test_v1",
        "issuers": issuers,
    }


def _report_document(store, *, generation_id=None, extra_issuers: bool = False) -> dict:
    report = {
        "schema": "fundamental_forensics.fif_production_publish_report/v1",
        "recorded_at": "2026-10-14T00:00:00.000000Z",
        "rule_clocks": {
            "confirmation_rule_available_at": "2026-08-25T00:00:00Z",
            "confirmation_chain_rule_available_at": "2026-10-12T00:00:00Z",
            "registry_available_at": ["2026-08-02T00:00:00Z"],
        },
        "published": [
            {
                "entity_id": _AAPL_ENTITY,
                "ticker": "AAPL",
                "cik": _AAPL_CIK,
                "outcome": "published",
                "clock_basis": "content",
                "generation_id": generation_id or store["generation_id"],
                "manifest_key": store["manifest_key"],
                "admitted_at": "2026-10-14T00:00:00.000000Z",
                "source_recorded_at_floor": "2026-08-23T00:00:00Z",
                "admitted_accessions": store["accessions"],
                "admitted_event_accessions": [],
                "lineage_receipt_count": store["lineage_count"],
            }
        ],
        "excluded": [],
        "coverage": [
            {
                "ticker": "AAPL",
                "cik": _AAPL_CIK,
                "contract_accessions": 2,
                "captured": 2,
                "admitted": 2,
                "served": 2,
                "accessions": [
                    {"accession": a, "captured": True, "admitted": True, "served": True}
                    for a in store["accessions"]
                ],
            }
        ],
    }
    if extra_issuers:
        report["excluded"].append(
            {
                "ticker": "SECOND",
                "cik": "0000999999",
                "reason": "no_retained_package",
                "detail": "nothing was retained for this issuer",
            }
        )
        report["coverage"].append(
            {
                "ticker": "SECOND",
                "cik": "0000999999",
                "contract_accessions": 1,
                "captured": 0,
                "admitted": 0,
                "served": 0,
                "accessions": [
                    {
                        "accession": "0000999999-26-000001",
                        "captured": False,
                        "admitted": False,
                        "served": False,
                        "missing_code": "not_attempted",
                    }
                ],
            }
        )
    return report


def _write_inputs(
    directory: Path,
    report: dict,
    contract: dict | None = None,
    *,
    extra_issuers: bool = False,
):
    directory.mkdir(parents=True, exist_ok=True)
    report_path = directory / "report.json"
    report_path.write_text(json.dumps(report, indent=1), encoding="utf-8")
    contract_path = directory / "contract.json"
    contract_path.write_text(
        json.dumps(
            contract if contract is not None else _contract_document(
                extra_issuers=extra_issuers
            ),
            indent=1,
        ),
        encoding="utf-8",
    )
    return report_path, contract_path


def _run_cli(report_path: Path, contract_path: Path, store_dir: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / "ledger.json"
    out_md = out_dir / "ledger.md"
    process = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--production-report",
            str(report_path),
            "--store-dir",
            str(store_dir),
            "--coverage-file",
            str(contract_path),
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    return process, out_json, out_md


@pytest.fixture(scope="module")
def a1_match_run(a1_store, tmp_path_factory):
    """The baseline bridge-match run (AAPL-only contract, all checks pass)."""
    directory = tmp_path_factory.mktemp("a1-match")
    report_path, contract_path = _write_inputs(directory, _report_document(a1_store))
    process, out_json, out_md = _run_cli(
        report_path, contract_path, a1_store["store_dir"], directory / "out"
    )
    return {
        "process": process,
        "out_json": out_json,
        "out_md": out_md,
        "document": json.loads(out_json.read_text(encoding="utf-8")),
        "report_path": report_path,
        "contract_path": contract_path,
        "directory": directory,
    }


@pytest.fixture(scope="module")
def a1_extra_run(a1_store, tmp_path_factory):
    """The excluded + dropped issuer run (contract adds SECOND and THIRD)."""
    directory = tmp_path_factory.mktemp("a1-extra")
    report_path, contract_path = _write_inputs(
        directory, _report_document(a1_store, extra_issuers=True), extra_issuers=True
    )
    process, out_json, out_md = _run_cli(
        report_path, contract_path, a1_store["store_dir"], directory / "out"
    )
    return {
        "process": process,
        "out_json": out_json,
        "out_md": out_md,
        "document": json.loads(out_json.read_text(encoding="utf-8")),
    }


# ---------------------------------------------------------------------------
# CLI cases
# ---------------------------------------------------------------------------


def test_bridge_match_all_checks_pass_exit_0(a1_match_run):
    run = a1_match_run
    assert run["process"].returncode == 0, run["process"].stderr
    assert run["out_json"].is_file() and run["out_md"].is_file()
    document = run["document"]
    assert document["schema"] == "fif.a1_journey_ledger/v1"
    assert document["all_checks_passed"] is True
    aapl = next(i for i in document["issuers"] if i["ticker"] == "AAPL")
    assert aapl["bridge"]["status"] == "match"
    assert aapl["bridge"]["production_outcome"] == "published"
    assert aapl["bridge"]["production_clock_basis"] == "content"
    for row in aapl["accessions"]:
        assert row["edgar_index_url"] == (
            f"https://www.sec.gov/Archives/edgar/data/320193/"
            f"{row['accession'].replace('-', '')}/{row['accession']}-index.htm"
        )
        assert row["primary_document"]["name"].endswith(".htm")
        assert len(row["primary_document"]["sha256"]) == 64
    assert aapl["statement_counts"]["served"] == 6
    assert aapl["lineage"]["receipts"]["v1_pair"] == 130

    # R1/R4: a clean run proves the kernel, coverage and statement-consistency
    # checks RAN for the published issuer — pass rows are emitted, not skipped.
    check_rows = {c["id"]: c for c in document["checks"]}
    kernel_row = check_rows["kernel_query_engine"]
    assert kernel_row["issuer"] == "AAPL"
    assert kernel_row["status"] == "pass"
    assert re.fullmatch(
        r"production query engine built; \d+ matrix periods queried",
        kernel_row["detail"],
    )
    served_row = check_rows["coverage_served"]
    assert served_row["issuer"] == "AAPL"
    assert served_row["status"] == "pass"
    assert served_row["detail"] == "issuer published by the production run"
    consistency_row = check_rows["statement_refusal_consistency"]
    assert consistency_row["issuer"] == "AAPL"
    assert consistency_row["status"] == "pass"
    assert (
        consistency_row["detail"]
        == "generation and report agree on 0 statement refusals"
    )


def test_bridge_mismatch_reports_fail_and_writes_outputs(a1_store, tmp_path):
    directory = tmp_path / "mismatch"
    report = _report_document(a1_store)
    report["published"][0]["generation_id"] = "ffprods_" + "0" * 64
    report_path, contract_path = _write_inputs(directory, report)
    process, out_json, out_md = _run_cli(
        report_path, contract_path, a1_store["store_dir"], directory / "out"
    )
    assert process.returncode == 1
    assert out_json.is_file() and out_md.is_file()
    document = json.loads(out_json.read_text(encoding="utf-8"))
    assert document["all_checks_passed"] is False
    aapl = next(i for i in document["issuers"] if i["ticker"] == "AAPL")
    assert aapl["bridge"]["status"] == "mismatch"
    failed = {c["id"] for c in document["checks"] if c["status"] == "fail"}
    assert "bridge" in failed


def test_excluded_issuer_carried_verbatim(a1_extra_run):
    document = a1_extra_run["document"]
    second = next(i for i in document["issuers"] if i["ticker"] == "SECOND")
    assert second["bridge"]["status"] == "not_published"
    assert second["bridge"]["exclusion_reason"] == "no_retained_package"
    assert second["bridge"]["exclusion_detail"] == "nothing was retained for this issuer"
    failed = {
        (c["id"], c["issuer"]) for c in document["checks"] if c["status"] == "fail"
    }
    assert ("coverage_served", "SECOND") in failed
    markdown = a1_extra_run["out_md"].read_text(encoding="utf-8")
    assert "| SECOND |" in markdown


def test_dropped_issuer_fails(a1_extra_run):
    document = a1_extra_run["document"]
    third = next(i for i in document["issuers"] if i["ticker"] == "THIRD")
    assert third["bridge"]["status"] is None
    failed = {
        (c["id"], c["issuer"]) for c in document["checks"] if c["status"] == "fail"
    }
    assert ("issuer_dropped", "THIRD") in failed


def test_statement_refusal_carried_with_code_and_message(a1_store, tmp_path):
    directory = tmp_path / "refusal"
    report = _report_document(a1_store)
    report["statement_refusals"] = [
        {
            "ticker": "AAPL",
            "cik": _AAPL_CIK,
            "accession": "0000320193-25-000079",
            "statement_type": "income_statement",
            "code": "displayed_columns_absent",
            "message": "displayed statement columns are absent: Income",
            "pinned": False,
        }
    ]
    report_path, contract_path = _write_inputs(directory, report)
    process, out_json, _out_md = _run_cli(
        report_path, contract_path, a1_store["store_dir"], directory / "out"
    )
    assert process.returncode == 1
    document = json.loads(out_json.read_text(encoding="utf-8"))
    aapl = next(i for i in document["issuers"] if i["ticker"] == "AAPL")
    row = next(
        r
        for r in aapl["statements"]
        if r["accession"] == "0000320193-25-000079"
        and r["statement_type"] == "income_statement"
    )
    assert row["served"] is False
    assert row["refusal"]["report_code"] == "displayed_columns_absent"
    assert (
        row["refusal"]["report_message"]
        == "displayed statement columns are absent: Income"
    )
    failed = {c["id"] for c in document["checks"] if c["status"] == "fail"}
    assert "statement_refusal_consistency" in failed


def test_fixture_path_substitution_fails(a1_store, tmp_path):
    directory = tmp_path / "fixture-sub"
    report = _report_document(a1_store)
    report["published"][0]["admitted_accessions"] = [
        "tests/fixtures/fundamental_forensics/aapl_10k_2025"
    ]
    report_path, contract_path = _write_inputs(directory, report)
    process, out_json, _out_md = _run_cli(
        report_path, contract_path, a1_store["store_dir"], directory / "out"
    )
    assert process.returncode == 1
    document = json.loads(out_json.read_text(encoding="utf-8"))
    check = next(
        c for c in document["checks"] if c["id"] == "no_fixture_substitution"
    )
    assert check["status"] == "fail"
    assert "report published[0]" in check["detail"]


def test_unusable_inputs_exit_2(a1_store, tmp_path):
    directory = tmp_path / "usage"
    report = _report_document(a1_store)
    report["schema"] = "something.else/v9"
    report_path, contract_path = _write_inputs(directory, report)
    process, out_json, _md = _run_cli(
        report_path, contract_path, a1_store["store_dir"], directory / "out"
    )
    assert process.returncode == 2
    assert process.stderr.strip().startswith("fif_a1_journey_ledger:")
    # The usage error is still a ledger: both out paths carry the FAIL row.
    document = json.loads(out_json.read_text(encoding="utf-8"))
    assert document["all_checks_passed"] is False
    assert document["inputs"] == {}
    assert [
        (c["id"], c["issuer"], c["status"]) for c in document["checks"]
    ] == [("harness_input", None, "fail")]

    missing = directory / "missing.json"
    process2 = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--production-report",
            str(missing),
            "--store-dir",
            str(a1_store["store_dir"]),
            "--coverage-file",
            str(contract_path),
            "--out-json",
            str(directory / "o.json"),
            "--out-md",
            str(directory / "o.md"),
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert process2.returncode == 2
    assert "unreadable" in process2.stderr


def test_byte_determinism(a1_store, tmp_path):
    directory = tmp_path / "determinism"
    report_path, contract_path = _write_inputs(directory, _report_document(a1_store))
    _process, out_json_a, out_md_a = _run_cli(
        report_path, contract_path, a1_store["store_dir"], directory / "out-a"
    )
    _process, out_json_b, out_md_b = _run_cli(
        report_path, contract_path, a1_store["store_dir"], directory / "out-b"
    )
    assert out_json_a.read_bytes() == out_json_b.read_bytes()
    assert out_md_a.read_bytes() == out_md_b.read_bytes()
    assert out_json_a.read_bytes().endswith(b"\n")


def test_engine_construction_failure_fails_ledger(
    a1_store, registry, tmp_path, monkeypatch
):
    """One issuer whose generation cannot build the production query engine
    is a FAILED ``kernel_query_engine`` check, never a silent all-clear.

    The real kernel must raise: one ``filing_metadata`` entry for a ledger
    accession gets its ``filed_at`` moved past that accession's fact
    acceptance, past the kernel's filed_at-versus-acceptance guard in
    engine/fundamental_forensics/query.py, which then refuses the engine at
    construction; no ``_build_engine`` stand-in is involved.  The harness
    reports the failure (exit-1 semantics via ``all_checks_passed`` false),
    keeps the carried
    journey codes and the unavailable causes object, renders the coverage
    census as ``unavailable`` instead of a never-computed 0, and resolves the
    journey metric ids so no ``None`` reaches the MD metric column.
    """
    import dataclasses

    import scripts.fif_a1_journey_ledger as ledger_module

    directory = tmp_path / "engine-fail"
    report_path, contract_path = _write_inputs(directory, _report_document(a1_store))
    report = ledger_module._read_json_file(str(report_path), kind="production report")
    contract = ledger_module._read_json_file(str(contract_path), kind="coverage contract")

    real_load = ledger_module.load_query_dataset_payloads
    target_accession = a1_store["accessions"][0]

    def _poison_filed_at(generation):
        payloads = real_load(generation)
        accepted = [
            event.accepted_at
            for event in payloads["ledger"].events
            if event.source.accession == target_accession
            and event.accepted_at is not None
        ]
        assert accepted, "fixture ledger has no accepted_at for the target accession"
        # 10 calendar days is beyond any EDGAR next-business-day roll (at most
        # 5 calendar days), so the kernel refuses under either filed_at bound.
        late_filed_at = max(accepted).date() + timedelta(days=10)
        entry = payloads["filing_metadata"][target_accession]
        if dataclasses.is_dataclass(entry):
            # content_sha256 is re-derived in __post_init__; passing None lets
            # the frozen dataclass recompute it over the moved filed_at.
            # available_at is untouched.
            payloads["filing_metadata"][target_accession] = dataclasses.replace(
                entry, filed_at=late_filed_at, content_sha256=None
            )
        else:
            moved = dict(entry)
            moved["filed_at"] = late_filed_at.isoformat()
            payloads["filing_metadata"][target_accession] = moved
        return payloads

    monkeypatch.setattr(
        ledger_module, "load_query_dataset_payloads", _poison_filed_at
    )

    document = ledger_module.build_ledger(
        report=report,
        contract=contract,
        store_dir=a1_store["store_dir"],
        archive_root=None,
    )

    # R1: the whole-issuer engine failure is a failed check — and the only one.
    assert document["all_checks_passed"] is False
    failed = {
        (c["id"], c["issuer"]) for c in document["checks"] if c["status"] == "fail"
    }
    assert failed == {("kernel_query_engine", "AAPL")}
    kernel_row = next(
        c for c in document["checks"] if c["id"] == "kernel_query_engine"
    )
    assert kernel_row["issuer"] == "AAPL"
    assert kernel_row["status"] == "fail"
    assert kernel_row["detail"].startswith("QueryValidationError")
    assert kernel_row["detail"].startswith(
        "QueryValidationError: filing metadata filed_at follows "
    )
    assert kernel_row["detail"].endswith("source acceptance")

    # R1/R3: the carried journey codes and unavailable causes are unchanged,
    # and every journey row resolves its metric id from the pinned catalog.
    aapl = next(i for i in document["issuers"] if i["ticker"] == "AAPL")
    causes = aapl["lineage"]["refusal_causes"]
    assert causes["status"] == "unavailable"
    assert "histogram" not in causes
    assert causes["reason"] == kernel_row["detail"]
    journeys = aapl["query_journeys"]
    assert journeys
    expected_ids = ledger_module._journey_metric_ids(registry)
    for journey in journeys:
        assert journey["status"] == "refused"
        assert journey["code"].startswith("query_engine_unavailable (")
        assert journey["metric_id"] == expected_ids[journey["metric"]]
        assert journey["metric_id"] is not None

    # R2: no fake 0 census for a histogram that never computed.
    coverage = next(r for r in document["coverage_table"] if r["ticker"] == "AAPL")
    assert coverage["lineage_refusals"] == "unavailable"

    markdown = ledger_module._render_markdown(document)
    assert "| unavailable |" in markdown
    assert "| None |" not in markdown


def test_edgar_index_url_rule():
    from scripts.fif_a1_journey_ledger import edgar_index_url

    assert (
        edgar_index_url("0000320193", "0000320193-25-000079")
        == "https://www.sec.gov/Archives/edgar/data/320193/"
        "000032019325000079/0000320193-25-000079-index.htm"
    )
    assert (
        edgar_index_url("0000018230", "0000018230-26-000008")
        == "https://www.sec.gov/Archives/edgar/data/18230/"
        "000001823026000008/0000018230-26-000008-index.htm"
    )


# ---------------------------------------------------------------------------
# Lineage refusal causes — REAL kernel calls, no mocking
# ---------------------------------------------------------------------------


def _synthetic_fact(*, accession, body, value="359241000000", accepted_at, decimals="-6"):
    """The synthetic occurrence builder used by the cross-filing lineage
    suites (tests/test_fundamental_forensics_cross_filing_lineage.py:517-556,
    tests/test_fundamental_forensics_multi_filing_lineage.py:80-127)."""
    from engine.fundamental_forensics.raw_ledger import (
        FactContext,
        FactUnit,
        SourceIdentity,
        make_raw_fact,
    )

    return make_raw_fact(
        source=SourceIdentity(
            source="sec-edgar",
            entity_id=_AAPL_CIK,
            accession=accession,
            document_id=f"doc-{accession}.htm",
            body_sha256=body,
            source_url="https://www.sec.gov/Archives/example",
        ),
        concept_qname="us-gaap:Assets",
        context=FactContext(
            context_id="ctx",
            entity_scheme="http://www.sec.gov/CIK",
            entity_identifier=_AAPL_CIK,
            instant="2025-09-27",
        ),
        unit=FactUnit("usd", ["iso4217:USD"]),
        raw_token=value,
        parsed_value=value,
        decimals=decimals,
        source_span=(10, 20),
        accepted_at=accepted_at,
        recorded_at="2026-08-23T00:00:00Z",
    )


def _facts_pair(value="359241000000"):
    return [
        _synthetic_fact(
            accession="0001", body="a" * 64, accepted_at=_CHAIN_ACCEPTED[0], value=value
        ),
        _synthetic_fact(
            accession="0002", body="b" * 64, accepted_at=_CHAIN_ACCEPTED[1], value=value
        ),
    ]


def _facts_chain():
    return [
        _synthetic_fact(accession="0001", body="a" * 64, accepted_at=_CHAIN_ACCEPTED[0]),
        _synthetic_fact(accession="0002", body="b" * 64, accepted_at=_CHAIN_ACCEPTED[1]),
        _synthetic_fact(accession="0003", body="c" * 64, accepted_at=_CHAIN_ACCEPTED[2]),
    ]


def _uris_for(facts, year_by_accession):
    return {
        (fact.source.accession, fact.source_occurrence_key or ""): (
            f"http://fasb.org/us-gaap/{year_by_accession[fact.source.accession]}"
        )
        for fact in facts
    }


def _real_kernel_cells(facts, registry):
    """Real query_matrix cells refused with the unlinked-vintages reason."""
    from engine.fundamental_forensics.query import (
        BitemporalMetricQueryEngine,
        PeriodRequest,
        QueryPolicy,
    )
    from engine.fundamental_forensics.raw_ledger import RawFactLedger

    engine = BitemporalMetricQueryEngine(
        RawFactLedger(tuple(facts)),
        registry,
        entities={"AAPL": _AAPL_CIK},
    )
    policy = QueryPolicy(
        selection="latest_known_as_of",
        source_snapshot_at="2026-10-20T00:00:00Z",
        recorded_at="2026-10-20T00:00:00Z",
    )
    matrix = engine.query_matrix(
        tickers=["AAPL"],
        metrics=["total_assets"],
        periods=[PeriodRequest.instant("2025-09-27")],
        policy=policy,
    )
    return list(matrix.cells)


def _classify(facts, cells, uris, archive_available):
    from scripts.fif_a1_lineage_causes import classify_refusal_causes

    event_by_id = {fact.occurrence_id: fact for fact in facts}
    events_by_logical_key = {}
    for fact in facts:
        events_by_logical_key.setdefault(fact.logical_key, []).append(fact)
    return classify_refusal_causes(
        cells=cells,
        event_by_id=event_by_id,
        events_by_logical_key=events_by_logical_key,
        taxonomy_uris=uris,
        archive_available=archive_available,
    )


@pytest.fixture(scope="module")
def registry():
    from engine.fundamental_forensics.financial_intelligence_packet import load_core_registry

    return load_core_registry(ROOT)


def test_cross_taxonomy_pair_from_real_kernel_cells(registry):
    facts = _facts_pair()
    cells = _real_kernel_cells(facts, registry)
    assert len(cells) == 1
    assert cells[0].reason == _UNLINKED
    uris = _uris_for(facts, {"0001": 2025, "0002": 2026})
    result = _classify(facts, cells, uris, True)
    row = result["cells"][0]
    assert row["code"] == "cross_taxonomy_version_confirmation_unavailable"
    assert row["bucket"] == "v1_pair"
    assert row["basis"] == "kernel_guard_11"
    assert row["kernel_code"] == "source_taxonomy_namespace_version_mismatch"
    assert row["accessions"] == ["0001", "0002"]
    assert result["histogram"]["cross_taxonomy_version_confirmation_unavailable"]["v1_pair"] == 1


def test_changed_value_pair_is_restatement(registry):
    facts = [
        _synthetic_fact(
            accession="0001", body="a" * 64, accepted_at=_CHAIN_ACCEPTED[0]
        ),
        _synthetic_fact(
            accession="0002",
            body="b" * 64,
            accepted_at=_CHAIN_ACCEPTED[1],
            value="400000000000",
        ),
    ]
    cells = _real_kernel_cells(facts, registry)
    assert cells[0].reason == _UNLINKED
    uris = _uris_for(facts, {"0001": 2025, "0002": 2026})
    result = _classify(facts, cells, uris, True)
    row = result["cells"][0]
    assert row["code"] == "restatement_requires_revision_lineage"
    assert "changed_value" in row["kernel_codes"]


def test_three_accession_chain_is_v2_unproven(registry):
    from engine.fundamental_forensics.lineage_evidence import classify_filing_chain

    facts = _facts_chain()
    uris = _uris_for(facts, {"0001": 2025, "0002": 2025, "0003": 2026})
    # Assert the chain state the kernel itself returns for this slice.
    classification = classify_filing_chain(facts, original_taxonomy_uris=uris)
    assert classification.state == "unproven"
    assert classification.edge_refusals == (
        None,
        "source_taxonomy_namespace_version_mismatch",
    )
    cells = _real_kernel_cells(facts, registry)
    assert cells[0].reason == _UNLINKED
    result = _classify(facts, cells, uris, True)
    row = result["cells"][0]
    assert row["code"] == "cross_taxonomy_version_confirmation_unavailable"
    assert row["bucket"] == "v2_unproven_chain"
    assert row["basis"] == "kernel_guard_11"
    assert row["accessions"] == ["0001", "0002", "0003"]


def test_pair_without_uris_uses_elimination_basis(registry):
    facts = _facts_pair()
    cells = _real_kernel_cells(facts, registry)
    result = _classify(facts, cells, {}, False)
    row = result["cells"][0]
    assert row["code"] == "cross_taxonomy_version_confirmation_unavailable"
    assert row["bucket"] == "v1_pair"
    assert row["basis"] == "elimination_without_namespace_uris"
    assert result["basis"] == "elimination_without_namespace_uris"


def test_cascade_mapping_over_synthetic_cell_records(registry):
    """A derived cell whose only not-evaluable leaf is a cross-taxonomy cell."""
    from engine.fundamental_forensics.query import CellState
    from scripts.fif_a1_lineage_causes import (
        CODE_CROSS_TAXONOMY,
        UNLINKED_VINTAGES_REASON,
        classify_logical_key,
        classify_refusal_causes,
    )

    facts = _facts_pair()
    uris = _uris_for(facts, {"0001": 2025, "0002": 2026})
    verdict = classify_logical_key(facts, taxonomy_uris=uris, archive_available=True)
    assert verdict["code"] == CODE_CROSS_TAXONOMY

    provenance = types.SimpleNamespace(
        source_occurrence_ids=tuple(fact.occurrence_id for fact in facts)
    )
    leaf_node = types.SimpleNamespace(
        state=CellState.NOT_EVALUABLE,
        reason=UNLINKED_VINTAGES_REASON,
        provenance=provenance,
    )
    derived_cell = types.SimpleNamespace(
        metric_id="gross_margin",
        period=types.SimpleNamespace(
            kind="duration", start="2024-09-29", end="2025-09-27"
        ),
        reason="incompatible_dependencies: total_assets (unlinked source vintages require an explicit typed revision lineage)",
        dependency_nodes=(leaf_node,),
    )
    event_by_id = {fact.occurrence_id: fact for fact in facts}
    events_by_logical_key = {}
    for fact in facts:
        events_by_logical_key.setdefault(fact.logical_key, []).append(fact)
    result = classify_refusal_causes(
        cells=[derived_cell],
        event_by_id=event_by_id,
        events_by_logical_key=events_by_logical_key,
        taxonomy_uris=uris,
        archive_available=True,
    )
    assert len(result["cells"]) == 1
    row = result["cells"][0]
    assert row["metric_id"] == "gross_margin"
    assert row["code"] == CODE_CROSS_TAXONOMY
    assert row["bucket"] == "cascade"
    assert row["cascade"] is True
    assert result["histogram"][CODE_CROSS_TAXONOMY]["cascade"] == 1


# ---------------------------------------------------------------------------
# Precision-consistent refusals — REAL kernel guard 8/9 codes, no mocking
# ---------------------------------------------------------------------------


def _precision_facts():
    """The kernel guard-8 shape: unequal parsed values whose rounding
    intervals still agree (1.23 at decimals 2 vs 1.234 at decimals 3)."""
    return [
        _synthetic_fact(
            accession="0001",
            body="a" * 64,
            accepted_at=_CHAIN_ACCEPTED[0],
            value="1.23",
            decimals="2",
        ),
        _synthetic_fact(
            accession="0002",
            body="b" * 64,
            accepted_at=_CHAIN_ACCEPTED[1],
            value="1.234",
            decimals="3",
        ),
    ]


def test_precision_consistent_pair_is_precision_code():
    import engine.fundamental_forensics.lineage_evidence as lineage_evidence
    from engine.fundamental_forensics.lineage_evidence import (
        REFUSAL_PRECISION_CONSISTENT_UNCONFIRMED,
        evaluate_confirmation,
    )
    from scripts.fif_a1_lineage_causes import classify_logical_key

    facts = _precision_facts()
    parent_group = [facts[0]]
    child_group = [facts[1]]
    # The kernel itself names this refusal before the classifier ever runs.
    assert (
        evaluate_confirmation(
            parent_group, child_group, require_taxonomy_uri=False
        )
        == REFUSAL_PRECISION_CONSISTENT_UNCONFIRMED
    )

    uris = _uris_for(facts, {"0001": 2025, "0002": 2025})
    verdict = classify_logical_key(
        facts, taxonomy_uris=uris, archive_available=True
    )
    assert verdict["code"] == "precision_consistent_unconfirmed"
    assert verdict["bucket"] is None
    assert verdict["kernel_code"] == "precision_consistent_unconfirmed"

    # The code is unchanged without archive URIs (elimination basis).
    eliminated = classify_logical_key(
        facts, taxonomy_uris={}, archive_available=False
    )
    assert eliminated["code"] == "precision_consistent_unconfirmed"

    # CODE_PRECISION is the IMPORTED kernel constant, never a copied literal.
    from scripts.fif_a1_lineage_causes import CODE_PRECISION

    assert CODE_PRECISION == "precision_consistent_unconfirmed"
    assert (
        CODE_PRECISION
        is lineage_evidence.REFUSAL_PRECISION_CONSISTENT_UNCONFIRMED
    )


def test_precision_cell_counts_in_histogram_and_is_not_unclassified(registry):
    from scripts.fif_a1_lineage_causes import UNLINKED_VINTAGES_REASON

    facts = _precision_facts()
    cells = _real_kernel_cells(facts, registry)
    if not (len(cells) == 1 and cells[0].reason == _UNLINKED):
        # The real query path refused with a different reason: fall back to a
        # direct SimpleNamespace cell carrying the unlinked-vintages reason,
        # the same shape as the cascade test's leaf node.
        cells = [
            types.SimpleNamespace(
                metric_id="total_assets",
                period=types.SimpleNamespace(
                    kind="instant", start=None, end="2025-09-27"
                ),
                reason=UNLINKED_VINTAGES_REASON,
                provenance=types.SimpleNamespace(
                    source_occurrence_ids=tuple(
                        fact.occurrence_id for fact in facts
                    )
                ),
                dependency_nodes=(),
            )
        ]
    uris = _uris_for(facts, {"0001": 2025, "0002": 2025})
    result = _classify(facts, cells, uris, True)
    histogram = result["histogram"]
    assert histogram["precision_consistent_unconfirmed"] == 1
    assert histogram["unclassified_lineage_refusal"] == 0
    row = result["cells"][0]
    assert row["code"] == "precision_consistent_unconfirmed"


def test_changed_value_on_another_edge_beats_precision():
    from engine.fundamental_forensics.lineage_evidence import (
        REFUSAL_CHANGED_VALUE,
        REFUSAL_PRECISION_CONSISTENT_UNCONFIRMED,
        evaluate_confirmation,
    )
    from scripts.fif_a1_lineage_causes import CODE_PRECISION, classify_logical_key

    facts = [
        _synthetic_fact(
            accession="0001",
            body="a" * 64,
            accepted_at=_CHAIN_ACCEPTED[0],
            value="1.23",
            decimals="2",
        ),
        _synthetic_fact(
            accession="0002",
            body="b" * 64,
            accepted_at=_CHAIN_ACCEPTED[1],
            value="1.234",
            decimals="3",
        ),
        _synthetic_fact(
            accession="0003",
            body="c" * 64,
            accepted_at=_CHAIN_ACCEPTED[2],
            value="9.876",
            decimals="3",
        ),
    ]
    parent_group = [facts[0]]
    middle_group = [facts[1]]
    child_group = [facts[2]]
    assert (
        evaluate_confirmation(
            parent_group, middle_group, require_taxonomy_uri=False
        )
        == REFUSAL_PRECISION_CONSISTENT_UNCONFIRMED
    )
    assert (
        evaluate_confirmation(
            middle_group, child_group, require_taxonomy_uri=False
        )
        == REFUSAL_CHANGED_VALUE
    )

    uris = _uris_for(facts, {"0001": 2025, "0002": 2025, "0003": 2025})
    verdict = classify_logical_key(
        facts, taxonomy_uris=uris, archive_available=True
    )
    assert verdict["code"] == "restatement_requires_revision_lineage"
    without_archive = classify_logical_key(
        facts, taxonomy_uris={}, archive_available=False
    )
    assert without_archive["code"] == "restatement_requires_revision_lineage"
    assert CODE_PRECISION in verdict["kernel_codes"]
    assert REFUSAL_CHANGED_VALUE in verdict["kernel_codes"]


def test_precision_leaf_is_not_cascade():
    from engine.fundamental_forensics.query import CellState
    from scripts.fif_a1_lineage_causes import (
        BUCKET_CASCADE,
        CODE_CROSS_TAXONOMY,
        UNLINKED_VINTAGES_REASON,
        classify_logical_key,
        classify_refusal_causes,
    )

    facts = _precision_facts()
    uris = _uris_for(facts, {"0001": 2025, "0002": 2025})
    verdict = classify_logical_key(
        facts, taxonomy_uris=uris, archive_available=True
    )
    # The precision leaf is NOT a cross-taxonomy cell, so it can never
    # satisfy the cascade's all-cross-taxonomy leaf test.
    assert verdict["code"] != CODE_CROSS_TAXONOMY

    provenance = types.SimpleNamespace(
        source_occurrence_ids=tuple(fact.occurrence_id for fact in facts)
    )
    leaf_node = types.SimpleNamespace(
        state=CellState.NOT_EVALUABLE,
        reason=UNLINKED_VINTAGES_REASON,
        provenance=provenance,
    )
    derived_cell = types.SimpleNamespace(
        metric_id="gross_margin",
        period=types.SimpleNamespace(
            kind="duration", start="2024-09-29", end="2025-09-27"
        ),
        reason="incompatible_dependencies: total_assets (unlinked source vintages require an explicit typed revision lineage)",
        dependency_nodes=(leaf_node,),
    )
    event_by_id = {fact.occurrence_id: fact for fact in facts}
    events_by_logical_key = {}
    for fact in facts:
        events_by_logical_key.setdefault(fact.logical_key, []).append(fact)
    result = classify_refusal_causes(
        cells=[derived_cell],
        event_by_id=event_by_id,
        events_by_logical_key=events_by_logical_key,
        taxonomy_uris=uris,
        archive_available=True,
    )
    assert result["cells"] == []
    assert result["histogram"][CODE_CROSS_TAXONOMY][BUCKET_CASCADE] == 0


# ---------------------------------------------------------------------------
# B1: the harness engine is built exactly as production builds it (r7)
# ---------------------------------------------------------------------------


# Clocks mirroring _make_request in
# tests/test_fundamental_forensics_financial_query_service.py — the harness
# policy and the production request body carry the SAME clocks.
_FIP1_POLICY = {
    "selection": "latest_known_as_of",
    "source_snapshot_at": "2024-12-31T23:59:59Z",
    "recorded_at": "2026-08-03T12:00:00Z",
}
_FIP1_PERIOD = {
    "kind": "duration",
    "start": "2023-01-01",
    "end": "2023-12-31",
    "label": "FY2023",
}


def _fip1_dataset():
    from engine.fundamental_forensics.query_service import fip1_fixture_dataset

    return fip1_fixture_dataset(ROOT)


def _fip1_payloads(dataset):
    """The payload mapping _build_engine reads, straight from the dataset."""
    return {
        "ledger": dataset.ledger,
        "registry": dataset.registry,
        "filing_metadata": dataset.filing_metadata,
        "lineage_evidence": (),
    }


def _fip1_request_body(entity_id: str) -> bytes:
    """The production request body, built exactly like the service test's
    ``_make_request`` (same schema, clocks, metric and period)."""
    obj = {
        "schema": "fundamental_forensics.financial_query_request/v1",
        "entity_id": entity_id,
        "policy": dict(_FIP1_POLICY),
        "metric_ids": ["gross_profit"],
        "periods": [dict(_FIP1_PERIOD)],
    }
    return json.dumps(obj, separators=(",", ":")).encode("utf-8")


def _fip1_production_root_node(issuer_sic_resolver):
    """The production receipt's root node for the gross_profit FY2023 cell."""
    from engine.fundamental_forensics.query_service import execute_financial_query

    dataset = _fip1_dataset()

    class _Provider:
        def resolve(self, entity_id: str):
            assert entity_id == dataset.binding.entity_id
            return dataset

    result = execute_financial_query(
        body=_fip1_request_body(dataset.binding.entity_id),
        provider=_Provider(),
        issuer_sic_resolver=issuer_sic_resolver,
    )
    receipt = result.envelope["receipt"]
    root_ids = set(receipt["root_cell_ids"])
    nodes = [
        node
        for node in receipt["nodes"]
        if node["cell_id"] in root_ids and node.get("metric_id") == "gross_profit"
    ]
    assert len(nodes) == 1, nodes
    return nodes[0]


def _fip1_harness_cell(issuer_sic_resolver=None):
    """The harness gross_profit FY2023 cell from the SAME payloads."""
    import scripts.fif_a1_journey_ledger as ledger_module
    from engine.fundamental_forensics.query import PeriodRequest, QueryPolicy

    dataset = _fip1_dataset()
    kwargs = (
        {} if issuer_sic_resolver is None else {"issuer_sic_resolver": issuer_sic_resolver}
    )
    engine = ledger_module._build_engine(
        _fip1_payloads(dataset),
        dataset.binding.ticker,
        dataset.binding.source_entity_id,
        **kwargs,
    )
    policy = QueryPolicy(
        selection=_FIP1_POLICY["selection"],
        source_snapshot_at=_FIP1_POLICY["source_snapshot_at"],
        recorded_at=_FIP1_POLICY["recorded_at"],
    )
    matrix = engine.query_matrix(
        tickers=[dataset.binding.ticker],
        metrics=["gross_profit"],
        periods=[
            PeriodRequest.duration(_FIP1_PERIOD["start"], _FIP1_PERIOD["end"])
        ],
        policy=policy,
    )
    cells = list(matrix.cells)
    assert len(cells) == 1, cells
    return cells[0]


def test_t_b1a_bank_sic_parity_not_applicable():
    """T-B1a: SIC 6021 on BOTH sides — not_applicable_for_issuer_class."""
    resolver = lambda cik: "6021"  # noqa: E731 - the service tests use the same shape
    cell = _fip1_harness_cell(resolver)
    node = _fip1_production_root_node(resolver)
    assert cell.state.value == "not_applicable"
    assert cell.reason == "not_applicable_for_issuer_class"
    assert node["state"] == "not_applicable"
    assert node["reason"] == "not_applicable_for_issuer_class"


def test_t_b1b_non_bank_sic_parity_value():
    """T-B1b: SIC 3571 on BOTH sides — the same served value."""
    from decimal import Decimal

    resolver = lambda cik: "3571"  # noqa: E731
    cell = _fip1_harness_cell(resolver)
    node = _fip1_production_root_node(resolver)
    assert cell.state.value == node["state"] == "value"
    assert Decimal(str(cell.value)) == Decimal(str(node["value"]))


def test_t_b1c_default_path_parity_guard():
    """T-B1c (guard): no resolver on EITHER side — the production default
    resolution (the shipped coverage contracts) produces the same state and
    reason on both sides."""
    cell = _fip1_harness_cell()
    node = _fip1_production_root_node(None)
    assert cell.state.value == node["state"]
    assert cell.reason == node["reason"]


def test_t_b1d_default_resolution_resolved_at_call_time(monkeypatch):
    """T-B1d: the production default is looked up at CALL time — a monkeypatch
    of ``scripts.fif_a1_journey_ledger.resolve_issuer_sic`` takes effect on a
    ``_build_engine`` call that passes no resolver."""
    import scripts.fif_a1_journey_ledger as ledger_module

    monkeypatch.setattr(ledger_module, "resolve_issuer_sic", lambda cik, **kw: "6021")
    cell = _fip1_harness_cell()
    assert cell.state.value == "not_applicable"
    assert cell.reason == "not_applicable_for_issuer_class"


# ---------------------------------------------------------------------------
# r7 in-process build_ledger cases: real kernel, real generation store
# ---------------------------------------------------------------------------


def _build_in_process(a1_store, tmp_path, report=None, *, extra_issuers=False, contract=None):
    """Write inputs, read them back, and run build_ledger in-process so the
    caller's monkeypatches apply (the pattern of
    ``test_engine_construction_failure_fails_ledger``)."""
    import scripts.fif_a1_journey_ledger as ledger_module

    directory = tmp_path / "in-process"
    report_path, contract_path = _write_inputs(
        directory,
        report if report is not None else _report_document(a1_store, extra_issuers=extra_issuers),
        contract=contract,
        extra_issuers=extra_issuers,
    )
    report_document = ledger_module._read_json_file(str(report_path), kind="production report")
    contract_document = ledger_module._read_json_file(
        str(contract_path), kind="coverage contract"
    )
    return ledger_module.build_ledger(
        report=report_document,
        contract=contract_document,
        store_dir=a1_store["store_dir"],
        archive_root=None,
    )


def _derived_cell_with_leaves(*leaves):
    """A derived receipt cell refused with the incompatible-dependencies
    reason, carrying the given dependency nodes (the SimpleNamespace shape of
    ``test_cascade_mapping_over_synthetic_cell_records``)."""
    return types.SimpleNamespace(
        metric_id="gross_margin",
        period=types.SimpleNamespace(kind="duration", start="2024-09-29", end="2025-09-27"),
        reason=(
            "incompatible_dependencies: gross_margin ("
            + _UNLINKED
            + ")"
        ),
        dependency_nodes=tuple(leaves),
    )


# ---------------------------------------------------------------------------
# M1: strict cascade — mixed leaf sets become mixed_leaf_causes
# ---------------------------------------------------------------------------


def test_t_m1a_mixed_leaf_set_is_mixed_leaf_causes(registry):
    """T-M1a: one cross-taxonomy v1_pair leaf plus one issuer_class_unknown
    leaf is a mixed_leaf_causes row — never a cascade."""
    from engine.fundamental_forensics.query import CellState
    from scripts.fif_a1_lineage_causes import (
        BUCKET_CASCADE,
        CODE_CROSS_TAXONOMY,
        CODE_MIXED_LEAF_CAUSES,
        UNLINKED_VINTAGES_REASON,
        classify_logical_key,
    )

    facts = _facts_pair()
    uris = _uris_for(facts, {"0001": 2025, "0002": 2026})
    verdict = classify_logical_key(facts, taxonomy_uris=uris, archive_available=True)
    assert verdict["code"] == CODE_CROSS_TAXONOMY

    cross_leaf = types.SimpleNamespace(
        state=CellState.NOT_EVALUABLE,
        reason=UNLINKED_VINTAGES_REASON,
        provenance=types.SimpleNamespace(
            source_occurrence_ids=tuple(fact.occurrence_id for fact in facts)
        ),
    )
    other_leaf = types.SimpleNamespace(
        state=CellState.NOT_EVALUABLE,
        reason="issuer_class_unknown",
        provenance=types.SimpleNamespace(source_occurrence_ids=()),
    )
    result = _classify(facts, [_derived_cell_with_leaves(cross_leaf, other_leaf)], uris, True)
    assert len(result["cells"]) == 1
    row = result["cells"][0]
    assert row["code"] == CODE_MIXED_LEAF_CAUSES
    assert row["cascade"] is False
    assert row["bucket"] is None
    assert row["leaf_reasons"] == ["issuer_class_unknown"]
    assert row["accessions"] == ["0001", "0002"]
    assert result["histogram"][CODE_MIXED_LEAF_CAUSES] == 1
    assert result["histogram"][CODE_CROSS_TAXONOMY][BUCKET_CASCADE] == 0


def test_t_m1b_intermediate_derived_node_never_blocks_a_cascade(registry):
    """T-M1b (guard): an intermediate derived node (non-empty
    dependency_cell_ids) is not a leaf — an all-cross LEAF set still cascades."""
    from engine.fundamental_forensics.query import CellState
    from scripts.fif_a1_lineage_causes import (
        CODE_CROSS_TAXONOMY,
        INCOMPATIBLE_DEPENDENCIES_PREFIX,
        UNLINKED_VINTAGES_REASON,
    )

    facts = _facts_pair()
    uris = _uris_for(facts, {"0001": 2025, "0002": 2026})
    cross_leaf = types.SimpleNamespace(
        state=CellState.NOT_EVALUABLE,
        reason=UNLINKED_VINTAGES_REASON,
        provenance=types.SimpleNamespace(
            source_occurrence_ids=tuple(fact.occurrence_id for fact in facts)
        ),
    )
    intermediate_node = types.SimpleNamespace(
        state=CellState.NOT_EVALUABLE,
        reason=f"{INCOMPATIBLE_DEPENDENCIES_PREFIX}x ({UNLINKED_VINTAGES_REASON})",
        provenance=types.SimpleNamespace(
            source_occurrence_ids=(), dependency_cell_ids=("x",)
        ),
    )
    result = _classify(
        facts,
        [_derived_cell_with_leaves(cross_leaf, intermediate_node)],
        uris,
        True,
    )
    assert len(result["cells"]) == 1
    row = result["cells"][0]
    assert row["code"] == CODE_CROSS_TAXONOMY
    assert row["bucket"] == "cascade"
    assert row["cascade"] is True


# ---------------------------------------------------------------------------
# M2: every silent skip becomes a FAIL row
# ---------------------------------------------------------------------------


def test_t_m2a_unreadable_statement_index_is_a_fail_row(a1_store, tmp_path, monkeypatch):
    """T-M2a: a statement-packages index that cannot be decoded is a FAILED
    check, never a silent empty index."""
    import scripts.fif_a1_journey_ledger as ledger_module

    def _refuse(_generation):
        raise ValueError("index bytes cannot be decoded")

    monkeypatch.setattr(ledger_module, "_statement_index", _refuse)
    document = _build_in_process(a1_store, tmp_path)
    row = next(c for c in document["checks"] if c["id"] == "statement_index_unreadable")
    assert row["issuer"] == "AAPL"
    assert row["status"] == "fail"
    assert row["detail"] == "statement packages index cannot be decoded (ValueError)"
    assert document["all_checks_passed"] is False


def test_t_m2b_served_accession_absent_from_index_is_a_fail_row(
    a1_store, tmp_path, monkeypatch
):
    """T-M2b: a served accession missing from the statement index is a FAILED
    check, never a silent continue."""
    import scripts.fif_a1_journey_ledger as ledger_module

    real_index = ledger_module._statement_index
    dropped = a1_store["accessions"][0]

    def _drop_first(generation):
        index = real_index(generation)
        index.pop(dropped, None)
        return index

    monkeypatch.setattr(ledger_module, "_statement_index", _drop_first)
    document = _build_in_process(a1_store, tmp_path)
    row = next(
        c for c in document["checks"] if c["id"] == "served_accession_unindexed"
    )
    assert row["issuer"] == "AAPL"
    assert row["status"] == "fail"
    assert row["detail"].startswith(
        "served accessions absent from the statement packages index: "
    )
    assert dropped in row["detail"]


def test_t_m2c_unreadable_statement_trees_are_a_fail_row(a1_store, tmp_path, monkeypatch):
    """T-M2c: trees that refuse with ProductionDatasetError are a FAILED
    check naming the accession and the error type."""
    import scripts.fif_a1_journey_ledger as ledger_module

    real_trees = ledger_module.statement_trees_from_role_payload
    target = a1_store["accessions"][0]

    def _refuse(payload, accession):
        if accession == target:
            raise ledger_module.ProductionDatasetError("trees cannot be decoded")
        return real_trees(payload, accession)

    monkeypatch.setattr(ledger_module, "statement_trees_from_role_payload", _refuse)
    document = _build_in_process(a1_store, tmp_path)
    row = next(
        c for c in document["checks"] if c["id"] == "statement_trees_unreadable"
    )
    assert row["issuer"] == "AAPL"
    assert row["status"] == "fail"
    assert f"{target} (ProductionDatasetError)" in row["detail"]


def test_t_m2d_archive_with_empty_admitted_set_never_reports_a_match(
    a1_store, tmp_path, monkeypatch
):
    """T-M2d: an empty admitted set refuses BEFORE any archive read — a match
    over zero packages would be vacuous."""
    import scripts.fif_a1_journey_ledger as ledger_module

    monkeypatch.setattr(ledger_module, "read_retained_fif_packages", lambda *a, **k: [])
    monkeypatch.setattr(
        ledger_module, "admitted_concept_namespace_uris", lambda *a, **k: {}
    )
    checks = ledger_module._Checks()
    uris, available = ledger_module._archive_taxonomy_uris(
        archive_root=tmp_path,
        cik=_AAPL_CIK,
        admitted_accessions=[],
        statement_index={},
        ticker="AAPL",
        checks=checks,
    )
    assert uris == {}
    assert available is False
    assert [(row["id"], row["status"], row["detail"]) for row in checks.rows] == [
        (
            "archive_package_mismatch",
            "fail",
            "no admitted accession to verify against the retained archive",
        )
    ]


def test_t_m2e_published_issuer_without_coverage_row_fails(a1_store, tmp_path):
    """T-M2e: a published issuer with no coverage[] row is a FAILED check, and
    its coverage census is "unavailable" — never a fabricated 0."""
    report = _report_document(a1_store)
    report["coverage"] = []
    document = _build_in_process(a1_store, tmp_path, report=report)
    row = next(c for c in document["checks"] if c["id"] == "coverage_row_missing")
    assert row["issuer"] == "AAPL"
    assert row["status"] == "fail"
    assert row["detail"] == "published issuer has no coverage[] row in the production report"
    coverage = next(r for r in document["coverage_table"] if r["ticker"] == "AAPL")
    assert coverage["captured"] == "unavailable"


def test_t_m2f_unrecorded_primary_document_is_a_fail_row(a1_store, tmp_path, monkeypatch):
    """T-M2f: a served accession without a recorded primary document is a
    FAILED check, never a silent hole."""
    import scripts.fif_a1_journey_ledger as ledger_module

    real_index = ledger_module._statement_index
    target = a1_store["accessions"][0]

    def _blank_primary(generation):
        index = real_index(generation)
        row = index.get(target)
        if row is not None:
            row["members"] = [
                member
                for member in (row.get("members") or [])
                if not (isinstance(member, dict) and member.get("role") == "primary")
            ]
        return index

    monkeypatch.setattr(ledger_module, "_statement_index", _blank_primary)
    document = _build_in_process(a1_store, tmp_path)
    row = next(
        c for c in document["checks"] if c["id"] == "primary_document_recorded"
    )
    assert row["issuer"] == "AAPL"
    assert row["status"] == "fail"
    assert row["detail"].startswith(
        "served accessions without a recorded primary document: "
    )
    assert target in row["detail"]


def test_t_m2g_unaccounted_statement_type_is_a_fail_row(a1_store, tmp_path, monkeypatch):
    """T-M2g: a served type that is neither served nor refused anywhere is a
    FAILED check."""
    import scripts.fif_a1_journey_ledger as ledger_module

    real_trees = ledger_module.statement_trees_from_role_payload
    target = a1_store["accessions"][0]

    def _drop_cash_flow(payload, accession):
        trees = real_trees(payload, accession)
        if accession == target:
            trees["statements"] = [
                statement
                for statement in trees.get("statements") or []
                if statement.get("statement_type") != "cash_flow"
            ]
        return trees

    monkeypatch.setattr(ledger_module, "statement_trees_from_role_payload", _drop_cash_flow)
    document = _build_in_process(a1_store, tmp_path)
    row = next(
        c for c in document["checks"] if c["id"] == "statement_types_accounted"
    )
    assert row["issuer"] == "AAPL"
    assert row["status"] == "fail"
    assert row["detail"].startswith("statement types neither served nor refused: ")
    assert f"{target} cash_flow" in row["detail"]


def test_t_m2h_baseline_records_primary_documents_and_statement_types(a1_match_run):
    """T-M2h (guard): the clean baseline run carries PASS rows for both new
    fail-closed statement checks."""
    document = a1_match_run["document"]
    assert document["all_checks_passed"] is True
    for check_id in ("primary_document_recorded", "statement_types_accounted"):
        row = next(c for c in document["checks"] if c["id"] == check_id)
        assert row["issuer"] == "AAPL"
        assert row["status"] == "pass"


# ---------------------------------------------------------------------------
# M3: an empty universe and the unlinked total are never a fake 0
# ---------------------------------------------------------------------------


def test_t_m3a_empty_period_universe_is_a_kernel_failure(a1_store, tmp_path, monkeypatch):
    """T-M3a: an empty governed universe refuses the kernel half — the FAILED
    kernel_query_engine row, a None unlinked total and an "unavailable" census."""
    import scripts.fif_a1_journey_ledger as ledger_module

    monkeypatch.setattr(ledger_module, "_period_universe", lambda ledger, registry: [])
    document = _build_in_process(a1_store, tmp_path)
    row = next(c for c in document["checks"] if c["id"] == "kernel_query_engine")
    assert row["issuer"] == "AAPL"
    assert row["status"] == "fail"
    assert "period universe is empty" in row["detail"]
    aapl = next(i for i in document["issuers"] if i["ticker"] == "AAPL")
    causes = aapl["lineage"]["refusal_causes"]
    assert causes["total_unlinked_cells"] is None
    coverage = next(r for r in document["coverage_table"] if r["ticker"] == "AAPL")
    assert coverage["lineage_refusals"] == "unavailable"


def test_t_m3b_lineage_refusals_total_requires_a_real_int():
    """T-M3b: the census total is "unavailable" unless it is a real int."""
    import scripts.fif_a1_journey_ledger as ledger_module

    assert ledger_module._lineage_refusals_total({"histogram": {}}) == "unavailable"
    assert (
        ledger_module._lineage_refusals_total(
            {"histogram": {}, "total_unlinked_cells": None}
        )
        == "unavailable"
    )
    assert (
        ledger_module._lineage_refusals_total(
            {"histogram": {}, "total_unlinked_cells": True}
        )
        == "unavailable"
    )
    assert (
        ledger_module._lineage_refusals_total(
            {"histogram": {}, "total_unlinked_cells": 7}
        )
        == 7
    )


# ---------------------------------------------------------------------------
# m-fixtures: per-issuer census, clock pairs, harness errors, journey periods
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_count", [None, "130", True])
def test_t_m1_bad_report_lineage_receipt_count_fails(a1_store, tmp_path, bad_count):
    """T-m1: a missing, non-integer or boolean lineage_receipt_count is a
    FAILED lineage_count row — the comparison is never silently skipped."""
    report = _report_document(a1_store)
    report["published"][0]["lineage_receipt_count"] = bad_count
    document = _build_in_process(a1_store, tmp_path, report=report)
    row = next(c for c in document["checks"] if c["id"] == "lineage_count")
    assert row["issuer"] == "AAPL"
    assert row["status"] == "fail"
    assert row["detail"] == "report lineage_receipt_count is missing or not an integer"


def test_t_m2a_unlawful_clock_pair_fails_no_fixture_substitution(a1_store, tmp_path):
    """T-m2a: ("published", "latest_unchanged") is outside the publisher's own
    pairing invariant — the AAPL row fails."""
    report = _report_document(a1_store)
    report["published"][0]["clock_basis"] = "latest_unchanged"
    document = _build_in_process(a1_store, tmp_path, report=report)
    row = next(
        c
        for c in document["checks"]
        if c["id"] == "no_fixture_substitution" and c["issuer"] == "AAPL"
    )
    assert row["status"] == "fail"
    assert "latest_unchanged" in row["detail"]


def test_t_m2b_lawful_pairs_equal_publisher_invariant():
    """T-m2b (guard): the harness pair set IS the publisher's own invariant."""
    import scripts.publish_fif_production_datasets as producer

    from scripts.fif_a1_journey_ledger import LAWFUL_OUTCOME_CLOCK_PAIRS

    assert (
        LAWFUL_OUTCOME_CLOCK_PAIRS == producer._IssuerPlan._VALID_OUTCOME_CLOCK_BASIS
    )


def test_t_m2c_baseline_fixture_and_shape_rows_pass(a1_match_run):
    """T-m2c (guard): the baseline run carries a PASS no_fixture_substitution
    row for AAPL and a PASS report-shape row."""
    document = a1_match_run["document"]
    row = next(c for c in document["checks"] if c["id"] == "no_fixture_substitution")
    assert row["issuer"] == "AAPL"
    assert row["status"] == "pass"
    assert (
        row["detail"]
        == "no tests/fixtures locator; production provider mode and clock basis lawful"
    )
    shape = next(c for c in document["checks"] if c["id"] == "production_report_shape")
    assert shape["issuer"] is None
    assert shape["status"] == "pass"


def test_t_m3a_usage_error_overwrites_stale_outputs(a1_store, tmp_path):
    """T-m3a: stale out files are unlinked first, then the usage error writes
    the harness_input FAIL ledger over them (exit 2)."""
    directory = tmp_path / "stale"
    report = _report_document(a1_store)
    report["schema"] = "something.else/v9"
    report_path, contract_path = _write_inputs(directory, report)
    out_dir = directory / "out"
    out_dir.mkdir(parents=True)
    (out_dir / "ledger.json").write_text("STALE JSON", encoding="utf-8")
    (out_dir / "ledger.md").write_text("STALE MD", encoding="utf-8")
    process, out_json, out_md = _run_cli(
        report_path, contract_path, a1_store["store_dir"], out_dir
    )
    assert process.returncode == 2
    document = json.loads(out_json.read_text(encoding="utf-8"))
    assert document["schema"] == "fif.a1_journey_ledger/v1"
    assert document["inputs"] == {}
    assert document["issuers"] == []
    assert document["all_checks_passed"] is False
    assert [
        (c["id"], c["issuer"], c["status"]) for c in document["checks"]
    ] == [("harness_input", None, "fail")]
    assert "STALE" not in out_md.read_text(encoding="utf-8")


def test_t_m3b_internal_error_writes_fail_ledger_exit_3(a1_store, tmp_path, monkeypatch):
    """T-m3b: an internal error writes the harness_internal_error FAIL ledger
    to both out paths and exits 3 — never a traceback."""
    import scripts.fif_a1_journey_ledger as ledger_module

    directory = tmp_path / "internal"
    report_path, contract_path = _write_inputs(directory, _report_document(a1_store))

    def _explode(**_kwargs):
        raise RuntimeError("synthetic internal failure")

    monkeypatch.setattr(ledger_module, "build_ledger", _explode)
    exit_code = ledger_module.main(
        [
            "--production-report",
            str(report_path),
            "--store-dir",
            str(a1_store["store_dir"]),
            "--coverage-file",
            str(contract_path),
            "--out-json",
            str(directory / "o.json"),
            "--out-md",
            str(directory / "o.md"),
        ]
    )
    assert exit_code == 3
    document = json.loads((directory / "o.json").read_text(encoding="utf-8"))
    assert document["inputs"] == {}
    assert document["all_checks_passed"] is False
    assert [
        (c["id"], c["issuer"], c["status"]) for c in document["checks"]
    ] == [("harness_internal_error", None, "fail")]
    assert document["checks"][0]["detail"].startswith(
        "RuntimeError: synthetic internal failure"
    )
    assert (directory / "o.md").read_text(encoding="utf-8").strip()


def test_t_m3c_malformed_contract_issuer_is_a_fail_row_not_a_crash(a1_store, tmp_path):
    """T-m3c: a contract issuer with a non-digit cik is a FAILED row and a
    skipped issuer — the run continues, AAPL is still processed, no traceback."""
    directory = tmp_path / "malformed"
    contract = _contract_document()
    contract["issuers"].append(
        {
            "ticker": "BAD",
            "cik": "ABC",
            "security_master_binding": {"issuer_id": "ISS:US-XNAS-BAD"},
            "accessions": [],
        }
    )
    report_path, contract_path = _write_inputs(
        directory, _report_document(a1_store), contract=contract
    )
    process, out_json, _out_md = _run_cli(
        report_path, contract_path, a1_store["store_dir"], directory / "out"
    )
    assert process.returncode == 1
    assert "Traceback" not in process.stderr
    document = json.loads(out_json.read_text(encoding="utf-8"))
    row = next(c for c in document["checks"] if c["id"] == "contract_issuer_malformed")
    assert row["issuer"] == "BAD"
    assert row["status"] == "fail"
    assert "cik" in row["detail"]
    assert any(i["ticker"] == "AAPL" for i in document["issuers"])
    assert all(i["ticker"] != "BAD" for i in document["issuers"])


def test_t_m4_unavailable_census_markers(a1_extra_run):
    """T-m4: a section that never ran is "unavailable" in the coverage table —
    never a fabricated 0."""
    table = {r["ticker"]: r for r in a1_extra_run["document"]["coverage_table"]}
    assert table["SECOND"]["statements_served"] == "unavailable"
    assert table["SECOND"]["lineage_receipts"] == "unavailable"
    assert table["THIRD"]["captured"] == "unavailable"
    assert table["AAPL"]["captured"] == 2


def test_t_m5_annual_pick_is_longest_duration_at_latest_end(registry):
    """T-m5: the annual journey pick is the LONGEST duration at the latest end
    (the fiscal year, not a same-end quarter); quarterly stays the shortest."""
    import scripts.fif_a1_journey_ledger as ledger_module
    from engine.fundamental_forensics.query import PeriodRequest

    universe = [
        PeriodRequest.duration("2023-10-01", "2024-09-28"),
        PeriodRequest.duration("2024-06-30", "2024-09-28"),
        PeriodRequest.duration("2024-03-31", "2024-06-29"),
    ]
    metric_id = ledger_module._journey_metric_ids(registry)["revenue"]

    scopes = ledger_module._journey_periods(
        metric_id, registry, universe, {"2024-09-28"}, {"2024-06-29"}
    )
    assert (str(scopes["annual"].start), str(scopes["annual"].end)) == (
        "2023-10-01",
        "2024-09-28",
    )
    assert (str(scopes["quarterly"].start), str(scopes["quarterly"].end)) == (
        "2024-03-31",
        "2024-06-29",
    )

    # Fallback path (no statement packages): same annual rule; quarterly picks
    # the latest-end 3-month period.
    fallback = ledger_module._journey_periods(metric_id, registry, universe, set(), set())
    assert (str(fallback["annual"].start), str(fallback["annual"].end)) == (
        "2023-10-01",
        "2024-09-28",
    )
    assert (str(fallback["quarterly"].start), str(fallback["quarterly"].end)) == (
        "2024-06-30",
        "2024-09-28",
    )


def test_t_m6a_publish_exclusion_conflict_fails(a1_store, tmp_path):
    """T-m6a: one cik in both published[] and excluded[] is a FAILED row."""
    report = _report_document(a1_store)
    report["excluded"].append(
        {
            "ticker": "AAPL",
            "cik": _AAPL_CIK,
            "reason": "duplicate",
            "detail": "present in both sections",
        }
    )
    document = _build_in_process(a1_store, tmp_path, report=report)
    row = next(
        c for c in document["checks"] if c["id"] == "publish_exclusion_conflict"
    )
    assert row["issuer"] == "AAPL"
    assert row["status"] == "fail"
    assert _AAPL_CIK in row["detail"]


def test_t_m6b_report_cik_outside_contract_fails(a1_store, tmp_path):
    """T-m6b: a report row whose cik is outside the contract is a FAILED row
    naming the cik and its sections."""
    report = _report_document(a1_store)
    report["coverage"].append(
        {
            "ticker": "OUTSIDER",
            "cik": "0000000001",
            "captured": 0,
            "admitted": 0,
            "served": 0,
            "accessions": [],
        }
    )
    document = _build_in_process(a1_store, tmp_path, report=report)
    row = next(
        c for c in document["checks"] if c["id"] == "report_issuer_outside_contract"
    )
    assert row["issuer"] is None
    assert row["status"] == "fail"
    assert "0000000001" in row["detail"]
    assert "coverage" in row["detail"]


def test_t_m6c_reported_commit_failure_beats_issuer_dropped(a1_store, tmp_path):
    """T-m6c: a contract issuer absent from both sections is named by the
    report's failed[] object — publish_commit_failed, not issuer_dropped."""
    report = _report_document(a1_store, extra_issuers=True)
    report["failed"] = {
        "cik": "0000888888",
        "ticker": "THIRD",
        "code": "commit_refused",
        "error": "the publish commit refused",
    }
    document = _build_in_process(a1_store, tmp_path, report=report, extra_issuers=True)
    failed = {
        (c["id"], c["issuer"]) for c in document["checks"] if c["status"] == "fail"
    }
    assert ("publish_commit_failed", "THIRD") in failed
    assert ("issuer_dropped", "THIRD") not in failed
    row = next(c for c in document["checks"] if c["id"] == "publish_commit_failed")
    assert "commit_refused" in row["detail"]


def test_t_m6d_reported_not_attempted_beats_issuer_dropped(a1_store, tmp_path):
    """T-m6d: a contract issuer listed in not_attempted[] gets
    publish_not_attempted, not issuer_dropped."""
    report = _report_document(a1_store, extra_issuers=True)
    report["not_attempted"] = [
        {"ticker": "THIRD", "cik": "0000888888", "reason": "not_reached"}
    ]
    document = _build_in_process(a1_store, tmp_path, report=report, extra_issuers=True)
    failed = {
        (c["id"], c["issuer"]) for c in document["checks"] if c["status"] == "fail"
    }
    assert ("publish_not_attempted", "THIRD") in failed
    assert ("issuer_dropped", "THIRD") not in failed


# ---------------------------------------------------------------------------
# r8: per-issuer read errors are FAIL rows; the two outputs are a pair
# ---------------------------------------------------------------------------


def _generation_without_role(monkeypatch, ledger_module, role):
    """Serve every generation without ``role`` (one issuer's read error)."""
    import dataclasses

    real_load = ledger_module.load_latest_generation

    def _load(store, issuer_id):
        generation = real_load(store, issuer_id)
        if generation is None:
            return None
        payloads = {k: v for k, v in generation.role_payloads.items() if k != role}
        return dataclasses.replace(generation, role_payloads=payloads)

    monkeypatch.setattr(ledger_module, "load_latest_generation", _load)


def _rows_for(document, tickers):
    """The sorted (id, issuer, status, detail) check rows of ``tickers``."""
    return sorted(
        (c["id"], c["issuer"], c["status"], c["detail"])
        for c in document["checks"]
        if c["issuer"] in tickers
    )


def _only_row(document, check_id, issuer):
    matches = [
        c for c in document["checks"] if c["id"] == check_id and c["issuer"] == issuer
    ]
    assert len(matches) == 1, (check_id, issuer, matches)
    return matches[0]


_R8_MINIMAL_COVERAGE_ROW = {
    "ticker": "AAPL",
    "contract": "unavailable",
    "captured": "unavailable",
    "admitted": "unavailable",
    "served": "unavailable",
    "statements_served": "unavailable",
    "statement_refusals": "unavailable",
    "lineage_receipts": "unavailable",
    "lineage_refusals": "unavailable",
    "lineage_refusal_codes": {},
    "bridge": "unavailable",
}


def test_t_r8a_lineage_role_missing_is_a_fail_row_others_survive(
    a1_store, a1_extra_run, tmp_path, monkeypatch
):
    """T-r8a: a missing lineage_evidence_json role is a FAIL row for that
    issuer; the census reads "unavailable" (never a fake 0) and the other
    issuers' rows survive unchanged."""
    import scripts.fif_a1_journey_ledger as ledger_module

    _generation_without_role(monkeypatch, ledger_module, "lineage_evidence_json")
    document = _build_in_process(a1_store, tmp_path, extra_issuers=True)

    unreadable = _only_row(document, "lineage_evidence_unreadable", "AAPL")
    assert unreadable["status"] == "fail"
    assert unreadable["detail"] == (
        "lineage evidence cannot be read from the generation (KeyError)"
    )
    count = _only_row(document, "lineage_count", "AAPL")
    assert count["status"] == "fail"
    assert count["detail"] == (
        "generation lineage receipts are unreadable; "
        "the report lineage_receipt_count cannot be compared"
    )
    assert all(c["id"] != "issuer_internal_error" for c in document["checks"])
    assert [r["ticker"] for r in document["coverage_table"]] == ["AAPL", "SECOND", "THIRD"]
    aapl_row = next(r for r in document["coverage_table"] if r["ticker"] == "AAPL")
    assert aapl_row["lineage_receipts"] == "unavailable"
    aapl = next(i for i in document["issuers"] if i["ticker"] == "AAPL")
    assert aapl["lineage"]["receipt_count"] == "unavailable"
    assert aapl["lineage"]["receipts"] == {
        "v1_pair": "unavailable",
        "v2_chain": "unavailable",
    }
    assert _rows_for(document, {"SECOND", "THIRD"}) == _rows_for(
        a1_extra_run["document"], {"SECOND", "THIRD"}
    )
    assert document["all_checks_passed"] is False


def test_t_r8b_trees_role_missing_is_a_fail_row_others_survive(
    a1_store, a1_extra_run, tmp_path, monkeypatch
):
    """T-r8b: a missing statement_trees_json role is the
    statement_trees_unreadable FAIL row naming every served accession; the
    other issuers' rows survive unchanged."""
    import scripts.fif_a1_journey_ledger as ledger_module

    _generation_without_role(monkeypatch, ledger_module, "statement_trees_json")
    document = _build_in_process(a1_store, tmp_path, extra_issuers=True)

    unreadable = _only_row(document, "statement_trees_unreadable", "AAPL")
    assert unreadable["status"] == "fail"
    for accession in a1_store["accessions"]:
        assert f"{accession} (KeyError)" in unreadable["detail"]
    assert all(c["id"] != "issuer_internal_error" for c in document["checks"])
    assert [r["ticker"] for r in document["coverage_table"]] == ["AAPL", "SECOND", "THIRD"]
    assert _rows_for(document, {"SECOND", "THIRD"}) == _rows_for(
        a1_extra_run["document"], {"SECOND", "THIRD"}
    )
    assert document["all_checks_passed"] is False


def test_t_r8c_unexpected_issuer_error_is_issuer_internal_error(
    a1_store, a1_extra_run, tmp_path, monkeypatch
):
    """T-r8c (r9-strengthened): any other per-issuer error is the
    issuer_internal_error FAIL row (type and message, as on the run-wide path)
    with a minimal "unavailable" entry; the failed issuer keeps exactly that
    one check row (no PASS row written before the error survives), the
    remaining issuers are still ledgered and the markdown renders every
    issuer."""
    import scripts.fif_a1_journey_ledger as ledger_module

    real_hits = ledger_module._fixture_locator_hits

    def _hits(gen):
        if gen is not None:
            raise RuntimeError("synthetic per-issuer failure")
        return real_hits(gen)

    monkeypatch.setattr(ledger_module, "_fixture_locator_hits", _hits)
    document = _build_in_process(a1_store, tmp_path, extra_issuers=True)

    internal = _only_row(document, "issuer_internal_error", "AAPL")
    assert internal["status"] == "fail"
    assert internal["detail"] == (
        "issuer ledger stopped at an internal error "
        "(RuntimeError: synthetic per-issuer failure); "
        "the remaining issuers were still processed"
    )
    # The failed issuer ends with exactly one check row: no bridge/query
    # engine PASS claim survives beside an "unavailable" issuer entry.
    assert [c["id"] for c in document["checks"] if c["issuer"] == "AAPL"] == [
        "issuer_internal_error"
    ]
    assert all(c["id"] != "harness_internal_error" for c in document["checks"])
    assert [r["ticker"] for r in document["coverage_table"]] == ["AAPL", "SECOND", "THIRD"]
    aapl_row = next(r for r in document["coverage_table"] if r["ticker"] == "AAPL")
    assert aapl_row == _R8_MINIMAL_COVERAGE_ROW
    aapl = next(i for i in document["issuers"] if i["ticker"] == "AAPL")
    assert aapl["bridge"]["status"] == "unavailable"
    assert _rows_for(document, {"SECOND", "THIRD"}) == _rows_for(
        a1_extra_run["document"], {"SECOND", "THIRD"}
    )
    assert document["all_checks_passed"] is False
    markdown = ledger_module._render_markdown(document)
    assert "## AAPL" in markdown
    assert "## SECOND" in markdown
    assert "## THIRD" in markdown


def test_t_r8d_cli_bad_issuer_exits_1_and_writes_both(a1_store, tmp_path, monkeypatch):
    """T-r8d: an end-to-end run with one unreadable issuer exits 1 (not the
    run-wide exit 3) and writes both outputs with every issuer."""
    import scripts.fif_a1_journey_ledger as ledger_module

    _generation_without_role(monkeypatch, ledger_module, "lineage_evidence_json")
    directory = tmp_path / "r8d"
    report_path, contract_path = _write_inputs(
        directory, _report_document(a1_store, extra_issuers=True), extra_issuers=True
    )
    exit_code = ledger_module.main(
        [
            "--production-report",
            str(report_path),
            "--store-dir",
            str(a1_store["store_dir"]),
            "--coverage-file",
            str(contract_path),
            "--out-json",
            str(directory / "o.json"),
            "--out-md",
            str(directory / "o.md"),
        ]
    )
    assert exit_code == 1
    assert (directory / "o.json").is_file()
    assert (directory / "o.md").is_file()
    document = json.loads((directory / "o.json").read_text(encoding="utf-8"))
    ids = [c["id"] for c in document["checks"]]
    assert "lineage_evidence_unreadable" in ids
    assert "harness_internal_error" not in ids
    assert len(document["coverage_table"]) == 3
    assert "## SECOND" in (directory / "o.md").read_text(encoding="utf-8")


def test_t_r8e_markdown_write_failure_leaves_no_json(tmp_path, capsys):
    """T-r8e: when the markdown cannot be written, the JSON is not left
    behind and no temp file survives."""
    import scripts.fif_a1_journey_ledger as ledger_module

    d = tmp_path / "out"
    d.mkdir()
    blocker = d / "blocker"
    blocker.write_text("a regular file, not a directory\n", encoding="utf-8")
    result = ledger_module._write_outputs(
        argparse.Namespace(out_json=str(d / "o.json"), out_md=str(blocker / "o.md")),
        {"a": 1},
        "md\n",
    )
    assert result == 2
    assert not (d / "o.json").exists()
    assert sorted(p.name for p in d.iterdir()) == ["blocker"]
    assert "output is unwritable: o.md" in capsys.readouterr().err


def test_t_r8f_second_rename_failure_removes_the_first(tmp_path, capsys, monkeypatch):
    """T-r8f: a failure on the second rename removes the already-renamed
    first output, so a half pair never survives."""
    import scripts.fif_a1_journey_ledger as ledger_module

    d = tmp_path / "out"
    d.mkdir()
    real_replace = ledger_module.os.replace

    def _replace(src, dst, *args, **kwargs):
        if str(dst).endswith("o.md"):
            raise OSError(errno.EACCES, "Permission denied")
        return real_replace(src, dst, *args, **kwargs)

    monkeypatch.setattr(ledger_module.os, "replace", _replace)
    result = ledger_module._write_outputs(
        argparse.Namespace(out_json=str(d / "o.json"), out_md=str(d / "o.md")),
        {"a": 1},
        "md\n",
    )
    assert result == 2
    assert not (d / "o.json").exists()
    assert not (d / "o.md").exists()
    assert list(d.iterdir()) == []
    assert "output is unwritable: o.md" in capsys.readouterr().err


def test_t_r8g_success_writes_both_with_no_leftovers(tmp_path):
    """T-r8g: a successful write publishes both outputs byte-exactly and
    leaves no temp file."""
    import scripts.fif_a1_journey_ledger as ledger_module

    d = tmp_path / "out"
    d.mkdir()
    document = {"b": [1, 2], "a": "café"}
    markdown = "# ledger\n\nall_checks_passed: **false**\n"
    result = ledger_module._write_outputs(
        argparse.Namespace(out_json=str(d / "o.json"), out_md=str(d / "o.md")),
        document,
        markdown,
    )
    assert result is None
    assert (d / "o.json").read_text(encoding="utf-8") == (
        json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    )
    assert (d / "o.md").read_text(encoding="utf-8") == markdown
    assert sorted(p.name for p in d.iterdir()) == ["o.json", "o.md"]


# ---------------------------------------------------------------------------
# r9: all-issuer internal error is exit 3; unencodable output; shared out path
# ---------------------------------------------------------------------------


def _main_args(report_path, contract_path, store_dir, out_json, out_md):
    return [
        "--production-report",
        str(report_path),
        "--store-dir",
        str(store_dir),
        "--coverage-file",
        str(contract_path),
        "--out-json",
        str(out_json),
        "--out-md",
        str(out_md),
    ]


def test_t_r9a_every_issuer_internal_error_exits_3(a1_store, tmp_path, monkeypatch, capsys):
    """T-r9a: when EVERY contract issuer stops at an internal error the run is
    a harness defect: exit 3 with the run-level harness_internal_error row
    beside each issuer_internal_error row (both outputs written); one failed
    issuer among healthy ones stays the ordinary exit 1."""
    import scripts.fif_a1_journey_ledger as ledger_module

    def _always(gen):
        raise RuntimeError("synthetic harness defect")

    monkeypatch.setattr(ledger_module, "_fixture_locator_hits", _always)
    directory = tmp_path / "r9a-all"
    report_path, contract_path = _write_inputs(
        directory, _report_document(a1_store, extra_issuers=True), extra_issuers=True
    )
    exit_code = ledger_module.main(
        _main_args(
            report_path, contract_path, a1_store["store_dir"],
            directory / "o.json", directory / "o.md",
        )
    )
    assert exit_code == 3
    assert (directory / "o.json").is_file()
    assert (directory / "o.md").is_file()
    document = json.loads((directory / "o.json").read_text(encoding="utf-8"))
    internal = [c for c in document["checks"] if c["id"] == "issuer_internal_error"]
    assert sorted(c["issuer"] for c in internal) == ["AAPL", "SECOND", "THIRD"]
    for ticker in ("AAPL", "SECOND", "THIRD"):
        assert [c["id"] for c in document["checks"] if c["issuer"] == ticker] == [
            "issuer_internal_error"
        ]
    harness = _only_row(document, "harness_internal_error", None)
    assert harness["status"] == "fail"
    assert harness["detail"] == (
        "every contract issuer stopped at an internal error (3 of 3); "
        "see the issuer_internal_error rows"
    )
    assert document["all_checks_passed"] is False
    assert (
        "fif_a1_journey_ledger: internal error: every contract issuer stopped"
        in capsys.readouterr().err
    )

    # Contrast: only AAPL (the one issuer with a generation) fails -> exit 1.
    def _only_with_generation(gen):
        if gen is not None:
            raise RuntimeError("synthetic per-issuer failure")
        return []

    monkeypatch.setattr(ledger_module, "_fixture_locator_hits", _only_with_generation)
    directory = tmp_path / "r9a-one"
    report_path, contract_path = _write_inputs(
        directory, _report_document(a1_store, extra_issuers=True), extra_issuers=True
    )
    exit_code = ledger_module.main(
        _main_args(
            report_path, contract_path, a1_store["store_dir"],
            directory / "o.json", directory / "o.md",
        )
    )
    assert exit_code == 1
    document = json.loads((directory / "o.json").read_text(encoding="utf-8"))
    assert [c["issuer"] for c in document["checks"] if c["id"] == "issuer_internal_error"] == [
        "AAPL"
    ]
    assert all(c["id"] != "harness_internal_error" for c in document["checks"])


_CIRCULAR: dict = {}
_CIRCULAR["self"] = _CIRCULAR


@pytest.mark.parametrize(
    ("document", "markdown", "refused"),
    [
        pytest.param(
            {"a": "lone \ud800 surrogate"}, "md\n", "o.json (UnicodeEncodeError)",
            id="json-surrogate",
        ),
        pytest.param(
            {"a": 1}, "md lone \ud800 surrogate\n", "o.md (UnicodeEncodeError)",
            id="md-surrogate",
        ),
        pytest.param({"a": object()}, "md\n", "o.json (TypeError)", id="unserialisable"),
        pytest.param(_CIRCULAR, "md\n", "o.json (ValueError)", id="circular"),
    ],
)
def test_t_r9b_unencodable_payload_exits_2_with_no_temp(
    tmp_path, capsys, document, markdown, refused
):
    """T-r9b: an unencodable payload (lone surrogate -> UnicodeEncodeError) or
    an unserialisable document (TypeError / ValueError from json.dumps) is
    the typed exit 2 with neither output and no temp file left, never a
    traceback."""
    import scripts.fif_a1_journey_ledger as ledger_module

    d = tmp_path / "out"
    d.mkdir()
    result = ledger_module._write_outputs(
        argparse.Namespace(out_json=str(d / "o.json"), out_md=str(d / "o.md")),
        document,
        markdown,
    )
    assert result == 2
    # Neither output and no ``.partial-<pid>`` temp survives (the md-surrogate
    # case already staged the JSON temp before the markdown write failed).
    assert list(d.iterdir()) == []
    assert f"output is unwritable: {refused}" in capsys.readouterr().err


def test_t_r9c_cli_surrogate_ledger_exits_2_with_nothing_left(
    a1_store, tmp_path, monkeypatch, capsys
):
    """T-r9c: end to end, a ledger carrying a lone surrogate exits 2 and leaves
    no output and no temp file in the out directory."""
    import scripts.fif_a1_journey_ledger as ledger_module

    def _surrogate_ledger(**_kwargs):
        return ledger_module._failure_ledger("synthetic_check", "bad \ud800 detail")

    monkeypatch.setattr(ledger_module, "build_ledger", _surrogate_ledger)
    directory = tmp_path / "r9c"
    report_path, contract_path = _write_inputs(directory, _report_document(a1_store))
    out_dir = directory / "out"
    out_dir.mkdir()
    exit_code = ledger_module.main(
        _main_args(
            report_path, contract_path, a1_store["store_dir"],
            out_dir / "o.json", out_dir / "o.md",
        )
    )
    assert exit_code == 2
    assert list(out_dir.iterdir()) == []
    assert "output is unwritable: o.json (UnicodeEncodeError)" in capsys.readouterr().err


@pytest.mark.parametrize("alias", ["identical", "dotdot", "symlink", "hardlink"])
def test_t_r9d_shared_out_path_is_refused_before_any_read_or_delete(tmp_path, capsys, alias):
    """T-r9d: --out-json and --out-md naming one file (textually, through a
    ``..`` segment, a symlink or a hard link) is a typed usage refusal (exit
    2) before any input read or delete: the existing file keeps its bytes
    and nothing new is written."""
    import scripts.fif_a1_journey_ledger as ledger_module

    d = tmp_path / "out"
    (d / "sub").mkdir(parents=True)
    out_json = d / "o.json"
    out_json.write_text("previous run\n", encoding="utf-8")
    if alias == "identical":
        out_md = out_json
    elif alias == "dotdot":
        out_md = d / "sub" / ".." / "o.json"
    elif alias == "symlink":
        out_md = d / "link.md"
        out_md.symlink_to(out_json)
    else:
        out_md = d / "hard.md"
        os.link(out_json, out_md)
    before = sorted(p.name for p in d.iterdir())
    missing = tmp_path / "never-read"
    exit_code = ledger_module.main(
        _main_args(missing / "report.json", missing / "contract.json", missing, out_json, out_md)
    )
    assert exit_code == 2
    err = capsys.readouterr().err
    assert err == (
        f"fif_a1_journey_ledger: --out-json and --out-md name the same file: {out_md.name}\n"
    )
    assert out_json.read_text(encoding="utf-8") == "previous run\n"
    assert sorted(p.name for p in d.iterdir()) == before
