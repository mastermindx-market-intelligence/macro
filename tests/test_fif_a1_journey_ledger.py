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

import json
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
    process, _json, _md = _run_cli(
        report_path, contract_path, a1_store["store_dir"], directory / "out"
    )
    assert process.returncode == 2
    assert process.stderr.strip().startswith("fif_a1_journey_ledger:")

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
    acceptance (the kernel's own bitemporal guard then refuses the engine at
    construction, engine/fundamental_forensics/query.py:4694-4696); no
    ``_build_engine`` stand-in is involved.  The harness reports the failure
    (exit-1 semantics via ``all_checks_passed`` false), keeps the carried
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
        late_filed_at = max(accepted).date() + timedelta(days=1)
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
    assert kernel_row["detail"] == (
        "QueryValidationError: filing metadata filed_at follows source acceptance"
    )

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
