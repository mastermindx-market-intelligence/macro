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
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from collectors.edgar_forensics import historical_submissions_url, persist_response
from collectors.sec_document_spine import (
    ArchiveResponseTooLarge,
    ArchiveStoreError,
    persist_archive_document,
    retain_filing_manifest,
    with_document_retrievals,
)
from engine.research_vault.r2_store import LocalStore
from collectors.sec_request_pacer import SecRequestPacer
from engine.fundamental_forensics.admitted_filing_package import (
    admit_retained_filing_package,
)
from engine.fundamental_forensics.fif_member_capture import (
    DEFAULT_RUN_BUDGET_BYTES,
    read_retained_fif_packages,
)
from engine.fundamental_forensics.lineage_evidence import LineageEvidenceError
from engine.fundamental_forensics.production_datasets import (
    ProductionDatasetError,
    load_generation,
    lineage_from_role_payload,
)
from engine.fundamental_forensics.production_lineage import (
    mint_production_lineage_evidence,
)
from engine.fundamental_forensics.sec_document_spine import build_filing_manifests
from engine.fundamental_forensics import statement_graph
from engine.fundamental_forensics.statement_graph import (
    GOLDEN_AAPL_FIXTURES,
    StatementGraphError,
    load_golden_aapl_package,
)
from engine.fundamental_forensics.query_service import CanonicalEntityBinding
import scripts.publish_fif_production_datasets as producer

ROOT = Path(__file__).resolve().parents[1]
# Seat ruling R-9761-CLK (b): publisher-family runs use a byte-identical copy of
# the metric registry 1.0.0 YAML (catalog / mappings / formulas as on main before
# #9761) as --repo-root. The publisher reads --repo-root only for the registry
# (snapshot_core_registry_payload + load_core_registry), and its CLOCK RULE
# folds every registry available_at into admitted_at, so the live registry's
# later rule clocks would refuse these 2026-10-13 fixture runs. These tests pin
# publisher mechanics; registry drift is detected by the golden pins in
# test_fundamental_forensics_admitted_filing_package.py and
# test_fundamental_forensics_statement_grid.py, which stay on the live registry.
PINNED_REGISTRY_ROOT = ROOT / "tests" / "fixtures" / "fundamental_forensics_registry_v1_0_0"

FIRST_ACCEPTED_AT = "2025-10-31T10:01:26.000Z"   # real-shaped: accepted 2025
SECOND_ACCEPTED_AT = "2024-07-31T10:01:26.000Z"  # real-shaped: accepted 2024
CAPTURE_CLOCK = "2026-10-13T02:31:00Z"           # captured AFTER 2026-10-12
RUN_CLOCK = "2026-10-13T02:35:00Z"
NEXT_NIGHT_CAPTURE = "2026-10-14T02:31:00Z"
NEXT_NIGHT_RUN = "2026-10-14T02:35:00Z"
THIRD_NIGHT_RUN = "2026-10-15T02:35:00Z"
# A run clock EQUAL to the content clock (T_c) — used by ERRATA-3 (iv), where
# neither T_c nor T_r is strictly later than L.published_at.
RUN_CLOCK_EQUAL_TO_CONTENT = "2026-10-13T02:31:00Z"
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
    """Offline SEC stand-in: persists served bytes, paces on the shared pacer.

    ``fail_names`` forces a transport failure for named documents (q4/q9).
    """

    def __init__(
        self,
        cache_root: Path,
        served: dict[str, dict[str, bytes]],
        pacer,
        *,
        fail_names: set[str] | None = None,
    ) -> None:
        self.cache_root = Path(cache_root)
        self._served = served
        self._pacer = pacer
        self.fail_names = set(fail_names or ())
        self.fetched: list[str] = []
        self.pacer_acquires = 0

    def fetch_document(self, document, *, retrieved_at=None, expected_sha256=None, max_document_bytes=None):
        self._pacer.acquire()
        self.pacer_acquires += 1
        url = document["archive_url"]
        accession = url.rsplit("/", 2)[-2].replace("-", "")
        name = url.rsplit("/", 1)[-1]
        self.fetched.append(name)
        if name in self.fail_names:
            raise ArchiveStoreError(f"forced fetch failure: {name}")
        payload = self._served[accession][name]
        if max_document_bytes is not None and len(payload) > max_document_bytes:
            # The real collector's streamed cap: refuse BEFORE anything is
            # persisted, so an over-cap primary leaves no orphan object.
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
            # R8: the contract row carries the form + filing_date the witness
            # binds (mirroring _synthetic_submissions' rows).
            "accessions": [
                {
                    "accession": a,
                    "form": str(identity["manifests"][a]["form"]),
                    "filing_date": _row_value(identity, a, "filing_date"),
                }
                for a in identity["accessions"]
            ],
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
            "--repo-root", str(PINNED_REGISTRY_ROOT),
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


# ---------------------------------------------------------------------------
# FIF publish phase timing (2026-10-19): ::notice observation lines on STDERR.
# The nightly cancellation showed a 1,988 s plan-phase gap with NO per-phase
# evidence; these notices are the measurement, so they must never touch the
# stdout JSON report (D8 — stdout may be $(...)-captured by callers).
# ---------------------------------------------------------------------------

#: ``::notice title=fif_publish_timing::<phase> <ticker> <seconds with 1 decimal>s``
_TIMING_NOTICE_RE = re.compile(
    r"^::notice title=fif_publish_timing::(\S+) (\S+) (\d+\.\d)s$"
)


def _timing_notice_phases(err: str) -> list[tuple[str, str]]:
    """Phases of every timing notice on stderr, each checked against the
    exact wire format (phase, ticker-or-``-``, one-decimal seconds)."""
    phases: list[tuple[str, str]] = []
    for line in err.splitlines():
        if not line.startswith("::notice title=fif_publish_timing::"):
            continue
        match = _TIMING_NOTICE_RE.match(line)
        assert match is not None, f"malformed timing notice: {line!r}"
        phases.append((match.group(1), match.group(2)))
    return phases


def test_publish_timing_notices_land_on_stderr_and_stdout_report_is_unchanged(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    """(a) A passing publish run emits the timing notices on stderr, and its
    stdout stays exactly the JSON report: it still parses and carries the same
    keys/values the incumbent happy-path test asserts."""
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    store = tmp_path / "store"
    report_path = tmp_path / "publish_report.json"

    assert _capture_cli(lane, contract) == 0
    capsys.readouterr()  # drop the capture subcommand's own streams
    assert _publish_cli(lane, contract, store, report_path) == 0
    captured = capsys.readouterr()

    phases = _timing_notice_phases(captured.err)
    assert phases, "expected fif_publish_timing notices on stderr"
    assert any(phase == "plan" for phase, _ in phases)
    assert ("total_plan", "-") in phases
    # First publication over an empty store: no comparison build, one
    # authoritative build, then classification and a real commit — so every
    # other phase family is observed here too.
    for expected in (
        "plan_convert",
        "plan_lineage",
        "plan_build",
        "refusal_check",
        "commit",
        "total_commit",
    ):
        assert any(phase == expected for phase, _ in phases), expected
    # Ticker field is the fixture issuer's own ticker (never a literal here).
    assert {ticker for _, ticker in phases} <= {identity["ticker"], "-"}

    # stdout is STILL the report: it parses, equals the --report-path file,
    # and keeps the exact keys the happy-path test pins.
    report = json.loads(captured.out)
    assert report == json.loads(report_path.read_text(encoding="utf-8"))
    assert [row["ticker"] for row in report["published"]] == [identity["ticker"]]
    assert report["excluded"] == []
    row = report["published"][0]
    assert datetime.fromisoformat(
        row["admitted_at"].replace("Z", "+00:00")
    ) == datetime(2026, 10, 13, 2, 31, tzinfo=timezone.utc)
    assert row["admitted_accessions"] == sorted(identity["accessions"])


def test_publish_timing_never_appears_on_stdout(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    """(b) No timing line ever rides stdout — the run must actually have
    emitted notices (else this would pass vacuously) and none may be on the
    stdout that carries the JSON report."""
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    store = tmp_path / "store"
    report_path = tmp_path / "publish_report.json"

    assert _capture_cli(lane, contract) == 0
    capsys.readouterr()
    assert _publish_cli(lane, contract, store, report_path) == 0
    captured = capsys.readouterr()

    assert _timing_notice_phases(captured.err)
    assert "fif_publish_timing" not in captured.out
    assert not any(
        line.startswith("::notice") for line in captured.out.splitlines()
    )
    assert json.loads(captured.out)["published"]


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
            argv += ["--store-dir", str(tmp_path / "store"), "--repo-root", str(PINNED_REGISTRY_ROOT)]
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


def test_d12_run_budget_default_single_sourced() -> None:
    """D12: the publisher carries no second 256 MiB literal — the capture
    subcommand's --run-budget-bytes default IS the capture module's
    DEFAULT_RUN_BUDGET_BYTES (one source)."""
    args = producer.build_parser().parse_args(
        [
            "capture-members",
            "--coverage-file", "c.json",
            "--raw-root", "r",
            "--archive-root", "a",
            "--recorded-at", RUN_CLOCK,
        ]
    )
    assert args.run_budget_bytes == DEFAULT_RUN_BUDGET_BYTES
    source = (ROOT / "scripts" / "publish_fif_production_datasets.py").read_text(
        encoding="utf-8"
    )
    assert "256 * 1024 * 1024" not in source


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


# ---------------------------------------------------------------------------
# ERRATA-3 (D1+D2): clock advance for changed content — plan/commit/report
# ---------------------------------------------------------------------------


def test_d6_capture_report_files_member_capture_failure_not_no_retained_package(
    tmp_path, monkeypatch, offline_collector
) -> None:
    """D6: capture-members writes a JSON capture report (--report-path) and
    publish consumes it (--capture-report): an issuer whose accessions all
    failed capture is excluded as member_capture_failed:<code>, never the
    misleading no_retained_package."""
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    # Serve empty bytes for BOTH accessions' schema members: capture refuses
    # each with malformed_member (a row-level code — capture still exits 0).
    for accession in identity["accessions"]:
        served = offline_collector["served"][accession.replace("-", "")]
        schema_name = next(name for name in sorted(served) if name.endswith(".xsd"))
        served[schema_name] = b""
    capture_report = tmp_path / "capture_report.json"
    rc = producer.main(
        [
            "capture-members",
            "--coverage-file", str(contract),
            "--raw-root", str(lane["raw_root"]),
            "--archive-root", str(lane["archive_root"]),
            "--recorded-at", CAPTURE_CLOCK,
            "--user-agent", USER_AGENT,
            "--report-path", str(capture_report),
        ]
    )
    assert rc == 0
    capture = json.loads(capture_report.read_text(encoding="utf-8"))
    outcomes = [row["outcome"] for row in capture["issuers"][0]["accessions"]]
    assert outcomes == [
        "member_capture_failed:malformed_member",
        "member_capture_failed:malformed_member",
    ]

    store = tmp_path / "store"
    report_path = tmp_path / "publish_report.json"
    # Without the capture report the issuer is the (misleading)
    # no_retained_package exclusion; with it, the capture failure is filed.
    assert _publish_cli(lane, contract, store, report_path) == 0
    baseline = json.loads(report_path.read_text(encoding="utf-8"))
    assert [row["reason"] for row in baseline["excluded"]] == ["no_retained_package"]

    rc = producer.main(
        [
            "publish",
            "--coverage-file", str(contract),
            "--raw-root", str(lane["raw_root"]),
            "--archive-root", str(lane["archive_root"]),
            "--recorded-at", RUN_CLOCK,
            "--store-dir", str(store),
            "--repo-root", str(PINNED_REGISTRY_ROOT),
            "--report-path", str(report_path),
            "--capture-report", str(capture_report),
        ]
    )
    assert rc == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["published"] == []
    assert [row["reason"] for row in report["excluded"]] == [
        "member_capture_failed:malformed_member"
    ]


def test_q2_malformed_incumbent_targets_extra_key_is_typed(tmp_path, capsys) -> None:
    """Q2: a malformed incumbent targets file (extra top-level key) makes
    `targets` exit rc != 0 with typed contract_malformed and a line-start
    ::error. Call path: scripts/publish_fif_production_datasets.py
    `_run_targets` -> `from scripts.run_fundamental_forensics_wave2 import
    load_targets_file` -> `load_targets_file(Path(args.targets_file))`
    (scripts/run_fundamental_forensics_wave2.py:102-136: strict
    set(value) == {'schema','targets'} and set(entry) == {'ticker','cik'}
    shape, raising OperatorFlowError, which _run_targets wraps as
    PublisherError contract_malformed)."""
    identity = _fixture_identity()
    contract = _write_contract(tmp_path, identity, None)
    targets_file = tmp_path / "targets.json"
    targets_file.write_text(
        json.dumps(
            {
                "schema": "fundamental_forensics.wave2_targets/v1",
                "targets": [{"ticker": "T001", "cik": "0000000001"}],
                "extra": True,
            }
        ),
        encoding="utf-8",
    )
    rc = producer.main(
        [
            "targets",
            "--coverage-file", str(contract),
            "--targets-file", str(targets_file),
            "--max-tickers", "5",
        ]
    )
    assert rc == 1
    assert any(
        "contract_malformed" in line for line in _stderr_error_lines(capsys)
    )


def test_q2_incumbent_targets_entry_missing_cik_refuses(tmp_path, capsys) -> None:
    """Q2: an incumbent targets entry missing its cik is the same typed
    refusal (load_targets_file's strict entry shape)."""
    identity = _fixture_identity()
    contract = _write_contract(tmp_path, identity, None)
    targets_file = tmp_path / "targets.json"
    targets_file.write_text(
        json.dumps(
            {
                "schema": "fundamental_forensics.wave2_targets/v1",
                "targets": [{"ticker": "T001"}],
            }
        ),
        encoding="utf-8",
    )
    rc = producer.main(
        [
            "targets",
            "--coverage-file", str(contract),
            "--targets-file", str(targets_file),
            "--max-tickers", "5",
        ]
    )
    assert rc == 1
    assert any(
        "contract_malformed" in line for line in _stderr_error_lines(capsys)
    )


def _empty_mint(_ledger, _packages, *, system_available_at):
    """A changed S2-p mint output (an empty receipt tuple is lawful): moves the
    generation id WITHOUT moving any content clock — exactly the ERRATA-3
    registry/code-output-change scenario."""
    return ()


def test_errata3_i_identical_rerun_is_unchanged_zero_real_writes(
    tmp_path, monkeypatch, offline_collector
) -> None:
    """(i) rerun with identical inputs -> outcome unchanged, ZERO real-store
    writes (store object listing byte-identical before/after)."""
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    assert _capture_cli(lane, contract) == 0
    store = tmp_path / "store"
    report_path = tmp_path / "publish_report.json"
    assert _publish_cli(lane, contract, store, report_path) == 0
    first = json.loads(report_path.read_text(encoding="utf-8"))
    assert first["published"][0]["outcome"] == "published"
    files_before = _store_files(store)
    latest_before = _latest_json_path(store, identity["entity_id"]).read_bytes()
    assert files_before  # night 1 really wrote a generation

    assert _publish_cli(lane, contract, store, report_path, clock=NEXT_NIGHT_RUN) == 0
    second = json.loads(report_path.read_text(encoding="utf-8"))
    row = second["published"][0]
    assert row["outcome"] == "unchanged"
    assert row["clock_basis"] == "latest_unchanged"
    assert row["generation_id"] == first["published"][0]["generation_id"]
    assert row["admitted_at"] == first["published"][0]["admitted_at"]
    # ZERO real-store writes: identical object listing, identical pointer.
    assert _store_files(store) == files_before
    assert _latest_json_path(store, identity["entity_id"]).read_bytes() == latest_before
    # verify accepts `unchanged` because latest.json NAMES the generation.
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


def test_errata3_ii_content_change_publishes_at_run_clock(
    tmp_path, monkeypatch, offline_collector
) -> None:
    """(ii) mint output changes with the same captures -> new generation at
    T_r (--recorded-at), pointer advances, clock_basis=run_recorded_at."""
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    assert _capture_cli(lane, contract) == 0
    store = tmp_path / "store"
    report_path = tmp_path / "publish_report.json"
    assert _publish_cli(lane, contract, store, report_path) == 0
    first = json.loads(report_path.read_text(encoding="utf-8"))
    first_generation = first["published"][0]["generation_id"]

    monkeypatch.setattr(producer, "mint_production_lineage_evidence", _empty_mint)
    assert _publish_cli(lane, contract, store, report_path, clock=NEXT_NIGHT_RUN) == 0
    second = json.loads(report_path.read_text(encoding="utf-8"))
    row = second["published"][0]
    assert row["outcome"] == "published"
    assert row["clock_basis"] == "run_recorded_at"
    assert datetime.fromisoformat(row["admitted_at"].replace("Z", "+00:00")) == datetime(
        2026, 10, 14, 2, 35, tzinfo=timezone.utc
    )  # admitted_at == T_r (the run's --recorded-at)
    assert row["generation_id"] != first_generation
    pointer = json.loads(_latest_json_path(store, identity["entity_id"]).read_text())
    assert pointer["generation_id"] == row["generation_id"]  # pointer ADVANCED


def test_errata3_iii_night_after_change_is_unchanged_no_churn(
    tmp_path, monkeypatch, offline_collector
) -> None:
    """(iii) the night after (ii), no further change -> unchanged, no churn."""
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    assert _capture_cli(lane, contract) == 0
    store = tmp_path / "store"
    report_path = tmp_path / "publish_report.json"
    assert _publish_cli(lane, contract, store, report_path) == 0
    monkeypatch.setattr(producer, "mint_production_lineage_evidence", _empty_mint)
    assert _publish_cli(lane, contract, store, report_path, clock=NEXT_NIGHT_RUN) == 0
    second = json.loads(report_path.read_text(encoding="utf-8"))
    files_after_change = _store_files(store)
    latest_after_change = _latest_json_path(store, identity["entity_id"]).read_bytes()

    assert _publish_cli(lane, contract, store, report_path, clock=THIRD_NIGHT_RUN) == 0
    third = json.loads(report_path.read_text(encoding="utf-8"))
    row = third["published"][0]
    assert row["outcome"] == "unchanged"
    assert row["clock_basis"] == "latest_unchanged"
    assert row["generation_id"] == second["published"][0]["generation_id"]
    assert _store_files(store) == files_after_change  # no new generation minted
    assert (
        _latest_json_path(store, identity["entity_id"]).read_bytes() == latest_after_change
    )


def test_errata3_iv_clock_not_after_latest_refuses_store_byte_identical(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    """(iv) T_r <= L.published_at with changed content -> typed
    admission_clock_not_after_latest naming T_c, T_r and L.published_at,
    raised before any real-store write: store byte-identical, no orphans."""
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    assert _capture_cli(lane, contract) == 0
    store = tmp_path / "store"
    report_path = tmp_path / "publish_report.json"
    assert _publish_cli(lane, contract, store, report_path) == 0
    files_before = _store_files(store)
    latest_before = _latest_json_path(store, identity["entity_id"]).read_bytes()
    report_before = report_path.read_bytes()

    monkeypatch.setattr(producer, "mint_production_lineage_evidence", _empty_mint)
    # T_c == L.published_at == 2026-10-13T02:31:00 and T_r equals it — neither
    # clock is strictly later than the latest published clock.
    rc = _publish_cli(lane, contract, store, report_path, clock=RUN_CLOCK_EQUAL_TO_CONTENT)
    assert rc == 1
    error_lines = _stderr_error_lines(capsys)
    assert any("admission_clock_not_after_latest" in line for line in error_lines)
    joined = " ".join(error_lines)
    # The refusal NAMES all three clocks (here they coincide at 02:31:00Z).
    for role in ("t_c=", "t_r=", "latest_published_at="):
        assert role in joined, role
    assert "2026-10-13T02:31:00" in joined  # T_c and T_r and L.published_at
    assert _store_files(store) == files_before  # byte-identical, no orphan objects
    assert _latest_json_path(store, identity["entity_id"]).read_bytes() == latest_before
    # No report was written by the refusing run (night 1's report stands).
    assert report_path.read_bytes() == report_before


def test_errata3_v_first_publication_uses_content_clock(
    tmp_path, monkeypatch, offline_collector
) -> None:
    """(v) first publication -> clock T_c, clock_basis=content."""
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    assert _capture_cli(lane, contract) == 0
    store = tmp_path / "store"
    report_path = tmp_path / "publish_report.json"
    assert _publish_cli(lane, contract, store, report_path) == 0
    row = json.loads(report_path.read_text(encoding="utf-8"))["published"][0]
    assert row["outcome"] == "published"
    assert row["clock_basis"] == "content"
    assert datetime.fromisoformat(row["admitted_at"].replace("Z", "+00:00")) == datetime(
        2026, 10, 13, 2, 31, tzinfo=timezone.utc
    )  # T_c: the content clock, not the run clock


def test_errata3_vi_new_capture_advances_content_clock(
    tmp_path, monkeypatch, offline_collector
) -> None:
    """(vi) a new capture with a later clock -> T_c > L.published_at ->
    clock_basis=content at the NEW content clock, pointer advances."""
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    assert _capture_cli(lane, contract) == 0
    store = tmp_path / "store"
    report_path = tmp_path / "publish_report.json"
    assert _publish_cli(lane, contract, store, report_path) == 0
    first = json.loads(report_path.read_text(encoding="utf-8"))

    # Re-capture ONE accession with a later clock: delete its (finished)
    # package dir so the accession is absent, then capture at the later clock.
    victim = (
        lane["archive_root"]
        / "fif-packages"
        / identity["cik"]
        / identity["accessions"][0]
    )
    shutil.rmtree(victim)
    assert _capture_cli(lane, contract, clock=NEXT_NIGHT_CAPTURE) == 0

    assert _publish_cli(lane, contract, store, report_path, clock=NEXT_NIGHT_RUN) == 0
    row = json.loads(report_path.read_text(encoding="utf-8"))["published"][0]
    assert row["outcome"] == "published"
    assert row["clock_basis"] == "content"
    assert datetime.fromisoformat(row["admitted_at"].replace("Z", "+00:00")) == datetime(
        2026, 10, 14, 2, 31, tzinfo=timezone.utc
    )  # T_c moved with the new capture
    assert row["generation_id"] != first["published"][0]["generation_id"]
    pointer = json.loads(_latest_json_path(store, identity["entity_id"]).read_text())
    assert pointer["generation_id"] == row["generation_id"]


def _stage_three_issuers(monkeypatch) -> None:
    """Fabricate a three-issuer staged lane over the ONE real admitted set.

    Issuer rows are contract-level data; the D1/D2 plan/commit machinery is
    the object under test, so every fabricated issuer still converts, mints
    and publishes through the REAL path (a synthetic second CIK cannot ride
    the fixture bytes — admission binds the package CIK to the filing's own
    dei EntityCentralIndexKey — so the rows are cloned bindings, not cloned
    packages). Identities are DERIVED at runtime; no literals.
    """
    real_stage = producer._stage_contract_issuers

    def _staged(issuers, *, archive_root, capture_failures=None):
        staged, excluded = real_stage(
            issuers, archive_root=archive_root, capture_failures=capture_failures
        )
        assert len(staged) == 1
        base = staged[0]
        base_binding = base.binding
        for suffix in ("2", "3"):
            cik = base_binding.cik[:-1] + str(
                (int(base_binding.cik[-1]) + int(suffix)) % 10
            )
            issuer = dict(base.issuer)
            issuer["cik"] = cik
            issuer["ticker"] = base_binding.ticker + suffix
            issuer["security_master_binding"] = {
                **dict(base.issuer["security_master_binding"]),
                "issuer_id": base_binding.entity_id + suffix,
                "issuer_cik": cik,
            }
            staged.append(
                producer._StagedIssuer(
                    issuer=issuer,
                    binding=CanonicalEntityBinding(
                        entity_id=base_binding.entity_id + suffix,
                        cik=cik,
                        ticker=base_binding.ticker + suffix,
                        source_entity_id=cik,
                    ),
                    admitted_packages=base.admitted_packages,
                    capture_clocks=base.capture_clocks,
                )
            )
        return staged, excluded

    monkeypatch.setattr(producer, "_stage_contract_issuers", _staged)


class _FlakyPointerStore(LocalStore):
    """A REAL local store whose SECOND latest.json CAS raises — a synthetic
    commit-phase fault on the second committed issuer. (A delegating wrapper
    cannot pass the engine's runtime-Protocol isinstance: Python 3.12 checks
    protocol attrs statically and never sees __getattr__ delegation, so the
    fault has to ride a genuine LocalStore subclass.)"""

    def __init__(self, root) -> None:
        super().__init__(root)
        self.pointer_writes = 0

    def put_bytes_strict_conditional(self, key, data, **kwargs):
        if key.endswith("latest.json"):
            self.pointer_writes += 1
            if self.pointer_writes == 2:
                raise OSError("synthetic commit-phase pointer fault")
        return super().put_bytes_strict_conditional(key, data, **kwargs)


def test_errata3_vii_commit_fault_writes_partial_report(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    """(vii) a mid-commit write failure (injected store fault on issuer 2 of
    3) -> the PARTIAL report names committed / failed+typed code /
    not-attempted issuers before the non-zero exit."""
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    assert _capture_cli(lane, contract) == 0
    store = tmp_path / "store"
    report_path = tmp_path / "publish_report.json"
    _stage_three_issuers(monkeypatch)
    real_builder = producer.build_production_dataset_store

    def _factory(local_dir=None):
        built = real_builder(local_dir)
        if local_dir is not None and Path(local_dir) == store:
            return _FlakyPointerStore(store)
        return built  # plan-phase scratch stores stay honest

    monkeypatch.setattr(producer, "build_production_dataset_store", _factory)

    rc = _publish_cli(lane, contract, store, report_path)
    assert rc == 1
    partial = json.loads(report_path.read_text(encoding="utf-8"))
    entity_ids = [identity["entity_id"], identity["entity_id"] + "2", identity["entity_id"] + "3"]
    assert [row["entity_id"] for row in partial["published"]] == [entity_ids[0]]
    assert partial["published"][0]["outcome"] == "published"
    assert partial["failed"]["entity_id"] == entity_ids[1]
    assert partial["failed"]["code"]  # typed code present (store fault -> publish_failed family)
    assert [row["entity_id"] for row in partial["not_attempted"]] == [entity_ids[2]]
    # Issuer 1 committed for real; issuers 2 and 3 never moved a pointer.
    assert _latest_json_path(store, entity_ids[0]).is_file()
    assert not _latest_json_path(store, entity_ids[1]).exists()
    assert not _latest_json_path(store, entity_ids[2]).exists()
    assert any(
        "publish_failed" in line or partial["failed"]["code"] in line
        for line in _stderr_error_lines(capsys)
    )


def test_d2_plan_failure_on_second_of_three_issuers_leaves_store_byte_identical(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    """D2: the PLAN is all-or-nothing over ALL issuers — issuer 2's plan
    failure (mint refusal) leaves the real store byte-identical with no
    pointer moved and no report minted."""
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    assert _capture_cli(lane, contract) == 0
    store = tmp_path / "store"
    report_path = tmp_path / "publish_report.json"
    _stage_three_issuers(monkeypatch)
    real_mint = producer.mint_production_lineage_evidence
    calls = {"count": 0}

    def _explode_on_second(ledger, packages, *, system_available_at):
        calls["count"] += 1
        if calls["count"] == 2:
            raise LineageEvidenceError("synthetic second-issuer mint refusal")
        return real_mint(ledger, packages, system_available_at=system_available_at)

    monkeypatch.setattr(producer, "mint_production_lineage_evidence", _explode_on_second)
    rc = _publish_cli(lane, contract, store, report_path)
    assert rc == 1
    assert any(
        "lineage_mint_failed" in line for line in _stderr_error_lines(capsys)
    )
    # ALL-or-nothing: nothing was written for ANY issuer.
    assert _store_files(store) == []
    for suffix in ("", "2", "3"):
        assert not _latest_json_path(store, identity["entity_id"] + suffix).exists()
    assert not report_path.exists()


def test_d1_latest_pointer_unreadable_is_typed(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    """D1 (ERRATA-3 1.a): a pointer that exists but cannot be verified is the
    typed latest_pointer_unreadable failure — never treated as absent (which
    would mint a first-publication clock over a broken pointer), and raised
    in PLAN so the store keeps no orphan writes."""
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    assert _capture_cli(lane, contract) == 0
    store = tmp_path / "store"
    report_path = tmp_path / "publish_report.json"
    assert _publish_cli(lane, contract, store, report_path) == 0
    files_before = _store_files(store)
    _latest_json_path(store, identity["entity_id"]).write_text(
        "{ not a pointer", encoding="utf-8"
    )
    files_corrupt = _store_files(store)

    rc = _publish_cli(lane, contract, store, report_path, clock=NEXT_NIGHT_RUN)
    assert rc == 1
    assert any(
        "latest_pointer_unreadable" in line for line in _stderr_error_lines(capsys)
    )
    assert _store_files(store) == files_corrupt  # no writes beyond the corruption
    assert len(files_corrupt) == len(files_before)


# ---------------------------------------------------------------------------
# D13: contract-acquire-summary (T5) + the contract_acquire report block (T6)
# ---------------------------------------------------------------------------


def _acquire_form(form: str, status: str, selected: list[str]) -> dict:
    return {
        "form": form,
        "requested_comparables": 2,
        "selected_accessions": selected,
        "manifest_keys": [],
        "stored_documents": len(selected),
        "missing_documents": 0,
        "reused_documents": 0,
        "status": status,
        "failures": (
            [
                {
                    "stage": f"select_{form}",
                    "error_type": "ComparableCoverageShortfall",
                    "message": (
                        f"only {len(selected)} of 2 comparable {form} filings "
                        "were eligible at as_of"
                    ),
                }
            ]
            if status != "complete"
            else []
        ),
    }


def _acquire_ticker(ticker: str, cik: str, forms: list[dict], status: str) -> dict:
    return {
        "schema": "fundamental_forensics.acquisition_ticker/v1",
        "run_id": "ffsecacq_" + "0" * 64,
        "ticker": ticker,
        "cik": cik,
        "as_of": "2026-10-13T02:31:00Z",
        "recorded_at": "2026-10-13T02:31:00Z",
        "limits": {},
        "submissions": None,
        "forms": forms,
        "bytes_retained": 0,
        "bytes_reused": 0,
        "status": status,
        "failures": [],
    }


def _contract_acquire_result(status: str = "partial") -> dict:
    """A wave-2 outcome shaped like acquire_bounded_filings' run dict
    (collectors/fundamental_forensics_acquisition.py:976-989): one synthetic
    issuer complete, one PARTIAL on its 10-K — the D13 motivating shape (a
    recent window holding a single 10-K, selected 1 of the contractual 2)."""
    complete = _acquire_ticker(
        "FXT",
        "0000000001",
        [
            _acquire_form("10-K", "complete", ["0000000001-26-000004", "0000000001-25-000005"]),
            _acquire_form("10-Q", "complete", ["0000000001-26-000001", "0000000001-26-000002"]),
        ],
        "complete",
    )
    partial = _acquire_ticker(
        "FXU",
        "0000000002",
        [
            _acquire_form("10-K", "partial", ["0000000002-26-000009"]),
            _acquire_form("10-Q", "complete", ["0000000002-26-000003", "0000000002-26-000002"]),
        ],
        "partial",
    )
    return {
        "schema": "fundamental_forensics.wave2_operator_flow/v1",
        "targets": [],
        "actions": {"acquire": True, "sync": True},
        "clocks": {},
        "results": {
            "acquire": {
                "schema": "fundamental_forensics.acquisition_run/v1",
                "run_id": "ffsecacq_" + "0" * 64,
                "as_of": "2026-10-13T02:31:00Z",
                "recorded_at": "2026-10-13T02:31:00Z",
                "targets": [],
                "limits": {},
                "bytes_retained": 0,
                "bytes_reused": 0,
                "reuse_local_archive": True,
                "status": status,
                "ticker_receipts": [complete, partial],
                "observations": [],
            }
        },
        "timings": {},
    }


def test_d13_t5_partial_summary_warns_and_records_shortfalls(tmp_path, capsys) -> None:
    """T5: a typed partial acquire prints a line-start
    ``::warning title=fif-contract-acquire::`` per shortfall on STDOUT (bare
    print, never a logger), exits 0, and the shortfalls ride the summary."""
    result = tmp_path / "result.json"
    result.write_text(
        json.dumps(_contract_acquire_result("partial"), indent=2), encoding="utf-8"
    )
    summary_path = tmp_path / "summary.json"
    rc = producer.main(
        [
            "contract-acquire-summary",
            "--result", str(result),
            "--report-path", str(summary_path),
        ]
    )
    assert rc == 0
    captured = capsys.readouterr()
    warning_lines = [
        line
        for line in captured.out.splitlines()
        if line.startswith("::warning title=fif-contract-acquire::")
    ]
    assert warning_lines, captured.out
    assert any("FXU 10-K 1/2" in line for line in warning_lines), warning_lines
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["schema"] == "fundamental_forensics.fif_contract_acquire_summary/v1"
    assert summary["status"] == "partial"
    shortfall = next(
        row for row in summary["shortfalls"] if row["ticker"] == "FXU" and row["form"] == "10-K"
    )
    assert set(shortfall) == {"ticker", "cik", "form", "selected", "required"}
    assert (shortfall["selected"], shortfall["required"]) == (1, 2)


def test_d13_t5_complete_summary_is_silent(tmp_path, capsys) -> None:
    """T5: a complete acquire emits NO annotation and exits 0."""
    result = tmp_path / "result.json"
    result.write_text(
        json.dumps(_contract_acquire_result("complete"), indent=2), encoding="utf-8"
    )
    rc = producer.main(["contract-acquire-summary", "--result", str(result)])
    assert rc == 0
    captured = capsys.readouterr()
    assert not any(
        line.startswith("::") for line in captured.out.splitlines()
    ), captured.out


def test_d13_t5_missing_result_is_typed_refusal(tmp_path, capsys) -> None:
    """T5: a missing result file is the typed crash-class refusal — rc != 0,
    stderr line-start ::error naming contract_acquire_result_unreadable."""
    rc = producer.main(
        ["contract-acquire-summary", "--result", str(tmp_path / "absent.json")]
    )
    assert rc == 1
    error_lines = [
        line for line in capsys.readouterr().err.splitlines() if line.startswith("::error")
    ]
    assert error_lines and any(
        "contract_acquire_result_unreadable" in line for line in error_lines
    )


def test_d13_t5_malformed_result_is_typed_refusal(tmp_path, capsys) -> None:
    """T5: a result without ``results.acquire`` (malformed) is the same typed
    refusal, never a guessed-at summary."""
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"schema": "unrelated", "results": {}}), encoding="utf-8")
    rc = producer.main(["contract-acquire-summary", "--result", str(bad)])
    assert rc == 1
    error_lines = [
        line for line in capsys.readouterr().err.splitlines() if line.startswith("::error")
    ]
    assert error_lines and any(
        "contract_acquire_result_unreadable" in line for line in error_lines
    )


def test_d13_t5_summary_parses_final_json_despite_mixed_stdout(tmp_path, capsys) -> None:
    """C5 robustness: wave-2's stdout is pure JSON today (its logging rides
    stderr), but the summary must still find the outcome when stray lines land
    on stdout around the final JSON object."""
    outcome = _contract_acquire_result("partial")
    mixed = (
        "some future stray stdout line\n"
        + json.dumps(outcome, indent=2)
        + "\ntrailing noise without braces\n"
    )
    result = tmp_path / "result.json"
    result.write_text(mixed, encoding="utf-8")
    summary_path = tmp_path / "summary.json"
    rc = producer.main(
        ["contract-acquire-summary", "--result", str(result), "--report-path", str(summary_path)]
    )
    assert rc == 0
    captured = capsys.readouterr()
    assert any(
        line.startswith("::warning title=fif-contract-acquire::")
        for line in captured.out.splitlines()
    )
    # The parsed object was the WHOLE final outcome, never a nested fragment:
    # the written summary carries the outer status plus both issuers' rows.
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "partial"
    assert {row["ticker"] for row in summary["shortfalls"]} == {"FXU"}


def test_d13_t6_capture_report_carries_contract_acquire_block(
    tmp_path, monkeypatch, offline_collector
) -> None:
    """T6: capture-members copies the validated contract_acquire block into
    its capture report (schema/status/shortfalls verbatim)."""
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    summary_path = tmp_path / "summary.json"
    rc = producer.main(
        [
            "contract-acquire-summary",
            "--result", _write_result(tmp_path, "partial"),
            "--report-path", str(summary_path),
        ]
    )
    assert rc == 0
    capture_report = tmp_path / "capture_report.json"
    rc = producer.main(
        [
            "capture-members",
            "--coverage-file", str(contract),
            "--raw-root", str(lane["raw_root"]),
            "--archive-root", str(lane["archive_root"]),
            "--recorded-at", CAPTURE_CLOCK,
            "--user-agent", USER_AGENT,
            "--contract-acquire-report", str(summary_path),
            "--report-path", str(capture_report),
        ]
    )
    assert rc == 0
    capture = json.loads(capture_report.read_text(encoding="utf-8"))
    block = capture["contract_acquire"]
    assert block["schema"] == "fundamental_forensics.fif_contract_acquire_summary/v1"
    assert block["status"] == "partial"
    assert any(row["form"] == "10-K" and row["selected"] == 1 for row in block["shortfalls"])


def _write_result(tmp_path: Path, status: str) -> str:
    result = tmp_path / f"result-{status}.json"
    result.write_text(
        json.dumps(_contract_acquire_result(status), indent=2), encoding="utf-8"
    )
    return str(result)


def test_d13_t6_publish_report_carries_contract_acquire_block_and_moves_no_byte(
    tmp_path, monkeypatch, offline_collector
) -> None:
    """T6: publish carries the block onward from the capture report — and the
    block is REPORT ONLY: two stores published from identical inputs, one with
    the block and one without, mint the SAME generation ids and the same store
    bytes (the existing AAPL pins stay green in the same suite)."""
    generation_ids: dict[str, list[str]] = {}
    for variant, with_block in (("with", True), ("without", False)):
        lane = _materialize_lane(tmp_path / variant)
        identity = lane["identity"]
        contract = _write_contract(tmp_path / variant, identity, None)
        store = tmp_path / variant / "store"
        report_path = tmp_path / variant / "publish_report.json"
        capture_report = tmp_path / variant / "capture_report.json"
        summary_path = tmp_path / variant / "summary.json"
        assert producer.main(
            [
                "contract-acquire-summary",
                "--result", _write_result(tmp_path / variant, "partial"),
                "--report-path", str(summary_path),
            ]
        ) == 0
        capture_args = [
            "capture-members",
            "--coverage-file", str(contract),
            "--raw-root", str(lane["raw_root"]),
            "--archive-root", str(lane["archive_root"]),
            "--recorded-at", CAPTURE_CLOCK,
            "--user-agent", USER_AGENT,
            "--report-path", str(capture_report),
        ]
        if with_block:
            capture_args[-2:-2] = ["--contract-acquire-report", str(summary_path)]
        assert producer.main(capture_args) == 0
        publish_args = [
            "publish",
            "--coverage-file", str(contract),
            "--raw-root", str(lane["raw_root"]),
            "--archive-root", str(lane["archive_root"]),
            "--recorded-at", RUN_CLOCK,
            "--store-dir", str(store),
            "--repo-root", str(PINNED_REGISTRY_ROOT),
            "--report-path", str(report_path),
            "--capture-report", str(capture_report),
        ]
        assert producer.main(publish_args) == 0
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if with_block:
            assert report["contract_acquire"]["status"] == "partial"
        else:
            assert "contract_acquire" not in report
        generation_ids[variant] = [row["generation_id"] for row in report["published"]]
        if with_block:
            with_block_store_files = _store_files(store)
        else:
            without_block_store_files = _store_files(store)
    assert generation_ids["with"] == generation_ids["without"]
    assert with_block_store_files == without_block_store_files


def test_d13_t6_capture_refuses_malformed_contract_acquire_report(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    """Fail closed: a present-but-malformed summary file is the typed
    contract_acquire_result_unreadable refusal BEFORE any SEC fetch."""
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    bad_summary = tmp_path / "summary.json"
    bad_summary.write_text(json.dumps({"schema": "unrelated"}), encoding="utf-8")
    rc = producer.main(
        [
            "capture-members",
            "--coverage-file", str(contract),
            "--raw-root", str(lane["raw_root"]),
            "--archive-root", str(lane["archive_root"]),
            "--recorded-at", CAPTURE_CLOCK,
            "--user-agent", USER_AGENT,
            "--contract-acquire-report", str(bad_summary),
            "--report-path", str(tmp_path / "capture_report.json"),
        ]
    )
    assert rc == 1
    error_lines = [
        line for line in capsys.readouterr().err.splitlines() if line.startswith("::error")
    ]
    assert error_lines and any(
        "contract_acquire_result_unreadable" in line for line in error_lines
    )
    # Fail-closed BEFORE the fetch leg: not even a collector was constructed,
    # so no member could be requested from SEC.
    assert offline_collector["collectors"] == []


# ---------------------------------------------------------------------------
# C0-c E1: acquire-contract — contract-keyed primary acquisition (q1..q7, q9)
# ---------------------------------------------------------------------------

ACQUIRE_CLOCK = "2026-10-13T02:28:00Z"  # inside the contract step, before capture


def _clone_accession(accession: str, digit: str) -> str:
    return accession[:-1] + digit


def _page_name_for(identity: dict, index: int = 1) -> str:
    return f"CIK{identity['cik']}-submissions-{index:03d}.json"


def _acquire_row(identity: dict, accession: str, *, form: str, filing_date: str, primary: str) -> dict:
    report_date = filing_date.replace("-02-", "-12-31") if form == "10-K" else filing_date
    return {
        "accessionNumber": accession,
        "form": form,
        "filingDate": filing_date,
        "reportDate": report_date,
        "acceptanceDateTime": SECOND_ACCEPTED_AT,
        "primaryDocument": primary,
        "isXBRL": True,
        "isInlineXBRL": True,
    }


def _identity_rows(identity: dict) -> list[dict]:
    return [
        _acquire_row(
            identity,
            accession,
            form=str(manifest["form"]),
            filing_date=str(manifest["filing_date"]),
            primary=str(manifest["primary_document"]),
        )
        for accession, manifest in sorted(identity["manifests"].items())
    ]


def _write_acquire_submissions(
    raw_root: Path,
    identity: dict,
    *,
    recent_rows: list[dict],
    page_rows: list[dict],
    extra_files: list[dict] | None = None,
    files_override: list[dict] | None = None,
    retrieved_at: str = CAPTURE_CLOCK,
) -> str:
    """latest.json over recent + ONE synthetic covering page (E5-d/E5-8 shape).

    The page is SYNTHETIC but columnar exactly like the real shards: the same
    key set as ``recent`` and one list per key of equal length. Its object and
    receipt are NOT pre-retained — the fake collector fetches it on demand.
    """
    page_name = _page_name_for(identity)
    columns: dict[str, list] = {}
    for row in recent_rows:
        for key, value in row.items():
            columns.setdefault(key, []).append(value)
    filings: dict[str, Any] = {"recent": columns}
    if page_rows or extra_files or files_override:
        files: list[dict] = []
        if page_rows:
            page_columns: dict[str, list] = {}
            for row in page_rows:
                for key, value in row.items():
                    page_columns.setdefault(key, []).append(value)
            assert sorted(page_columns) == sorted(columns), "synthetic page shape must equal recent"
            dates = [row["filingDate"] for row in page_rows]
            files.append(
                {
                    "name": page_name,
                    "filingFrom": min(dates)[:8] + "01",
                    "filingTo": max(dates),
                }
            )
        filings["files"] = (
            list(files_override) if files_override is not None else files + list(extra_files or [])
        )
    payload = json.dumps(
        {"cik": int(identity["cik"]), "name": "Synthetic Lane Issuer", "filings": filings}
    ).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    object_path = f"{identity['cik']}/submissions/{digest}.json.gz"
    target = raw_root / object_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(gzip.compress(payload))
    (raw_root / identity["cik"] / "submissions" / "latest.json").write_text(
        json.dumps(
            {
                "schema": "fundamental_forensics_retrieval.v1",
                "cik": identity["cik"],
                "endpoint": "submissions",
                "url": f"https://data.sec.gov/submissions/CIK{identity['cik']}.json",
                "retrieved_at": retrieved_at,
                "sha256": digest,
                "bytes": len(payload),
                "object_path": object_path,
                "http_etag": None,
                "http_last_modified": None,
            }
        ),
        encoding="utf-8",
    )
    return page_name


def _write_acquire_contract(tmp_path: Path, identity: dict, entries: list[dict]) -> Path:
    path = tmp_path / "acquire-contract.json"
    path.write_text(
        json.dumps(
            {
                "schema": "fundamental_forensics.coverage_contract/v1",
                "contract_id": "synthetic-c0c-acquire-test",
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
                        "accessions": entries,
                    }
                ],
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    return path


class _FakeSubmissionsCollector:
    """Offline stand-in for ``SecForensicsCollector``'s historical-shard fetch.

    Persists the served page bytes through the incumbent ``persist_response``
    with ``publish_latest=False`` exactly as the real
    ``fetch_historical_submissions_file`` does, so the E5-b reuse check reads
    genuine receipts back from the raw root.
    """

    def __init__(self, raw_root: Path, pages: dict[str, dict], pacer) -> None:
        self.raw_root = Path(raw_root)
        self._pages = pages
        self._pacer = pacer
        self.page_fetches: list[str] = []

    def fetch_historical_submissions_file(
        self, cik, source_name, *, retrieved_at=None, max_response_bytes=None
    ):
        self._pacer.acquire()
        self.page_fetches.append(str(source_name))
        content = json.dumps(self._pages[str(source_name)]).encode("utf-8")
        return persist_response(
            self.raw_root,
            cik=cik,
            endpoint="submissions",
            url=historical_submissions_url(cik, source_name),
            content=content,
            retrieved_at=retrieved_at,
            publish_latest=False,
        )


@pytest.fixture()
def offline_acquire_collectors(monkeypatch):
    """Route acquire-contract's TWO collectors + pacer to offline fakes."""
    served = _served_members()
    pages: dict[str, dict] = {}
    fail_primary_names: set[str] = set()
    submissions_collectors: list[_FakeSubmissionsCollector] = []
    archive_collectors: list[_FakeCollector] = []
    pacers: list[SecRequestPacer] = []

    def _subs_factory(raw_root, **kwargs):
        collector = _FakeSubmissionsCollector(raw_root, pages, kwargs["pacer"])
        submissions_collectors.append(collector)
        return collector

    def _arch_factory(cache_root, **kwargs):
        collector = _FakeCollector(
            cache_root, served, kwargs["pacer"], fail_names=fail_primary_names
        )
        archive_collectors.append(collector)
        return collector

    def _pacer_factory(**kwargs):
        pacer = _no_sleep_pacer(**kwargs)
        pacers.append(pacer)
        return pacer

    monkeypatch.setattr(producer, "SecForensicsCollector", _subs_factory)
    monkeypatch.setattr(producer, "SecFilingArchiveCollector", _arch_factory)
    monkeypatch.setattr(producer, "SecRequestPacer", _pacer_factory)
    return {
        "pages": pages,
        "served": served,
        "fail_primary_names": fail_primary_names,
        "submissions": submissions_collectors,
        "archive": archive_collectors,
        "pacers": pacers,
    }


def _acquire_cli(
    lane: dict,
    contract: Path,
    report: Path,
    clock: str = ACQUIRE_CLOCK,
    *,
    run_budget_bytes: int | None = None,
    summary: Path | None = None,
) -> int:
    argv = [
        "acquire-contract",
        "--coverage-file", str(contract),
        "--raw-root", str(lane["raw_root"]),
        "--archive-root", str(lane["archive_root"]),
        "--recorded-at", clock,
        "--user-agent", USER_AGENT,
        "--report-path", str(report),
    ]
    if run_budget_bytes is not None:
        argv += ["--run-budget-bytes", str(run_budget_bytes)]
    if summary is not None:
        argv += ["--contract-acquire-summary", str(summary)]
    return producer.main(argv)


def _acquire_outcome(report_path: Path, accession: str) -> dict:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    for issuer in report["issuers"]:
        for row in issuer["accessions"]:
            if row["accession"] == accession:
                return row
    raise AssertionError(f"accession missing from acquire report: {accession}")


def _materialize_acquire_lane(tmp_path: Path, fixtures: dict) -> dict:
    """One issuer, five contract accessions across recent + one page:

    * ``identity[0]`` 10-K (newest) and ``identity[1]`` 10-Q — recent rows;
    * a mid-10-K and an OLD 10-K clone (the wave-2 latest-2 would drop it);
    * an 8-K row (recent) — never selected by wave-2's FORM_FAMILIES;
    * one page-row 10-Q clone covered by the synthetic shard.
    """
    identity = _fixture_identity()
    raw_root = tmp_path / "raw"
    archive_root = tmp_path / "archive"
    raw_root.mkdir(parents=True)
    archive_root.mkdir(parents=True)
    newest_10k = identity["accessions"][0]
    ten_q = identity["accessions"][1]
    mid_10k = _clone_accession(newest_10k, "6")
    old_10k = _clone_accession(newest_10k, "7")
    eight_k = _clone_accession(ten_q, "5")
    page_10q = _clone_accession(ten_q, "8")
    recent_rows = [
        *_identity_rows(identity),
        _acquire_row(identity, mid_10k, form="10-K", filing_date="2025-01-15", primary=str(identity["manifests"][newest_10k]["primary_document"])),
        _acquire_row(identity, old_10k, form="10-K", filing_date="2024-01-15", primary=str(identity["manifests"][newest_10k]["primary_document"])),
        _acquire_row(identity, eight_k, form="8-K", filing_date="2026-09-02", primary=str(identity["manifests"][ten_q]["primary_document"])),
    ]
    page_row = _acquire_row(identity, page_10q, form="10-Q", filing_date="2024-07-31", primary=str(identity["manifests"][ten_q]["primary_document"]))
    page_name = _write_acquire_submissions(
        raw_root, identity, recent_rows=recent_rows, page_rows=[page_row]
    )
    # The synthetic page payload is the columnar dict itself (one row).
    columns: dict[str, list] = {}
    for key in recent_rows[0]:
        columns[key] = [page_row[key]]
    fixtures["pages"][page_name] = columns
    # Serve synthetic accessions' primaries from their fixture twins.
    for clone, twin in ((mid_10k, newest_10k), (old_10k, newest_10k), (eight_k, ten_q), (page_10q, ten_q)):
        fixtures["served"][clone.replace("-", "")] = dict(fixtures["served"][twin.replace("-", "")])
    entries = [
        {"accession": newest_10k, "form": "10-K", "filing_date": str(identity["manifests"][newest_10k]["filing_date"])},
        {"accession": ten_q, "form": "10-Q", "filing_date": str(identity["manifests"][ten_q]["filing_date"])},
        {"accession": mid_10k, "form": "10-K", "filing_date": "2025-01-15"},
        {"accession": old_10k, "form": "10-K", "filing_date": "2024-01-15"},
        {"accession": eight_k, "form": "8-K", "filing_date": "2026-09-02"},
        {"accession": page_10q, "form": "10-Q", "filing_date": "2024-07-31"},
    ]
    contract = _write_acquire_contract(tmp_path, identity, entries)
    return {
        "identity": identity,
        "raw_root": raw_root,
        "archive_root": archive_root,
        "contract": contract,
        "page_name": page_name,
        "page_10q": page_10q,
        "old_10k": old_10k,
        "eight_k": eight_k,
        "newest_10k": newest_10k,
        "ten_q": ten_q,
        "entries": entries,
    }


def test_c0c_q1_recent_row_beyond_latest_two_gets_primary_and_manifest(
    tmp_path, monkeypatch, offline_acquire_collectors, capsys
) -> None:
    """(q1) A recent-row contract accession BEYOND the wave-2 latest-2 (the
    oldest of three 10-K rows — ``select_periodic_comparables`` drops it) gets
    a primary plus manifest retained by acquire-contract, and
    ``find_retained_primary_manifest`` returns it."""
    from engine.fundamental_forensics.fif_member_capture import (
        find_retained_primary_manifest,
    )
    from engine.fundamental_forensics.sec_document_spine import (
        build_filing_manifests,
        select_periodic_comparables,
    )

    lane = _materialize_acquire_lane(tmp_path, offline_acquire_collectors)
    identity = lane["identity"]
    # Prove the wave-2 selector drops the oldest 10-K at count=2.
    submissions_payload = json.loads(
        gzip.decompress((lane["raw_root"] / _latest_object(lane)).read_bytes())
    )
    manifests = build_filing_manifests(
        submissions_payload,
        cik=identity["cik"],
        ticker=identity["ticker"],
        recorded_at=ACQUIRE_CLOCK,
    )
    selected = select_periodic_comparables(manifests, form="10-K", ticker=identity["ticker"], as_of=ACQUIRE_CLOCK, count=2)
    selected_accessions = {m["filing"]["accession"] for m in selected}
    assert lane["old_10k"] not in selected_accessions

    report = tmp_path / "acquire-report.json"
    rc = _acquire_cli(lane, lane["contract"], report)
    assert rc == 0
    row = _acquire_outcome(report, lane["old_10k"])
    assert row["outcome"] == "primary_retained"
    retained = find_retained_primary_manifest(lane["archive_root"], cik=identity["cik"], accession=lane["old_10k"])
    assert retained is not None
    primary = next(
        item for item in retained["documents"] if item["role"] == "primary"
    )
    assert primary["availability"] == "stored"
    assert primary["retrieval"]["status"] == "retrieved"


def _latest_object(lane: dict) -> str:
    pointer = json.loads(
        (lane["raw_root"] / lane["identity"]["cik"] / "submissions" / "latest.json").read_text()
    )
    return pointer["object_path"]


def test_c0c_q2_page_row_arrives_through_incumbent_shard_fetch(
    tmp_path, monkeypatch, offline_acquire_collectors, capsys
) -> None:
    """(q2) A page-row accession: the page arrives through the incumbent
    ``fetch_historical_submissions_file`` semantics (``publish_latest=False``
    — ``latest.json`` bytes are byte-identical before/after) and the accession's
    manifest is retained."""
    lane = _materialize_acquire_lane(tmp_path, offline_acquire_collectors)
    identity = lane["identity"]
    latest_before = (
        lane["raw_root"] / identity["cik"] / "submissions" / "latest.json"
    ).read_bytes()
    report = tmp_path / "acquire-report.json"
    rc = _acquire_cli(lane, lane["contract"], report)
    assert rc == 0
    # The ONE shard fetch went through the incumbent historical-shard method.
    collector = offline_acquire_collectors["submissions"][0]
    assert collector.page_fetches == [lane["page_name"]]
    # publish_latest=False: the latest pointer never moved.
    assert (
        lane["raw_root"] / identity["cik"] / "submissions" / "latest.json"
    ).read_bytes() == latest_before
    # The page object + receipt landed in the CIK submissions namespace.
    from engine.fundamental_forensics.fif_member_capture import (
        find_verified_submissions_page,
    )

    verified = find_verified_submissions_page(
        lane["raw_root"], cik=identity["cik"], page_name=lane["page_name"]
    )
    assert verified is not None
    # The page-row accession's manifest is retained with a stored primary.
    from engine.fundamental_forensics.fif_member_capture import (
        find_retained_primary_manifest,
    )

    retained = find_retained_primary_manifest(
        lane["archive_root"], cik=identity["cik"], accession=lane["page_10q"]
    )
    assert retained is not None
    row = _acquire_outcome(report, lane["page_10q"])
    assert row["outcome"] == "primary_retained"


def test_c0c_q3_eight_k_primary_retained_form_agnostic(
    tmp_path, monkeypatch, offline_acquire_collectors, capsys
) -> None:
    """(q3) An 8-K contract accession gets a primary retained (form-agnostic)."""
    lane = _materialize_acquire_lane(tmp_path, offline_acquire_collectors)
    identity = lane["identity"]
    report = tmp_path / "acquire-report.json"
    rc = _acquire_cli(lane, lane["contract"], report)
    assert rc == 0
    row = _acquire_outcome(report, lane["eight_k"])
    assert row["outcome"] == "primary_retained"
    from engine.fundamental_forensics.fif_member_capture import (
        find_retained_primary_manifest,
    )

    retained = find_retained_primary_manifest(
        lane["archive_root"], cik=identity["cik"], accession=lane["eight_k"]
    )
    assert retained is not None
    assert retained["filing"]["form"] == "8-K"


def test_c0c_q4_rerun_makes_zero_requests_manifest_and_page_reused(
    tmp_path, monkeypatch, offline_acquire_collectors, capsys
) -> None:
    """(q4) A rerun makes ZERO requests: every accession is a manifest reuse
    hit, and — when a primary failed on night one so its row must be located
    again — the page is served from its verified receipt, not refetched."""
    lane = _materialize_acquire_lane(tmp_path, offline_acquire_collectors)
    identity = lane["identity"]
    report = tmp_path / "acquire-report.json"
    assert _acquire_cli(lane, lane["contract"], report) == 0
    first_archive = offline_acquire_collectors["archive"][0]

    # (a) full rerun: no page fetch, no primary fetch, all rows manifest reuse.
    assert _acquire_cli(lane, lane["contract"], report, clock=NEXT_NIGHT_RUN) == 0
    second_subs = offline_acquire_collectors["submissions"][-1]
    second_archive = offline_acquire_collectors["archive"][-1]
    assert second_subs.page_fetches == []
    assert second_archive.fetched == []
    assert second_archive is not first_archive
    for entry in lane["entries"]:
        row = _acquire_outcome(report, entry["accession"])
        assert row["outcome"] == "retained_reused", row

    # (b) page reuse on a partial first night: force the page-row accession's
    # primary to fail on run 1 (the page IS retained), then let run 2 succeed.
    fresh = _materialize_acquire_lane(tmp_path / "b", offline_acquire_collectors)
    primary_name = str(identity["manifests"][fresh["ten_q"]]["primary_document"])
    offline_acquire_collectors["fail_primary_names"].add(primary_name)
    assert _acquire_cli(fresh, fresh["contract"], report) == 0
    assert _acquire_outcome(report, fresh["page_10q"])["outcome"] == (
        "acquire_failed:primary_fetch_failed"
    )
    offline_acquire_collectors["fail_primary_names"].discard(primary_name)
    assert _acquire_cli(fresh, fresh["contract"], report, clock=NEXT_NIGHT_RUN) == 0
    last_subs = offline_acquire_collectors["submissions"][-1]
    assert last_subs.page_fetches == [], "the retained page must be reused, never refetched"
    assert _acquire_outcome(report, fresh["page_10q"])["outcome"] == "primary_retained"


def test_c0c_q5_page_not_found_and_ambiguous_are_typed(
    tmp_path, monkeypatch, offline_acquire_collectors, capsys
) -> None:
    """(q5) No covering page -> ``submissions_page_not_found``; two covering
    pages -> ``submissions_page_ambiguous``. Both per-accession (exit 0) with a
    line-start ::warning."""
    lane = _materialize_acquire_lane(tmp_path, offline_acquire_collectors)
    identity = lane["identity"]
    missing_acc = _clone_accession(lane["ten_q"], "9")
    row = _acquire_row(identity, missing_acc, form="10-Q", filing_date="2023-03-31", primary=str(identity["manifests"][lane["ten_q"]]["primary_document"]))
    offline_acquire_collectors["served"][missing_acc.replace("-", "")] = dict(
        offline_acquire_collectors["served"][lane["ten_q"].replace("-", "")]
    )
    recent_rows = _identity_rows(identity)
    entries = [{"accession": missing_acc, "form": "10-Q", "filing_date": "2023-03-31"}]
    contract = _write_acquire_contract(tmp_path, identity, entries)
    report = tmp_path / "acquire-report.json"
    # (a) not found: files[] exists but nothing covers 2023-03-31.
    _write_acquire_submissions(
        lane["raw_root"],
        identity,
        recent_rows=recent_rows,
        page_rows=[],
        extra_files=[{"name": f"CIK{identity['cik']}-submissions-001.json", "filingFrom": "2024-01-01", "filingTo": "2024-12-31"}],
    )
    assert _acquire_cli(lane, contract, report) == 0
    assert _acquire_outcome(report, missing_acc)["outcome"] == (
        "acquire_failed:submissions_page_not_found"
    )
    warnings = [
        line
        for line in capsys.readouterr().out.splitlines()
        if line.startswith("::warning title=fif-contract-acquire::")
    ]
    assert warnings and any("submissions_page_not_found" in w for w in warnings)

    # (b) ambiguous: TWO files[] entries both cover 2023-03-31.
    _write_acquire_submissions(
        lane["raw_root"],
        identity,
        recent_rows=recent_rows,
        page_rows=[],
        files_override=[
            {"name": f"CIK{identity['cik']}-submissions-001.json", "filingFrom": "2023-01-01", "filingTo": "2023-12-31"},
            {"name": f"CIK{identity['cik']}-submissions-002.json", "filingFrom": "2022-01-01", "filingTo": "2023-06-30"},
        ],
    )
    assert _acquire_cli(lane, contract, report) == 0
    assert _acquire_outcome(report, missing_acc)["outcome"] == (
        "acquire_failed:submissions_page_ambiguous"
    )


def test_c0c_q6_budget_counts_page_and_primary_refused_before_fetch(
    tmp_path, monkeypatch, offline_acquire_collectors, capsys
) -> None:
    """(q6) The budget counts page PLUS primary bytes: after one page-row
    accession consumes its page and its primary, the remaining budget is below
    the 16 MiB page ceiling, so the SECOND page-row accession is refused
    BEFORE any fetch of its page."""
    lane = _materialize_acquire_lane(tmp_path, offline_acquire_collectors)
    identity = lane["identity"]
    page_bytes = len(
        json.dumps(offline_acquire_collectors["pages"][lane["page_name"]]).encode("utf-8")
    )
    primary_name = str(identity["manifests"][lane["ten_q"]]["primary_document"])
    primary_bytes = len(
        (ROOT / GOLDEN_AAPL_FIXTURES[lane["ten_q"]] / "members" / primary_name).read_bytes()
    )
    # The budget admits the FIRST page (>= 16 MiB pre-fetch reservation) and
    # its primary's actual bytes, then leaves < 16 MiB so the SECOND page-row
    # accession is refused BEFORE its page fetch.
    budget = 16 * 1024 * 1024 + (page_bytes + primary_bytes) // 2
    assert budget >= 16 * 1024 * 1024
    assert budget - page_bytes - primary_bytes < 16 * 1024 * 1024

    second = _clone_accession(lane["ten_q"], "4")
    row2 = _acquire_row(identity, second, form="10-Q", filing_date="2023-06-30", primary=primary_name)
    offline_acquire_collectors["served"][second.replace("-", "")] = dict(
        offline_acquire_collectors["served"][lane["ten_q"].replace("-", "")]
    )
    recent_rows = _identity_rows(identity)
    page_name2 = _page_name_for(identity, index=2)
    first_row = _acquire_row(identity, lane["page_10q"], form="10-Q", filing_date="2024-07-31", primary=primary_name)
    offline_acquire_collectors["pages"][lane["page_name"]] = {
        key: [value] for key, value in first_row.items()
    }
    offline_acquire_collectors["pages"][page_name2] = {
        key: [value] for key, value in row2.items()
    }
    _write_acquire_submissions(
        lane["raw_root"],
        identity,
        recent_rows=recent_rows,
        page_rows=[],
        files_override=[
            {"name": lane["page_name"], "filingFrom": "2024-07-01", "filingTo": "2024-07-31"},
            {"name": page_name2, "filingFrom": "2023-06-01", "filingTo": "2023-06-30"},
        ],
    )
    entries = [
        {"accession": lane["page_10q"], "form": "10-Q", "filing_date": "2024-07-31"},
        {"accession": second, "form": "10-Q", "filing_date": "2023-06-30"},
    ]
    contract = _write_acquire_contract(tmp_path, identity, entries)
    report = tmp_path / "acquire-report.json"
    assert _acquire_cli(lane, contract, report, run_budget_bytes=budget) == 0
    assert _acquire_outcome(report, lane["page_10q"])["outcome"] == "primary_retained"
    assert _acquire_outcome(report, second)["outcome"] == (
        "acquire_failed:run_budget_exceeded"
    )
    # Refused BEFORE the fetch: only ONE page was ever requested.
    assert offline_acquire_collectors["submissions"][0].page_fetches == [lane["page_name"]]


def test_c0c_q7_private_pacer_is_a_typed_refusal(
    tmp_path, monkeypatch, offline_acquire_collectors, capsys
) -> None:
    """(q7) A collector paced privately (its own SecRequestPacer) is the typed
    ``private_pacer`` refusal — rc != 0, no request issued."""
    lane = _materialize_acquire_lane(tmp_path, offline_acquire_collectors)
    real_factory = producer.SecForensicsCollector

    def _private_pacer_factory(raw_root, **kwargs):
        kwargs = dict(kwargs)
        kwargs["pacer"] = _no_sleep_pacer()
        return real_factory(raw_root, **kwargs)

    monkeypatch.setattr(producer, "SecForensicsCollector", _private_pacer_factory)
    report = tmp_path / "acquire-report.json"
    rc = _acquire_cli(lane, lane["contract"], report)
    assert rc == 1
    err = capsys.readouterr().err
    assert "private_pacer" in err
    # Refused before any SEC request: the impostor-paced collector was built,
    # but no page and no primary was ever requested through it.
    assert all(c.page_fetches == [] for c in offline_acquire_collectors["submissions"])
    assert all(c.fetched == [] for c in offline_acquire_collectors["archive"])


def test_c0c_q9_acquire_failure_surfaces_in_both_reports(
    tmp_path, monkeypatch, offline_acquire_collectors, capsys
) -> None:
    """(q9) A forced ``primary_fetch_failed`` in acquire-contract, followed by
    capture: capture reports ``no_retained_primary`` for the accession while
    the acquire report names ``primary_fetch_failed`` for the SAME accession."""
    lane = _materialize_acquire_lane(tmp_path, offline_acquire_collectors)
    identity = lane["identity"]
    primary_name = str(identity["manifests"][lane["ten_q"]]["primary_document"])
    offline_acquire_collectors["fail_primary_names"].add(primary_name)
    acquire_report = tmp_path / "acquire-report.json"
    assert _acquire_cli(lane, lane["contract"], acquire_report) == 0
    assert _acquire_outcome(acquire_report, lane["page_10q"])["outcome"] == (
        "acquire_failed:primary_fetch_failed"
    )
    offline_acquire_collectors["fail_primary_names"].discard(primary_name)

    # capture over the same lane: no retained primary -> no_retained_primary.
    capture_report = tmp_path / "capture-report.json"
    rc = producer.main(
        [
            "capture-members",
            "--coverage-file", str(lane["contract"]),
            "--raw-root", str(lane["raw_root"]),
            "--archive-root", str(lane["archive_root"]),
            "--recorded-at", CAPTURE_CLOCK,
            "--user-agent", USER_AGENT,
            "--report-path", str(capture_report),
        ]
    )
    assert rc == 0
    capture = json.loads(capture_report.read_text(encoding="utf-8"))
    rows = {
        row["accession"]: row["outcome"]
        for issuer in capture["issuers"]
        for row in issuer["accessions"]
    }
    assert rows[lane["page_10q"]] == "no_retained_primary"


def _retain_stale_acquire_page(
    raw_root: Path, cik: str, page_name: str, page: dict, *, retrieved_at: str
):
    """Seed a VERIFIED retained page for one shard URL (incumbent
    ``persist_response``, ``publish_latest=False``) — the re-paged shape."""
    return persist_response(
        raw_root,
        cik=cik,
        endpoint="submissions",
        url=historical_submissions_url(cik, page_name),
        content=json.dumps(page).encode("utf-8"),
        retrieved_at=retrieved_at,
        publish_latest=False,
    )


def test_c0c_q9_stale_retained_page_refetched_once_for_two_accessions(
    tmp_path, monkeypatch, offline_acquire_collectors, capsys
) -> None:
    """(q9, MAJOR-1) Two contract accessions share ONE current page; the
    retained verified page holds only the FIRST (SEC re-paged: its derived
    range also disagrees with the current files[] entry). The run reuses the
    retained page for the first accession, fetches the CURRENT page exactly
    ONCE for the second, and both accessions acquire."""
    identity = _fixture_identity()
    raw_root = tmp_path / "raw"
    archive_root = tmp_path / "archive"
    raw_root.mkdir(parents=True)
    archive_root.mkdir(parents=True)
    ten_q = identity["accessions"][1]
    primary_name = str(identity["manifests"][ten_q]["primary_document"])
    acc1 = _clone_accession(ten_q, "8")
    acc2 = _clone_accession(ten_q, "2")
    page_name = _page_name_for(identity)
    entry = {"name": page_name, "filingFrom": "2024-07-01", "filingTo": "2024-08-31"}
    _write_acquire_submissions(
        raw_root,
        identity,
        recent_rows=_identity_rows(identity),
        page_rows=[],
        files_override=[entry],
    )
    row1 = _acquire_row(identity, acc1, form="10-Q", filing_date="2024-07-31", primary=primary_name)
    row2 = _acquire_row(identity, acc2, form="10-Q", filing_date="2024-08-15", primary=primary_name)
    # The retained page: verified, but stale — it holds only acc1 and its
    # derived range [2024-07-31, 2024-07-31] != the entry's [2024-07-01, 2024-08-31].
    _retain_stale_acquire_page(
        raw_root,
        identity["cik"],
        page_name,
        {key: [row1[key]] for key in row1},
        retrieved_at="2026-10-12T02:28:00Z",
    )
    # The collector serves the CURRENT page: both rows.
    offline_acquire_collectors["pages"][page_name] = {
        key: [row1[key], row2[key]] for key in row1
    }
    for clone in (acc1, acc2):
        offline_acquire_collectors["served"][clone.replace("-", "")] = dict(
            offline_acquire_collectors["served"][ten_q.replace("-", "")]
        )
    entries = [
        {"accession": acc1, "form": "10-Q", "filing_date": "2024-07-31"},
        {"accession": acc2, "form": "10-Q", "filing_date": "2024-08-15"},
    ]
    contract = _write_acquire_contract(tmp_path, identity, entries)
    report = tmp_path / "acquire-report.json"
    lane = {"raw_root": raw_root, "archive_root": archive_root}
    assert _acquire_cli(lane, contract, report) == 0
    assert _acquire_outcome(report, acc1)["outcome"] == "primary_retained"
    assert _acquire_outcome(report, acc2)["outcome"] == "primary_retained"
    # Exactly ONE page fetch in the run, and requests_issued counts it once
    # (the two primary fetches plus the one page fetch).
    assert offline_acquire_collectors["submissions"][0].page_fetches == [page_name]
    acquire_report = json.loads(report.read_text(encoding="utf-8"))
    assert acquire_report["requests_issued"] == 3


def _acquire_row_outcome(report: dict, accession: str) -> str:
    return next(
        row["outcome"]
        for issuer_row in report["issuers"]
        for row in issuer_row["accessions"]
        if row["accession"] == accession
    )


def test_c0c_q10_page_bytes_reduce_primary_budget(tmp_path) -> None:
    """(q10, MINOR-4a) A primary that fits the ORIGINAL budget but not
    budget-minus-page is refused ``run_budget_exceeded``: page bytes reduce the
    run budget, and the refusal fires through the pre-storage cap."""
    from engine.fundamental_forensics.fif_contract_acquisition import (
        acquire_contract_primaries,
    )
    from engine.fundamental_forensics.sec_document_spine import content_storage_key

    identity = _fixture_identity()
    raw_root = tmp_path / "raw"
    archive_root = tmp_path / "archive"
    raw_root.mkdir(parents=True)
    archive_root.mkdir(parents=True)
    ten_q = identity["accessions"][1]
    acc = _clone_accession(ten_q, "4")
    primary_name = str(identity["manifests"][ten_q]["primary_document"])
    inflated = (
        ROOT / GOLDEN_AAPL_FIXTURES[ten_q] / "members" / primary_name
    ).read_bytes() + (b"<!--" + b"p" * 200_000 + b"-->")
    row = _acquire_row(identity, acc, form="10-Q", filing_date="2024-07-31", primary=primary_name)
    page_name = _page_name_for(identity)
    _write_acquire_submissions(
        raw_root,
        identity,
        recent_rows=_identity_rows(identity),
        page_rows=[],
        files_override=[
            {"name": page_name, "filingFrom": "2024-07-01", "filingTo": "2024-07-31"}
        ],
    )
    page = {key: [row[key]] for key in row}
    page_len = len(json.dumps(page).encode("utf-8"))
    pacer = _no_sleep_pacer()
    submissions_collector = _FakeSubmissionsCollector(raw_root, {page_name: page}, pacer)
    archive_collector = _FakeCollector(
        archive_root, {acc.replace("-", ""): {primary_name: inflated}}, pacer
    )
    issuers = [
        {
            "cik": identity["cik"],
            "ticker": identity["ticker"],
            "accessions": [{"accession": acc, "form": "10-Q", "filing_date": "2024-07-31"}],
        }
    ]
    report = acquire_contract_primaries(
        raw_root=raw_root,
        archive_root=archive_root,
        issuers=issuers,
        submissions_collector=submissions_collector,
        archive_collector=archive_collector,
        pacer=pacer,
        recorded_at=ACQUIRE_CLOCK,
        # The ORIGINAL budget admits the page reservation plus the primary in
        # full — but not the primary once the page's bytes are subtracted.
        run_budget_bytes=len(inflated),
        page_ceiling_bytes=page_len,
    )
    assert _acquire_row_outcome(report, acc) == "acquire_failed:run_budget_exceeded"
    assert submissions_collector.page_fetches == [page_name]
    # The page was charged; the over-budget primary left no object behind.
    assert report["bytes_charged"] == page_len
    assert not (
        archive_root / content_storage_key(hashlib.sha256(inflated).hexdigest())
    ).exists()


def test_c0c_q11_over_budget_primary_refused_before_storage(tmp_path) -> None:
    """(q11, MINOR-4b) An over-budget primary is refused by the incumbent
    streamed cap BEFORE anything is persisted: typed ``run_budget_exceeded``
    AND no primary object/receipt for that accession under the archive root
    (the DECLARED manifest may remain — the incumbent discipline retains it
    before the network leg)."""
    from engine.fundamental_forensics.fif_contract_acquisition import (
        acquire_contract_primaries,
    )
    from engine.fundamental_forensics.fif_member_capture import (
        find_retained_primary_manifest,
    )
    from engine.fundamental_forensics.sec_document_spine import content_storage_key

    identity = _fixture_identity()
    raw_root = tmp_path / "raw"
    archive_root = tmp_path / "archive"
    raw_root.mkdir(parents=True)
    archive_root.mkdir(parents=True)
    ten_q = identity["accessions"][1]
    acc = _clone_accession(ten_q, "6")
    primary_name = str(identity["manifests"][ten_q]["primary_document"])
    inflated = (
        ROOT / GOLDEN_AAPL_FIXTURES[ten_q] / "members" / primary_name
    ).read_bytes() + (b"<!--" + b"p" * 200_000 + b"-->")
    row = _acquire_row(identity, acc, form="10-Q", filing_date="2024-07-31", primary=primary_name)
    # A RECENT row: no page is involved, so only the primary touches the budget.
    _write_acquire_submissions(
        raw_root, identity, recent_rows=[*_identity_rows(identity), row], page_rows=[]
    )
    pacer = _no_sleep_pacer()
    submissions_collector = _FakeSubmissionsCollector(raw_root, {}, pacer)
    archive_collector = _FakeCollector(
        archive_root, {acc.replace("-", ""): {primary_name: inflated}}, pacer
    )
    issuers = [
        {
            "cik": identity["cik"],
            "ticker": identity["ticker"],
            "accessions": [{"accession": acc, "form": "10-Q", "filing_date": "2024-07-31"}],
        }
    ]
    report = acquire_contract_primaries(
        raw_root=raw_root,
        archive_root=archive_root,
        issuers=issuers,
        submissions_collector=submissions_collector,
        archive_collector=archive_collector,
        pacer=pacer,
        recorded_at=ACQUIRE_CLOCK,
        run_budget_bytes=len(inflated) // 2,
    )
    assert _acquire_row_outcome(report, acc) == "acquire_failed:run_budget_exceeded"
    assert submissions_collector.page_fetches == []
    assert not (
        archive_root / content_storage_key(hashlib.sha256(inflated).hexdigest())
    ).exists()
    assert (
        find_retained_primary_manifest(
            archive_root, cik=identity["cik"], accession=acc
        )
        is None
    )


# ---------------------------------------------------------------------------
# C0-c E4 + ERRATA-6: coverage row, 8-K publish path, AAPL pins (p8,p9,q8,t6,t8*)
# ---------------------------------------------------------------------------

# Base pins captured at the P1 head (9cc2bdb7cf8) over the standard AAPL lane
# and re-confirmed identical at the P3 head (c149c5c1e64): the 10-K/10-Q
# capture/publish paths must not move through C0-c.
# A0 (R-4 re-pin): the publisher now stamps binding.entity_id into every
# admitted package manifest (admission-loop issuer bind), so the
# statement_packages_index_json role payload — which embeds each package
# manifest — changes bytes, hence the manifest core digest, hence the
# generation id. Cause proof (A0_ENTITY_REPORT.md): the BASE publisher bytes
# at 7ef20577c078 over the same staging lane re-derive the old pin
# ffprods_dacae5538dd6e3351fe52ec55f12629c665a2f63f6ac950fd58397e76578ab78,
# while the retained package_manifest.json sha256 pins below are byte-identical
# under both publishers (the stamp is in-memory, never written to the archive).
# G0 (code-identity re-pin, A0 R-4 precedent): the generation core binds
# packet_builder_digest (bytes of financial_intelligence_packet.py) and
# registry_content_sha256 (catalog/formulas/mappings snapshot). G0 edits both:
# builder cbea8f589a89 -> 87e5e176efe4, registry 3c01f53f1db7 -> 3234dd4dab64
# (python3.12.13 harness). With those inputs held at base the pin re-derives
# ffprods_5aec3b7a0adaa6ae4e752a7c9ced3dc3e9bd7ee4dd6bfa2f49a21262be1a556a;
# the manifest and witness sha256 pins below are unchanged by G0.
_BASE_GENERATION_ID = "ffprods_14aa0f20ba4514f640e784094e7a1dcbc3c8c889e5f956fa63696205e5c86f8d"
_BASE_MANIFEST_SHA = {
    "0000320193-25-000079": "4d9242653aa977a24b5bba955d3d695d4762042ca094ae742fad4453e984b4a8",
    "0000320193-26-000020": "3a9c046f500d542998e4fa7b02a42562e51b28647eb508c68c2a740f693d7f03",
}
_BASE_WITNESS_SHA = {
    "0000320193-25-000079": "f90705b9ac08c53adb6197f13e561e43e020c2b4ce12e223c25f843ec372fda3",
    "0000320193-26-000020": "bdbc22d50ec6f52e7cb56c4205f6fbe908332d3fb7f02661fd8b9b2009865bbb",
}


def _store_tree(store: Path) -> dict[str, bytes]:
    return {
        path.relative_to(store).as_posix(): path.read_bytes()
        for path in sorted(store.rglob("*"))
        if path.is_file()
    }


def _eight_k_index(base_index: bytes, drop_suffixes=("_cal.xml", "_def.xml")) -> bytes:
    payload = json.loads(base_index.decode("utf-8"))
    payload["directory"]["item"] = [
        item
        for item in payload["directory"]["item"]
        if not any(str(item.get("name") or "").endswith(s) for s in drop_suffixes)
    ]
    return (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")


def _eight_k_publish_lane(tmp_path: Path, fixtures: dict, *, digit: str = "5") -> dict:
    """A publish lane with the 10-Q accession PLUS one 8-K event accession
    (captured, admitted, never served)."""
    identity = _fixture_identity()
    ten_q = identity["accessions"][1]
    eight_k = ten_q[:-1] + digit
    raw_root = tmp_path / "raw"
    archive_root = tmp_path / "archive"
    raw_root.mkdir(parents=True)
    archive_root.mkdir(parents=True)
    # Submissions: the identity rows plus the 8-K row (form 8-K) up front.
    submissions = _synthetic_submissions(identity)
    recent = submissions["filings"]["recent"]
    ten_q_index = recent["accessionNumber"].index(ten_q)
    recent["accessionNumber"] = [eight_k, *recent["accessionNumber"]]
    for field in ("form", "filingDate", "reportDate", "acceptanceDateTime", "primaryDocument"):
        recent[field] = [
            "8-K" if field == "form" else recent[field][ten_q_index],
            *recent[field],
        ]
    recent["isXBRL"] = [True, *recent["isXBRL"]]
    recent["isInlineXBRL"] = [True, *recent["isInlineXBRL"]]
    payload = json.dumps(submissions).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    object_path = f"{identity['cik']}/submissions/{digest[:32]}.json.gz"
    (raw_root / object_path).parent.mkdir(parents=True, exist_ok=True)
    (raw_root / object_path).write_bytes(gzip.compress(payload))
    (raw_root / identity["cik"] / "submissions").mkdir(parents=True, exist_ok=True)
    (raw_root / identity["cik"] / "submissions" / "latest.json").write_text(
        json.dumps(
            {
                "schema": "fundamental_forensics_retrieval.v1",
                "cik": identity["cik"],
                "endpoint": "submissions",
                "url": f"https://data.sec.gov/submissions/CIK{identity['cik']}.json",
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
    # Retained primaries: both identity accessions + the 8-K (cloned row).
    manifests = build_filing_manifests(
        submissions, cik=identity["cik"], ticker=identity["ticker"], recorded_at=CAPTURE_CLOCK
    )
    by_accession = {m["filing"]["accession"]: m for m in manifests}
    for accession in [*identity["accessions"], eight_k]:
        manifest = by_accession[accession]
        primary = next(item for item in manifest["documents"] if item["role"] == "primary")
        twin = accession if accession in GOLDEN_AAPL_FIXTURES else ten_q
        primary_bytes = (
            ROOT / GOLDEN_AAPL_FIXTURES[twin] / "members" / primary["document_name"]
        ).read_bytes()
        receipt = persist_archive_document(
            archive_root, primary, primary_bytes, retrieved_at=CAPTURE_CLOCK
        )
        materialized = with_document_retrievals(
            manifest, {str(primary["document_id"]): receipt.to_dict()}
        )
        retain_filing_manifest(archive_root, materialized)
    # Served members: the 8-K's index omits the optional linkbases.
    fixtures["served"][eight_k.replace("-", "")] = dict(
        fixtures["served"][ten_q.replace("-", "")]
    )
    fixtures["served"][eight_k.replace("-", "")]["index.json"] = _eight_k_index(
        fixtures["served"][eight_k.replace("-", "")]["index.json"]
    )
    ten_q_filing_date = _row_value(identity, ten_q, "filing_date")
    entries = [
        {
            "accession": ten_q,
            "form": str(identity["manifests"][ten_q]["form"]),
            "filing_date": ten_q_filing_date,
        },
        {"accession": eight_k, "form": "8-K", "filing_date": ten_q_filing_date},
    ]
    path = tmp_path / "contract-eight-k.json"
    path.write_text(
        json.dumps(
            {
                "schema": "fundamental_forensics.coverage_contract/v1",
                "contract_id": "synthetic-c0c-eight-k-test",
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
                        "accessions": entries,
                    }
                ],
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    return {
        "identity": identity,
        "raw_root": raw_root,
        "archive_root": archive_root,
        "contract": path,
        "ten_q": ten_q,
        "eight_k": eight_k,
    }


def test_c0c_t8_eight_k_admitted_never_served_generation_identical(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    """(t8) One issuer, captured 10-Q + captured 8-K, admit -> publish: the
    generation publishes; the 8-K is admitted; a spy on
    reconstruct_primary_statements proves it never receives the 8-K;
    manifest/generation/index bytes are byte-identical to the same run
    WITHOUT the 8-K; the report-only key names the 8-K accession."""
    import engine.fundamental_forensics.statement_graph as statement_graph

    lane = _eight_k_publish_lane(tmp_path, offline_collector)
    identity = lane["identity"]
    seen_accessions: list[str] = []
    real_reconstruct = statement_graph.reconstruct_primary_statements

    def _spy(*, package, registry):
        seen_accessions.append(str(package.manifest["accession"]))
        return real_reconstruct(package=package, registry=registry)

    monkeypatch.setattr(
        statement_graph, "reconstruct_primary_statements", _spy
    )
    report_path = tmp_path / "report.json"
    assert _capture_cli(lane, lane["contract"]) == 0
    store_with = tmp_path / "store-with"
    assert _publish_cli(lane, lane["contract"], store_with, report_path) == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    row = report["published"][0]
    assert row["outcome"] == "published"
    assert row["admitted_event_accessions"] == [lane["eight_k"]]
    assert row["admitted_accessions"] == [lane["ten_q"]]
    assert lane["eight_k"] not in seen_accessions
    assert seen_accessions  # the material 10-Q was reconstructed

    # Byte-identical to the same run WITHOUT the 8-K: a second lane whose
    # contract lists only the 10-Q over the same submissions + primaries.
    lane_without = dict(lane)
    contract_without = tmp_path / "contract-ten-q-only.json"
    ten_q_entry = json.loads(lane["contract"].read_text())["issuers"][0]["accessions"][0]
    document = json.loads(lane["contract"].read_text())
    document["issuers"][0]["accessions"] = [ten_q_entry]
    contract_without.write_text(json.dumps(document, indent=1), encoding="utf-8")
    lane_without["contract"] = contract_without
    store_without = tmp_path / "store-without"
    assert _publish_cli(lane_without, contract_without, store_without, tmp_path / "report2.json") == 0
    with_tree = _store_tree(store_with)
    without_tree = _store_tree(store_without)
    assert with_tree == without_tree


def test_c0c_t8b_later_captured_eight_k_is_unchanged_zero_writes(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    """(t8b) After t8's generation is published, a later-captured 8-K
    (recorded_at > L.published_at) for the same issuer yields outcome=unchanged
    with ZERO real-store writes."""
    lane = _eight_k_publish_lane(tmp_path, offline_collector)
    identity = lane["identity"]
    assert _capture_cli(lane, lane["contract"]) == 0
    store = tmp_path / "store"
    assert _publish_cli(lane, lane["contract"], store, tmp_path / "r1.json") == 0
    first = json.loads((tmp_path / "r1.json").read_text())
    assert first["published"][0]["outcome"] == "published"

    # A SECOND 8-K, captured at a later clock, joins the contract.
    eight_k2 = lane["ten_q"][:-1] + "6"
    eight_k2_clock = NEXT_NIGHT_CAPTURE
    submissions = _synthetic_submissions(identity)
    recent = submissions["filings"]["recent"]
    ten_q_index = recent["accessionNumber"].index(lane["ten_q"])
    recent["accessionNumber"] = [lane["eight_k"], eight_k2, *recent["accessionNumber"]]
    for field in ("form", "filingDate", "reportDate", "acceptanceDateTime", "primaryDocument"):
        recent[field] = [
            "8-K" if field == "form" else recent[field][ten_q_index],
            "8-K" if field == "form" else recent[field][ten_q_index],
            *recent[field],
        ]
    recent["isXBRL"] = [True, True, *recent["isXBRL"]]
    recent["isInlineXBRL"] = [True, True, *recent["isInlineXBRL"]]
    payload = json.dumps(submissions).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    object_path = f"{identity['cik']}/submissions/{digest[:32]}.json.gz"
    (lane["raw_root"] / object_path).parent.mkdir(parents=True, exist_ok=True)
    (lane["raw_root"] / object_path).write_bytes(gzip.compress(payload))
    (lane["raw_root"] / identity["cik"] / "submissions" / "latest.json").write_text(
        json.dumps(
            {
                "schema": "fundamental_forensics_retrieval.v1",
                "cik": identity["cik"],
                "endpoint": "submissions",
                "url": f"https://data.sec.gov/submissions/CIK{identity['cik']}.json",
                "retrieved_at": eight_k2_clock,
                "sha256": digest,
                "bytes": len(payload),
                "object_path": object_path,
                "http_etag": None,
                "http_last_modified": None,
            }
        ),
        encoding="utf-8",
    )
    manifests = build_filing_manifests(
        submissions, cik=identity["cik"], ticker=identity["ticker"], recorded_at=eight_k2_clock
    )
    by_accession = {m["filing"]["accession"]: m for m in manifests}
    manifest = by_accession[eight_k2]
    primary = next(item for item in manifest["documents"] if item["role"] == "primary")
    primary_bytes = (
        ROOT / GOLDEN_AAPL_FIXTURES[lane["ten_q"]] / "members" / primary["document_name"]
    ).read_bytes()
    receipt = persist_archive_document(
        lane["archive_root"], primary, primary_bytes, retrieved_at=eight_k2_clock
    )
    materialized = with_document_retrievals(
        manifest, {str(primary["document_id"]): receipt.to_dict()}
    )
    retain_filing_manifest(lane["archive_root"], materialized)
    offline_collector["served"][eight_k2.replace("-", "")] = dict(
        offline_collector["served"][lane["ten_q"].replace("-", "")]
    )
    offline_collector["served"][eight_k2.replace("-", "")]["index.json"] = _eight_k_index(
        offline_collector["served"][eight_k2.replace("-", "")]["index.json"]
    )
    document = json.loads(lane["contract"].read_text())
    ten_q_filing_date = _row_value(identity, lane["ten_q"], "filing_date")
    document["issuers"][0]["accessions"].append(
        {"accession": eight_k2, "form": "8-K", "filing_date": ten_q_filing_date}
    )
    lane["contract"].write_text(json.dumps(document, indent=1), encoding="utf-8")

    before = _store_tree(store)
    assert _capture_cli(lane, lane["contract"], clock=eight_k2_clock) == 0
    assert _publish_cli(lane, lane["contract"], store, tmp_path / "r2.json", clock=NEXT_NIGHT_RUN) == 0
    second = json.loads((tmp_path / "r2.json").read_text())
    row = second["published"][0]
    assert row["outcome"] == "unchanged", row
    assert row["clock_basis"] == "latest_unchanged"
    assert sorted(row["admitted_event_accessions"]) == sorted(
        [lane["eight_k"], eight_k2]
    )
    assert _store_tree(store) == before


def test_c0c_t8g_first_publish_eight_k_captured_after_ten_q_keeps_content_clock(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    """(t8g, MINOR-1) FIRST publish (no prior generation) of an issuer whose
    10-Q is captured at T1 and whose 8-K is captured LATER at T2 > T1: the
    published row's admitted_at is the 10-Q-derived content clock (never T2)
    and clock_basis == "content" — ERRATA-6 rule 3: the excluded 8-K's capture
    clock does not contribute to T_c."""
    lane = _eight_k_publish_lane(tmp_path, offline_collector)
    identity = lane["identity"]
    # Night 1: the contract carries ONLY the 10-Q -> its package is captured
    # at T1 (CAPTURE_CLOCK).
    document = json.loads(lane["contract"].read_text())
    ten_q_entry = document["issuers"][0]["accessions"][0]
    document["issuers"][0]["accessions"] = [ten_q_entry]
    ten_q_only = tmp_path / "contract-ten-q-only.json"
    ten_q_only.write_text(json.dumps(document, indent=1), encoding="utf-8")
    assert _capture_cli(lane, ten_q_only, clock=CAPTURE_CLOCK) == 0
    # Night 2: the 8-K joins the contract and is captured at T2 > T1 (the
    # 10-Q package is retained_reused, so its capture clock stays T1).
    assert _capture_cli(lane, lane["contract"], clock=NEXT_NIGHT_CAPTURE) == 0
    store = tmp_path / "store"
    report_path = tmp_path / "r1.json"
    assert _publish_cli(lane, lane["contract"], store, report_path) == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    row = report["published"][0]
    assert row["outcome"] == "published"
    assert row["clock_basis"] == "content"
    # The content clock over the 10-Q's T1 plus the rule + registry clocks —
    # nothing derived from the 8-K's later T2. The registry is the one this
    # publish run read (--repo-root, R-9761-CLK (b)).
    registry_clocks = producer._registry_available_clocks(
        producer.snapshot_core_registry_payload(PINNED_REGISTRY_ROOT)
    )
    t1 = producer.parse_utc(CAPTURE_CLOCK, field="capture clock")
    expected = producer.utc_text(producer._content_clock([t1], registry_clocks))
    assert row["admitted_at"] == expected
    # Guard: T2 is strictly later than the expected clock, so equality above
    # proves the 8-K's T2 did not contribute.
    assert expected < NEXT_NIGHT_CAPTURE
    assert row["admitted_event_accessions"] == [lane["eight_k"]]


def test_c0c_t8c_aapl_golden_pins_unchanged(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    """(t8c) AAPL golden pins unchanged: the generation id equals the base
    pin and the existing golden assertions still hold (a6/t6 re-run)."""
    from engine.fundamental_forensics.admitted_filing_package import (
        REQUIRED_STORED_ROLES,
        admit_retained_filing_package,
    )
    from engine.fundamental_forensics.statement_graph import GOLDEN_AAPL_FIXTURES as GOLDEN

    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    assert _capture_cli(lane, contract) == 0
    assert _publish_cli(lane, contract, tmp_path / "store", tmp_path / "r.json") == 0
    report = json.loads((tmp_path / "r.json").read_text())
    assert report["published"][0]["generation_id"] == _BASE_GENERATION_ID
    # Existing golden admission assertions re-run (t8c's "existing
    # assertions, re-run"): every golden capture still admits with every
    # strict role stored.
    for accession in sorted(GOLDEN):
        fixture = ROOT / GOLDEN[accession]
        manifest = json.loads((fixture / "package_manifest.json").read_text())
        members = {
            item["name"]: (fixture / item["path"]).read_bytes()
            for item in manifest["members"]
            if item.get("state") == "stored"
        }
        admitted = admit_retained_filing_package(
            index_bytes=(fixture / "index.json").read_bytes(),
            manifest=manifest,
            members=members,
            witness_bytes=(fixture / "sec_submissions_witness.json").read_bytes(),
            capture_recorded_at=CAPTURE_CLOCK,
        )
        stored_roles = {
            item.get("role")
            for item in admitted.manifest["members"]
            if item.get("state") == "stored"
        }
        for role in REQUIRED_STORED_ROLES:
            assert role in stored_roles, (accession, role)


def test_c0c_t6_aapl_generation_id_and_manifest_sha_unchanged(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    """(t6/R4) AAPL generation id and package_manifest.json sha256 are
    unchanged against the PR base pins."""
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    assert _capture_cli(lane, contract) == 0
    assert _publish_cli(lane, contract, tmp_path / "store", tmp_path / "r.json") == 0
    report = json.loads((tmp_path / "r.json").read_text())
    assert report["published"][0]["generation_id"] == _BASE_GENERATION_ID
    for accession in identity["accessions"]:
        manifest_path = (
            lane["archive_root"]
            / "fif-packages"
            / identity["cik"]
            / accession
            / "package_manifest.json"
        )
        assert hashlib.sha256(manifest_path.read_bytes()).hexdigest() == (
            _BASE_MANIFEST_SHA[accession]
        )


def test_c0c_p9_aapl_pins_and_witness_unchanged(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    """(p9) AAPL pins unchanged on the ERRATA-5 side: the captured witness
    bytes and package manifest shas equal the base pins."""
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    assert _capture_cli(lane, contract) == 0
    for accession in identity["accessions"]:
        package = lane["archive_root"] / "fif-packages" / identity["cik"] / accession
        assert hashlib.sha256(
            (package / "package_manifest.json").read_bytes()
        ).hexdigest() == _BASE_MANIFEST_SHA[accession]
        assert hashlib.sha256(
            (package / "sec_submissions_witness.json").read_bytes()
        ).hexdigest() == _BASE_WITNESS_SHA[accession]


def test_c0c_t8d_coverage_row_for_eight_k_captured_admitted_not_served(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    """(t8d/ERRATA-6 rule 4) The coverage row for an 8-K: captured=true,
    admitted=true, served=false."""
    lane = _eight_k_publish_lane(tmp_path, offline_collector)
    capture_report = tmp_path / "capture.json"
    rc = producer.main(
        [
            "capture-members",
            "--coverage-file", str(lane["contract"]),
            "--raw-root", str(lane["raw_root"]),
            "--archive-root", str(lane["archive_root"]),
            "--recorded-at", CAPTURE_CLOCK,
            "--user-agent", USER_AGENT,
            "--report-path", str(capture_report),
        ]
    )
    assert rc == 0
    report_path = tmp_path / "r.json"
    rc = producer.main(
        [
            "publish",
            "--coverage-file", str(lane["contract"]),
            "--raw-root", str(lane["raw_root"]),
            "--archive-root", str(lane["archive_root"]),
            "--recorded-at", RUN_CLOCK,
            "--store-dir", str(tmp_path / "store"),
            "--repo-root", str(PINNED_REGISTRY_ROOT),
            "--capture-report", str(capture_report),
            "--report-path", str(report_path),
        ]
    )
    assert rc == 0
    report = json.loads(report_path.read_text())
    coverage = report["coverage"][0]["accessions"]
    by_accession = {row["accession"]: row for row in coverage}
    assert by_accession[lane["eight_k"]] == {
        "accession": lane["eight_k"],
        "captured": True,
        "admitted": True,
        "served": False,
    }
    assert by_accession[lane["ten_q"]]["served"] is True


def test_c0c_t8e_only_event_packages_issuer_publishes_nothing_new(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    """(t8e/ERRATA-6 rule 5) An issuer whose only admitted packages are 8-Ks
    publishes nothing new: one typed exclusion row, no store write, and the
    periodic path is unchanged."""
    lane = _eight_k_publish_lane(tmp_path, offline_collector)
    document = json.loads(lane["contract"].read_text())
    document["issuers"][0]["accessions"] = [
        entry
        for entry in document["issuers"][0]["accessions"]
        if entry["form"] == "8-K"
    ]
    only_eight_k = tmp_path / "contract-only-8k.json"
    only_eight_k.write_text(json.dumps(document, indent=1), encoding="utf-8")
    assert _capture_cli(lane, only_eight_k) == 0
    store = tmp_path / "store"
    report_path = tmp_path / "r.json"
    assert _publish_cli(lane, only_eight_k, store, report_path) == 0
    report = json.loads(report_path.read_text())
    assert report["published"] == []
    assert report["excluded"] == [
        {
            "ticker": report["excluded"][0]["ticker"],
            "cik": report["excluded"][0]["cik"],
            "reason": "only_event_packages",
            "detail": "",
            # r4/D1 (ERRATA-6 rule 4): the admitted 8-Ks ride the exclusion row
            # report-only, so coverage can count them admitted without ever
            # staging the issuer or touching store bytes.
            "admitted_event_accessions": [lane["eight_k"]],
        }
    ]
    # r4/D1 (ERRATA-6 rule 4): the only-event-packages issuer is not staged,
    # yet its admitted 8-K still reports captured=True, admitted=True,
    # served=False — counted admitted, never served.
    coverage_row = report["coverage"][0]
    assert coverage_row["cik"] == str(report["excluded"][0]["cik"])
    by_accession = {row["accession"]: row for row in coverage_row["accessions"]}
    assert by_accession[lane["eight_k"]] == {
        "accession": lane["eight_k"],
        "captured": True,
        "admitted": True,
        "served": False,
    }
    assert coverage_row["captured"] == 1
    assert coverage_row["admitted"] == 1
    assert coverage_row["served"] == 0
    assert not store.exists() or _store_tree(store) == {}


def test_c0c_p8_coverage_row_reports_shortfall_with_typed_codes(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    """(p8/E4 rule 6) The coverage row reports a shortfall with typed codes:
    a never-captured accession carries the JOINED code (capture
    no_retained_primary -> acquire primary_fetch_failed) and the shortfall is
    printed loudly without blocking publish."""
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    ghost = identity["accessions"][1][:-1] + "9"  # never captured
    document = {
        "schema": "fundamental_forensics.coverage_contract/v1",
        "contract_id": "synthetic-c0c-coverage-test",
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
                ]
                + [
                    {
                        "accession": ghost,
                        "form": str(identity["manifests"][identity["accessions"][1]]["form"]),
                        "filing_date": _row_value(
                            identity, identity["accessions"][1], "filing_date"
                        ),
                    }
                ],
            }
        ],
    }
    contract = tmp_path / "contract-ghost.json"
    contract.write_text(json.dumps(document, indent=1), encoding="utf-8")
    assert _capture_cli(lane, contract) == 0
    # A capture report naming the ghost as no_retained_primary, with the
    # acquire report's typed code riding the contract_acquire block.
    capture_report = tmp_path / "capture.json"
    capture_report.write_text(
        json.dumps(
            {
                "schema": "fundamental_forensics.fif_member_capture_run/v1",
                "issuers": [
                    {
                        "cik": identity["cik"],
                        "accessions": [
                            {"accession": identity["accessions"][0], "outcome": "captured"},
                            {"accession": ghost, "outcome": "no_retained_primary"},
                        ],
                    }
                ],
                "contract_acquire": {
                    "schema": producer.CONTRACT_ACQUIRE_SUMMARY_SCHEMA,
                    "status": "partial",
                    "shortfalls": [],
                    "acquire_contract": {
                        "schema": producer.CONTRACT_ACQUISITION_RUN_SCHEMA,
                        "issuers": [
                            {
                                "cik": identity["cik"],
                                "accessions": [
                                    {
                                        "accession": ghost,
                                        "outcome": "acquire_failed:primary_fetch_failed",
                                    }
                                ],
                            }
                        ],
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    report_path = tmp_path / "r.json"
    capsys.readouterr()
    rc = producer.main(
        [
            "publish",
            "--coverage-file", str(contract),
            "--raw-root", str(lane["raw_root"]),
            "--archive-root", str(lane["archive_root"]),
            "--recorded-at", RUN_CLOCK,
            "--store-dir", str(tmp_path / "store"),
            "--repo-root", str(PINNED_REGISTRY_ROOT),
            "--capture-report", str(capture_report),
            "--report-path", str(report_path),
        ]
    )
    assert rc == 0  # a shortfall never blocks publish
    out = capsys.readouterr().out
    assert any(
        line.startswith("::warning title=fif-production-coverage::")
        and "primary_fetch_failed" in line
        for line in out.splitlines()
    )
    report = json.loads(report_path.read_text())
    coverage = {row["accession"]: row for row in report["coverage"][0]["accessions"]}
    missing = coverage[ghost]
    assert missing["captured"] is False
    assert missing["missing_code"] == "primary_fetch_failed"


def test_c0c_q8_acceptance_projection_over_census_summary() -> None:
    """(q8) The offline acceptance projection over the committed census
    summary: every contract accession reachable — 12/12 per new issuer and
    2/2 AAPL — with each residual (none here) carrying its typed code; and
    the committed synthetic page shares the census page's columnar shape."""
    summary = json.loads(
        (
            ROOT
            / "tests/fixtures/fundamental_forensics/fif_submissions_pages/census_summary.json"
        ).read_text(encoding="utf-8")
    )
    contract = json.loads(
        (
            ROOT / "config/fundamental_forensics/coverage/five_issuer_v1.json"
        ).read_text(encoding="utf-8")
    )
    projection = producer.project_census_reachability(summary)
    expected_totals = {
        issuer["ticker"]: len(issuer["accessions"]) for issuer in contract["issuers"]
    }
    assert set(projection) == set(expected_totals)
    for ticker, total in expected_totals.items():
        row = projection[ticker]
        assert row["total"] == total, (ticker, row)
        assert row["reachable"] == total, (ticker, row)
        assert row["residuals"] == []
    # The committed synthetic page carries the census-verified column set
    # (recorded in the summary fixture from the measured real page).
    synthetic = json.loads(
        (
            ROOT
            / "tests/fixtures/fundamental_forensics/fif_submissions_pages/CIK0000320193-submissions-001.json"
        ).read_text(encoding="utf-8")
    )
    assert sorted(synthetic) == summary["page_column_keys"]
    lengths = {len(value) for value in synthetic.values()}
    assert lengths == {2}
    # E5-a: no measured real page exceeds the 16 MiB ceiling, and both
    # worst-case projections stay inside the 256 MiB budget.
    assert summary["projections"]["largest_page_bytes"] <= summary["page_ceiling_bytes"]
    assert summary["projections"]["acquire_contract_worst_case_bytes"] < summary["run_budget_bytes"]
    assert summary["projections"]["capture_worst_case_bytes"] < summary["run_budget_bytes"]


def test_c0c_q8b_projection_residual_codes_are_reachable() -> None:
    """(q8b/r4-D2) The projection's reachability rule is PAGE-DERIVED, never
    location-string-derived: reachable iff recent with no covering pages, or
    exactly one covering page. A non-empty ``location`` cannot rescue a
    0-page row (submissions_page_not_found) or collapse a 2-page row
    (submissions_page_ambiguous) — both residual codes stay reachable."""
    summary = {
        "issuers": [
            {
                "ticker": "SYN",
                "accessions": [
                    {
                        "accession": "0000000000-26-000001",
                        "location": "recent",
                        "covering_pages": [],
                    },
                    {
                        "accession": "0000000000-26-000002",
                        "location": "CIK0000000000-submissions-001",
                        "covering_pages": ["CIK0000000000-submissions-001"],
                    },
                    {
                        # Zero covering pages and not recent — not found, even
                        # though a page NAME sits in ``location``.
                        "accession": "0000000000-26-000003",
                        "location": "CIK0000000000-submissions-002",
                        "covering_pages": [],
                    },
                    {
                        # Two covering pages — ambiguous, whatever location says.
                        "accession": "0000000000-26-000004",
                        "location": "CIK0000000000-submissions-001",
                        "covering_pages": [
                            "CIK0000000000-submissions-001",
                            "CIK0000000000-submissions-002",
                        ],
                    },
                ],
            }
        ]
    }
    projection = producer.project_census_reachability(summary)
    row = projection["SYN"]
    assert row["total"] == 4
    assert row["reachable"] == 2
    assert [residual["accession"] for residual in row["residuals"]] == [
        "0000000000-26-000003",
        "0000000000-26-000004",
    ]
    assert [residual["missing_code"] for residual in row["residuals"]] == [
        "submissions_page_not_found",
        "submissions_page_ambiguous",
    ]
    assert row["residual_codes"] == [
        "submissions_page_ambiguous",
        "submissions_page_not_found",
    ]


# ---------------------------------------------------------------------------
# C0-c M1-M3: reviewer minors on the publisher (m1..m3)
# ---------------------------------------------------------------------------


def test_c0c_m1_outcome_clock_basis_pairing_enforced(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    """(m1) The outcome/clock_basis pairing is enforced at construction:
    every VALID pair builds; every invalid pair raises a ValueError naming
    the pair; and every row of a complete report from an existing
    published+unchanged scenario satisfies the pairing."""
    from datetime import datetime as _datetime

    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    assert _capture_cli(lane, contract) == 0
    staged, _excluded = producer._stage_contract_issuers(
        json.loads(contract.read_text())["issuers"],
        archive_root=lane["archive_root"],
    )
    assert staged
    base = dict(
        staged=staged,
        admitted_at=_datetime(2026, 10, 13, 2, 35, tzinfo=timezone.utc),
        generation_id="ffprods_synthetic",
        manifest_key="manifests/synthetic",
        lineage_receipt_count=1,
        material=None,
    )
    valid = {
        ("published", "content"),
        ("published", "run_recorded_at"),
        ("unchanged", "latest_unchanged"),
    }
    for outcome, clock_basis in valid:
        producer._IssuerPlan(outcome=outcome, clock_basis=clock_basis, **base)
    invalid = [
        ("published", "latest_unchanged"),
        ("unchanged", "content"),
        ("unchanged", "run_recorded_at"),
        ("published", "published"),
        ("changed", "content"),
        ("unchanged", ""),
    ]
    for outcome, clock_basis in invalid:
        with pytest.raises(ValueError) as caught:
            producer._IssuerPlan(outcome=outcome, clock_basis=clock_basis, **base)
        assert outcome in str(caught.value) and clock_basis in str(caught.value)


def test_c0c_m1_complete_report_rows_satisfy_the_pairing(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    """(m1, report half) Every row of a complete report from an existing
    published-then-unchanged scenario satisfies the pairing."""
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    assert _capture_cli(lane, contract) == 0
    store = tmp_path / "store"
    assert _publish_cli(lane, contract, store, tmp_path / "r1.json") == 0
    assert _publish_cli(
        lane, contract, store, tmp_path / "r2.json", clock=NEXT_NIGHT_RUN
    ) == 0
    for name in ("r1.json", "r2.json"):
        report = json.loads((tmp_path / name).read_text(encoding="utf-8"))
        for row in report["published"]:
            assert (row["outcome"], row["clock_basis"]) in (
                producer._IssuerPlan._VALID_OUTCOME_CLOCK_BASIS
            )


class _WriteCountingStore(LocalStore):
    """A real local store that records every write (m2's zero-writes proof)."""

    def __init__(self, root) -> None:
        super().__init__(root)
        self.writes: list[str] = []

    def put_bytes_strict_conditional(self, key, data, **kwargs):
        self.writes.append(key)
        return super().put_bytes_strict_conditional(key, data, **kwargs)

    def put_bytes_strict(self, key, data, **kwargs):
        self.writes.append(key)
        return super().put_bytes_strict(key, data, **kwargs)


def test_c0c_m2_transient_plan_read_is_typed(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    """(m2) A non-ProductionDatasetError exception (OSError) from
    load_latest_generation during the plan read becomes the typed
    latest_pointer_unreadable refusal on stderr with rc != 0, NO raw
    traceback, and ZERO real-store writes for every issuer."""
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    assert _capture_cli(lane, contract) == 0
    store = tmp_path / "store"
    report_path = tmp_path / "r.json"
    # A PRIOR green publish puts a pointer in place for the plan to read.
    assert _publish_cli(lane, contract, store, report_path) == 0
    real_builder = producer.build_production_dataset_store

    def _factory(local_dir=None):
        built = real_builder(local_dir)
        if local_dir is not None and Path(local_dir) == store:
            faulted_store = _TransientReadStore(store)
            faulted.append(faulted_store)
            return faulted_store
        return built  # plan-phase scratch stores stay honest

    counting: list[_WriteCountingStore] = []

    def _factory(local_dir=None):
        built = real_builder(local_dir)
        if local_dir is not None and Path(local_dir) == store:
            counted = _WriteCountingStore(store)
            counting.append(counted)
            return counted
        return built  # plan-phase scratch stores stay honest

    monkeypatch.setattr(producer, "build_production_dataset_store", _factory)
    # The FAKE real store raises OSError during the plan read: the producer's
    # load_latest_generation seam is wrapped so the store's transient read
    # fault surfaces as a raw OSError from the plan read (the engine wraps
    # every in-store read itself; the seam boundary is where the raw type
    # lives for a transient store adapter).
    real_load = producer.load_latest_generation

    def _raise_transient(store, entity_id):
        raise OSError("synthetic transient store read fault")

    monkeypatch.setattr(producer, "load_latest_generation", _raise_transient)
    rc = _publish_cli(lane, contract, store, report_path, clock=NEXT_NIGHT_RUN)
    assert rc == 1
    captured = capsys.readouterr()
    error_lines = [
        line for line in captured.err.splitlines() if line.startswith("::error")
    ]
    assert any(
        "latest_pointer_unreadable" in line
        and "transient store read" in line
        and "OSError" in line
        for line in error_lines
    )
    assert "Traceback (most recent call last)" not in captured.err
    # ZERO real-store writes for every issuer: the typed refusal fired in
    # PLAN, before any commit-phase write.
    assert counting and counting[0].writes == []


class _FirstPointerFaultStore(LocalStore):
    """A real local store whose FIRST latest.json CAS raises (issuer 1)."""

    def __init__(self, root) -> None:
        super().__init__(root)
        self.pointer_writes = 0

    def put_bytes_strict_conditional(self, key, data, **kwargs):
        if key.endswith("latest.json"):
            self.pointer_writes += 1
            if self.pointer_writes == 1:
                raise OSError("synthetic issuer-1 commit fault")
        return super().put_bytes_strict_conditional(key, data, **kwargs)


def test_c0c_m3_partial_report_reports_unchanged_after_failure(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    """(m3) Three issuers, issuer 1's commit fails, issuer 2 planned
    published, issuer 3 unchanged: the partial report carries issuer 3 in
    ``published`` with outcome unchanged + clock_basis latest_unchanged and
    absent from ``not_attempted``; issuer 2 IS in ``not_attempted``; issuers
    2 and 3 see zero real-store writes."""
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    assert _capture_cli(lane, contract) == 0
    store = tmp_path / "store"
    report_path = tmp_path / "r.json"
    _stage_three_issuers(monkeypatch)
    real_plan = producer._plan_issuer
    staged_seen: list = []

    def _planned(staged_row, **kwargs):
        plan = real_plan(staged_row, **kwargs)
        staged_seen.append(staged_row)
        if len(staged_seen) == 3:
            # The THIRD issuer plans UNCHANGED (equal generation id at the
            # latest clock); its row must still be reported in `published`.
            plan.outcome = "unchanged"
            plan.clock_basis = "latest_unchanged"
        return plan

    monkeypatch.setattr(producer, "_plan_issuer", _planned)
    real_builder = producer.build_production_dataset_store

    def _factory(local_dir=None):
        built = real_builder(local_dir)
        if local_dir is not None and Path(local_dir) == store:
            return _FirstPointerFaultStore(store)
        return built

    monkeypatch.setattr(producer, "build_production_dataset_store", _factory)
    rc = _publish_cli(lane, contract, store, report_path)
    assert rc == 1
    partial = json.loads(report_path.read_text(encoding="utf-8"))
    entity_ids = [identity["entity_id"], identity["entity_id"] + "2", identity["entity_id"] + "3"]
    assert partial["failed"]["entity_id"] == entity_ids[0]
    assert [row["entity_id"] for row in partial["not_attempted"]] == [entity_ids[1]]
    assert [row["entity_id"] for row in partial["published"]] == [entity_ids[2]]
    unchanged_row = partial["published"][0]
    assert unchanged_row["outcome"] == "unchanged"
    assert unchanged_row["clock_basis"] == "latest_unchanged"
    # Zero real-store writes for issuers 2 and 3 (and 1 failed its write).
    for entity_id in entity_ids[1:]:
        assert not _latest_json_path(store, entity_id).exists()
    assert _latest_json_path(store, entity_ids[0]).exists() is False


def test_c0c_m4_partial_report_coverage_reflects_commit_outcome(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    """(m4, MINOR-5) The PARTIAL report's coverage reflects the commit loop:
    the failed issuer's accession rows get served=False plus
    ``served_withheld: commit_failed:<code>`` and its served count is
    recomputed; the not-attempted issuer's rows get served=False plus
    ``commit_not_attempted``; only the committed (published) issuer keeps
    served=True."""
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    base_cik = identity["cik"]
    # The derived CIKs _stage_three_issuers fabricates for suffixes "2"/"3",
    # so every commit-outcome class owns a coverage row.
    cik2 = base_cik[:-1] + str((int(base_cik[-1]) + 2) % 10)
    cik3 = base_cik[:-1] + str((int(base_cik[-1]) + 3) % 10)
    accessions = [
        {
            "accession": a,
            "form": str(identity["manifests"][a]["form"]),
            "filing_date": _row_value(identity, a, "filing_date"),
        }
        for a in identity["accessions"]
    ]

    def _issuer_row(cik: str, ticker: str, entity_id: str) -> dict:
        return {
            "cik": cik,
            "ticker": ticker,
            "legal_name": "Synthetic Lane Issuer",
            "security_master_binding": {
                "issuer_id": entity_id,
                "issuer_cik": cik,
                "security_id": identity["security_id"],
                "listing_key": identity["listing_key"],
                "mic": "XNAS",
                "effective_at": "2023-05-09T00:00:00",
            },
            "accessions": accessions,
        }

    document = {
        "schema": "fundamental_forensics.coverage_contract/v1",
        "contract_id": "synthetic-c0c-m4-test",
        "issuers": [
            _issuer_row(base_cik, identity["ticker"], identity["entity_id"]),
            _issuer_row(cik2, identity["ticker"] + "2", identity["entity_id"] + "2"),
            _issuer_row(cik3, identity["ticker"] + "3", identity["entity_id"] + "3"),
        ],
    }
    contract = tmp_path / "contract-three.json"
    contract.write_text(json.dumps(document, indent=1), encoding="utf-8")
    assert _capture_cli(lane, contract) == 0
    store = tmp_path / "store"
    report_path = tmp_path / "r.json"
    _stage_three_issuers(monkeypatch)
    real_builder = producer.build_production_dataset_store

    def _factory(local_dir=None):
        built = real_builder(local_dir)
        if local_dir is not None and Path(local_dir) == store:
            # Issuer 1 commits; issuer 2's pointer CAS faults; issuer 3 is
            # never attempted.
            return _FlakyPointerStore(store)
        return built

    monkeypatch.setattr(producer, "build_production_dataset_store", _factory)
    rc = _publish_cli(lane, contract, store, report_path)
    assert rc == 1
    partial = json.loads(report_path.read_text(encoding="utf-8"))
    assert partial["failed"]["cik"] == cik2
    assert [row["cik"] for row in partial["not_attempted"]] == [cik3]
    coverage = {row["cik"]: row for row in partial["coverage"]}
    # Committed issuer keeps served.
    base_row = coverage[base_cik]
    assert base_row["served"] == len(identity["accessions"])
    assert all(item["served"] for item in base_row["accessions"])
    assert all("served_withheld" not in item for item in base_row["accessions"])
    # Failed issuer: served demoted with the typed commit code.
    failed_row = coverage[cik2]
    withheld_code = f"commit_failed:{partial['failed']['code']}"
    assert failed_row["served"] == 0
    assert all(
        item["served"] is False and item["served_withheld"] == withheld_code
        for item in failed_row["accessions"]
    )
    # Not-attempted issuer: served demoted with the not-attempted marker.
    skipped_row = coverage[cik3]
    assert skipped_row["served"] == 0
    assert all(
        item["served"] is False and item["served_withheld"] == "commit_not_attempted"
        for item in skipped_row["accessions"]
    )


# ---------------------------------------------------------------------------
# A0 repair: a statement-reconstruction refusal excludes ONE issuer, typed,
# instead of aborting the whole publication (2026-10-13 schedule run: one
# SNOW 10-Q ragged grid killed AAPL's publish).

def _three_issuer_contract(tmp_path: Path, identity: dict) -> tuple[Path, list[str]]:
    """The m4 shape: one coverage row per issuer _stage_three_issuers makes."""
    base_cik = identity["cik"]
    ciks = [base_cik] + [
        base_cik[:-1] + str((int(base_cik[-1]) + step) % 10) for step in (2, 3)
    ]
    accessions = [
        {
            "accession": a,
            "form": str(identity["manifests"][a]["form"]),
            "filing_date": _row_value(identity, a, "filing_date"),
        }
        for a in identity["accessions"]
    ]
    issuers = []
    for cik, suffix in zip(ciks, ("", "2", "3")):
        entity_id = identity["entity_id"] + suffix
        issuers.append(
            {
                "cik": cik,
                "ticker": identity["ticker"] + suffix,
                "legal_name": "Synthetic Lane Issuer",
                "security_master_binding": {
                    "issuer_id": entity_id,
                    "issuer_cik": cik,
                    "security_id": identity["security_id"],
                    "listing_key": identity["listing_key"],
                    "mic": "XNAS",
                    "effective_at": "2023-05-09T00:00:00",
                },
                "accessions": accessions,
            }
        )
    document = {
        "schema": "fundamental_forensics.coverage_contract/v1",
        "contract_id": "synthetic-a0-statement-refusal-test",
        "issuers": issuers,
    }
    contract = tmp_path / "contract-three.json"
    contract.write_text(json.dumps(document, indent=1), encoding="utf-8")
    return contract, ciks


def _stage_three_issuers_coherently(monkeypatch) -> None:
    """_stage_three_issuers minus the real stage's ``no_retained_package`` rows
    for the CIKs it fabricates. Those issuers ARE staged here, so a coherent
    report must not also list them excluded (verify_report refuses an issuer
    that appears twice)."""
    _stage_three_issuers(monkeypatch)
    fabricated_stage = producer._stage_contract_issuers

    def _staged(issuers, *, archive_root, capture_failures=None):
        staged, excluded = fabricated_stage(
            issuers, archive_root=archive_root, capture_failures=capture_failures
        )
        staged_ciks = {row.binding.cik for row in staged}
        return staged, [row for row in excluded if row["cik"] not in staged_ciks]

    monkeypatch.setattr(producer, "_stage_contract_issuers", _staged)


def _disclosure_roles() -> dict:
    return {
        "income_statement": {
            "role_uri": "http://fasb.org/us-gaap/role/ParentCompanyInformationIncomeStatementDetails",
            "title": "99556 - Disclosure - Parent Company Information - Income Statement (Details)",
            "title_search": "Parent",
        },
        "balance_sheet": {
            "role_uri": "http://fasb.org/us-gaap/role/ParentCompanyInformationBalanceSheetDetails",
            "title": "99557 - Disclosure - Parent Company Information - Balance Sheet (Details)",
            "title_search": "Parent",
        },
        "cash_flow": {
            "role_uri": "http://fasb.org/us-gaap/role/ParentCompanyInformationCashFlowDetails",
            "title": "99558 - Disclosure - Parent Company Information - Cash Flow (Details)",
            "title_search": "Parent",
        },
    }


def _pin_partial_income_refusal(accession: str):
    return (
        {(accession, "income_statement"): "statement_role_not_consolidated"},
        {(accession, "income_statement", "statement_role_not_consolidated")},
        frozenset(),
    )


def _pin_disclosure_accession(accession: str):
    by_pair = {
        (accession, kind): "statement_role_not_consolidated"
        for kind in ("income_statement", "balance_sheet", "cash_flow")
    }
    triples = {
        (accession, kind, "statement_role_not_consolidated")
        for kind in ("income_statement", "balance_sheet", "cash_flow")
    }
    return by_pair, triples, frozenset()


def _mutate_lane_manifest(lane: dict, accession: str, statement_roles: dict) -> None:
    archive_pkg = (
        lane["archive_root"] / "fif-packages" / lane["identity"]["cik"] / accession
    )
    manifest_path = archive_pkg / "package_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["statement_roles"] = statement_roles
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def test_r6_statement_refusal_slug_reads_kernel_refusal_code() -> None:
    layout = statement_graph._layout_unsupported(
        "ragged grid at row 1 column 18", refusal_code="displayed_layout_unsupported"
    )
    assert producer.statement_refusal_slug(layout) == "displayed_layout_unsupported"
    assert (
        producer.statement_refusal_slug(
            StatementGraphError(
                "displayed statement table is absent: X", refusal_code="displayed_table_absent"
            )
        )
        == "displayed_table_absent"
    )
    assert producer.statement_refusal_slug(StatementGraphError("no numeric rows")) is None
    assert set(producer.STATEMENT_REFUSAL_SLUGS) == set(statement_graph.STATEMENT_REFUSAL_CODES)


def _partial_refusal_roles(identity: dict, accession: str) -> dict:
    golden = load_golden_aapl_package(ROOT, accession)
    from engine.fundamental_forensics.statement_graph import (
        PRIMARY_STATEMENT_ROLES,
        STATEMENT_TITLES,
    )

    extras = golden.manifest.get("statement_roles") or {}
    roles = {key: dict(value) for key, value in extras.items()}
    for kind in ("income_statement", "balance_sheet", "cash_flow"):
        roles.setdefault(
            kind,
            {
                "role_uri": PRIMARY_STATEMENT_ROLES[kind],
                "title": STATEMENT_TITLES[kind],
                "title_search": STATEMENT_TITLES[kind],
            },
        )
    roles["income_statement"] = _disclosure_roles()["income_statement"]
    return roles


def test_r6_partial_publish_reports_real_kernel_refusals(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    accession = identity["accessions"][0]
    contract, _ = _three_issuer_contract(tmp_path, identity)
    assert _capture_cli(lane, contract) == 0
    _mutate_lane_manifest(lane, accession, _partial_refusal_roles(identity, accession))
    store = tmp_path / "store"
    report_path = tmp_path / "r.json"
    _stage_three_issuers_coherently(monkeypatch)
    monkeypatch.setattr(
        producer,
        "_load_statement_refusal_pin",
        lambda: _pin_partial_income_refusal(accession),
    )
    rc = _publish_cli(lane, contract, store, report_path)
    captured = capsys.readouterr()
    assert rc == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["statement_refusals"]
    assert any(
        line.startswith("::warning title=fif_production_datasets-statement_refusals::")
        for line in captured.err.splitlines()
    )


def test_r6_all_refused_issuer_excluded_with_reason_and_detail(
    tmp_path, monkeypatch, offline_collector
) -> None:
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract, ciks = _three_issuer_contract(tmp_path, identity)
    assert _capture_cli(lane, contract) == 0
    for accession in identity["accessions"]:
        _mutate_lane_manifest(lane, accession, _disclosure_roles())
    store = tmp_path / "store"
    report_path = tmp_path / "r.json"
    _stage_three_issuers_coherently(monkeypatch)
    rc = _publish_cli(lane, contract, store, report_path)
    assert rc == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["published"] == []
    assert all(
        row["reason"].startswith("statement_reconstruction_refused:")
        for row in report["excluded"]
    )
    assert isinstance(report["excluded"][0]["detail"], list)


def test_r6_all_refused_accession_flagged_in_report(
    tmp_path, monkeypatch, offline_collector
) -> None:
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    accession = identity["accessions"][0]
    contract, _ = _three_issuer_contract(tmp_path, identity)
    assert _capture_cli(lane, contract) == 0
    _mutate_lane_manifest(lane, accession, _disclosure_roles())
    for other in identity["accessions"][1:]:
        golden = load_golden_aapl_package(ROOT, other)
        roles = golden.manifest.get("statement_roles") or {}
        _mutate_lane_manifest(
            lane,
            other,
            {key: dict(value) for key, value in roles.items()},
        )
    report_path = tmp_path / "r.json"
    _stage_three_issuers_coherently(monkeypatch)
    monkeypatch.setattr(
        producer,
        "_load_statement_refusal_pin",
        lambda: _pin_disclosure_accession(accession),
    )
    rc = _publish_cli(lane, contract, tmp_path / "store", report_path)
    assert rc == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report.get("accession_all_refused", {}).get(accession) is True


def test_r6_all_refused_issuer_exclusion_warns_on_stderr(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract, _ = _three_issuer_contract(tmp_path, identity)
    assert _capture_cli(lane, contract) == 0
    for accession in identity["accessions"]:
        _mutate_lane_manifest(lane, accession, _disclosure_roles())
    report_path = tmp_path / "r.json"
    _stage_three_issuers_coherently(monkeypatch)
    rc = _publish_cli(lane, contract, tmp_path / "store", report_path)
    captured = capsys.readouterr()
    assert rc == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    warnings = [
        line
        for line in captured.err.splitlines()
        if line.startswith(
            "::warning title=fif_production_datasets-statement_reconstruction_refused::"
        )
    ]
    assert len(warnings) == len(report["excluded"]) > 0
    for row in report["excluded"]:
        assert any(row["ticker"] in line for line in warnings)


def test_r6_all_refused_reason_and_detail_use_statement_order(
    tmp_path, monkeypatch, offline_collector
) -> None:
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    accession = identity["accessions"][0]
    contract, _ = _three_issuer_contract(tmp_path, identity)
    assert _capture_cli(lane, contract) == 0
    _stage_three_issuers_coherently(monkeypatch)

    def _rows(_store, plan, *, registry):
        binding = plan.staged.binding
        # Alphabetical order on purpose: balance_sheet < cash_flow < income_statement.
        return [
            {
                "ticker": binding.ticker,
                "cik": binding.cik,
                "accession": accession,
                "statement_type": statement_type,
                "code": code,
                "message": "",
            }
            for statement_type, code in (
                ("balance_sheet", "displayed_columns_absent"),
                ("cash_flow", "displayed_columns_absent"),
                ("income_statement", "statement_role_not_consolidated"),
            )
        ]

    monkeypatch.setattr(producer, "_issuer_all_statements_refused", lambda *_a: True)
    monkeypatch.setattr(producer, "_readback_issuer_refusals", _rows)
    report_path = tmp_path / "r.json"
    rc = _publish_cli(lane, contract, tmp_path / "store", report_path)
    assert rc == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["excluded"]
    for row in report["excluded"]:
        assert row["reason"] == "statement_reconstruction_refused:statement_role_not_consolidated"
        assert [item["statement_type"] for item in row["detail"]] == [
            "income_statement",
            "balance_sheet",
            "cash_flow",
        ]


def test_r6_shipped_refusal_pin_golden_set_is_the_golden_fixtures() -> None:
    from engine.fundamental_forensics.statement_graph import GOLDEN_AAPL_FIXTURES

    _by_pair, _triples, golden = producer._load_statement_refusal_pin()
    assert golden == frozenset(GOLDEN_AAPL_FIXTURES)


def test_r6_refusal_pin_without_golden_key_fails_closed(tmp_path, monkeypatch) -> None:
    pin = tmp_path / "statement_refusals.v1.json"
    pin.write_text(
        json.dumps(
            {
                "refusals": [
                    {
                        "accession": "0000070858-24-000122",
                        "statement_type": "income_statement",
                        "code": "statement_role_not_consolidated",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(producer, "_STATEMENT_REFUSAL_PIN_PATH", pin)
    with pytest.raises(producer.PublisherError) as caught:
        producer._load_statement_refusal_pin()
    assert caught.value.code == "publish_failed"
    assert "golden_accessions" in str(caught.value)


@pytest.mark.parametrize(
    ("raise_on", "reason"),
    (
        ("statement_accessions", "latest_accessions_unreadable"),
        ("statement_trees", "latest_entry_unreadable"),
    ),
)
def test_r6_l_read_failures_name_their_reason(raise_on: str, reason: str) -> None:
    accession = "0000070858-24-000122"

    class _Latest:
        def statement_accessions(self):
            if raise_on == "statement_accessions":
                raise ProductionDatasetError("torn")
            return (accession,)

        def statement_trees(self, _accession):
            raise ProductionDatasetError("torn")

    with pytest.raises(producer.PublisherError) as caught:
        producer._classify_statement_refusal(
            ticker="BAC",
            cik="0000070858",
            accession=accession,
            statement_type="income_statement",
            code="statement_role_not_consolidated",
            latest=_Latest(),
            pin_by_pair={},
            pin_triples=set(),
            golden_accessions=frozenset(),
        )
    assert caught.value.code == "statement_refusal_unpinned"
    assert reason in str(caught.value)


def test_r6_uncoded_kernel_error_fails_the_run(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    lane = _materialize_lane(tmp_path)
    contract, _ = _three_issuer_contract(tmp_path, lane["identity"])
    assert _capture_cli(lane, contract) == 0
    _stage_three_issuers_coherently(monkeypatch)

    def _boom(*_args, **_kwargs):
        raise StatementGraphError("displayed statement has no numeric rows: X")

    monkeypatch.setattr(statement_graph, "reconstruct_primary_statements", _boom)
    rc = _publish_cli(lane, contract, tmp_path / "store", tmp_path / "r.json")
    assert rc == 1
    assert not (tmp_path / "r.json").exists()


def test_r6_unpinned_refusal_on_new_accession_with_latest_publishes_false_and_warning() -> None:
    class _Latest:
        def statement_accessions(self):
            return ()

    assert (
        producer._classify_statement_refusal(
            ticker="SYN",
            cik="0000000001",
            accession="0000000001-26-000099",
            statement_type="income_statement",
            code="displayed_table_absent",
            latest=_Latest(),
            pin_by_pair={},
            pin_triples=set(),
            golden_accessions=frozenset(),
        )
        is False
    )


def test_r6_unpinned_refusal_regressed_from_latest_fails(monkeypatch) -> None:
    class _Latest:
        def statement_accessions(self):
            return ("0000000001-26-000001",)

        def statement_trees(self, accession):
            return {
                "statements": [
                    {
                        "statement_type": "income_statement",
                        "role_uri": "r",
                        "title": "t",
                        "columns": [],
                        "row_count": 1,
                        "rows": [{"cells": []}],
                    }
                ]
            }

    with pytest.raises(producer.PublisherError) as caught:
        producer._classify_statement_refusal(
            ticker="SYN",
            cik="0000000001",
            accession="0000000001-26-000001",
            statement_type="income_statement",
            code="displayed_table_absent",
            latest=_Latest(),
            pin_by_pair={},
            pin_triples=set(),
            golden_accessions=frozenset(),
        )
    assert caught.value.code == "statement_refusal_unpinned"


def test_r6_unpinned_refusal_first_publication_fails() -> None:
    with pytest.raises(producer.PublisherError) as caught:
        producer._classify_statement_refusal(
            ticker="SYN",
            cik="0000000001",
            accession="0000000001-26-000001",
            statement_type="income_statement",
            code="displayed_table_absent",
            latest=None,
            pin_by_pair={},
            pin_triples=set(),
            golden_accessions=frozenset(),
        )
    assert caught.value.code == "statement_refusal_unpinned"
    assert "first_publication" in str(caught.value)


def test_r6_unpinned_refusal_golden_accession_fails() -> None:
    accession = sorted(GOLDEN_AAPL_FIXTURES)[0]

    class _Latest:
        def statement_accessions(self):
            return ()

    with pytest.raises(producer.PublisherError) as caught:
        producer._classify_statement_refusal(
            ticker="AAPL",
            cik="0000320193",
            accession=accession,
            statement_type="income_statement",
            code="displayed_table_absent",
            latest=_Latest(),
            pin_by_pair={},
            pin_triples=set(),
            golden_accessions=frozenset({accession}),
        )
    assert "golden_accession" in str(caught.value)


def test_r6_pinned_code_changed_fails() -> None:
    class _Latest:
        def statement_accessions(self):
            return ()

    with pytest.raises(producer.PublisherError) as caught:
        producer._classify_statement_refusal(
            ticker="BAC",
            cik="0000070858",
            accession="0000070858-24-000122",
            statement_type="income_statement",
            code="displayed_table_absent",
            latest=_Latest(),
            pin_by_pair={("0000070858-24-000122", "income_statement"): "statement_role_not_consolidated"},
            pin_triples=set(),
            golden_accessions=frozenset(),
        )
    assert "pinned_code_changed" in str(caught.value)


def test_r6_resolved_pinned_refusal_reported_with_warning() -> None:
    class _Package:
        manifest = {"accession": "0000070858-24-000122"}

    class _Staged:
        binding = type("B", (), {"ticker": "BAC", "cik": "0000070858"})()
        admitted_packages = (_Package(),)

    plan = producer._IssuerPlan(
        staged=_Staged(),
        outcome="published",
        clock_basis="content",
        admitted_at=datetime.now(timezone.utc),
        generation_id="gen",
        manifest_key="m",
        lineage_receipt_count=0,
    )
    resolved = producer._resolved_pin_rows_for_issuer(
        plan,
        {("0000070858-24-000122", "income_statement", "statement_role_not_consolidated")},
        set(),
    )
    assert resolved == [
        {
            "ticker": "BAC",
            "cik": "0000070858",
            "accession": "0000070858-24-000122",
            "statement_type": "income_statement",
            "code": "statement_role_not_consolidated",
        }
    ]


def test_r6_k_pinned_regressed_from_latest_fails() -> None:
    class _Latest:
        def statement_accessions(self):
            return ("0000070858-24-000122",)

        def statement_trees(self, accession):
            return {
                "statements": [
                    {
                        "statement_type": "income_statement",
                        "role_uri": "r",
                        "title": "t",
                        "columns": [],
                        "row_count": 1,
                        "rows": [{"cells": []}],
                    }
                ]
            }

    with pytest.raises(producer.PublisherError):
        producer._classify_statement_refusal(
            ticker="BAC",
            cik="0000070858",
            accession="0000070858-24-000122",
            statement_type="income_statement",
            code="statement_role_not_consolidated",
            latest=_Latest(),
            pin_by_pair={},
            pin_triples={
                ("0000070858-24-000122", "income_statement", "statement_role_not_consolidated")
            },
            golden_accessions=frozenset(),
        )


def test_r6_l_latest_pointer_unreadable_fails() -> None:
    class _Latest:
        def statement_accessions(self):
            raise ProductionDatasetError("torn")

        def statement_trees(self, accession):
            raise ProductionDatasetError("torn")

    with pytest.raises(producer.PublisherError) as caught:
        producer._classify_statement_refusal(
            ticker="BAC",
            cik="0000070858",
            accession="0000070858-24-000122",
            statement_type="income_statement",
            code="statement_role_not_consolidated",
            latest=_Latest(),
            pin_by_pair={},
            pin_triples={
                ("0000070858-24-000122", "income_statement", "statement_role_not_consolidated")
            },
            golden_accessions=frozenset(),
        )
    assert caught.value.code == "statement_refusal_unpinned"


def test_r6_readback_production_dataset_error_fails_run(monkeypatch) -> None:
    def _boom(*_a, **_k):
        raise ProductionDatasetError("malformed")

    monkeypatch.setattr(producer, "load_generation", _boom)
    plan = producer._IssuerPlan(
        staged=type(
            "S",
            (),
            {
                "binding": type("B", (), {"entity_id": "ISS:X", "ticker": "X", "cik": "0000000000"})(),
                "admitted_packages": (),
            },
        )(),
        outcome="published",
        clock_basis="content",
        admitted_at=datetime.now(timezone.utc),
        generation_id="gen",
        manifest_key="m",
        lineage_receipt_count=0,
    )
    with pytest.raises(producer.PublisherError):
        producer._readback_issuer_refusals(None, plan, registry=object())


def test_r6_unchanged_plan_reports_refusals_from_comparison(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    accession = identity["accessions"][0]
    contract, _ = _three_issuer_contract(tmp_path, identity)
    assert _capture_cli(lane, contract) == 0
    _mutate_lane_manifest(lane, accession, _partial_refusal_roles(identity, accession))
    store = tmp_path / "store"
    first_report = tmp_path / "r1.json"
    _stage_three_issuers_coherently(monkeypatch)
    monkeypatch.setattr(
        producer,
        "_load_statement_refusal_pin",
        lambda: _pin_partial_income_refusal(accession),
    )
    assert _publish_cli(lane, contract, store, first_report) == 0
    second_report = tmp_path / "r2.json"
    rc = _publish_cli(lane, contract, store, second_report, clock=RUN_CLOCK)
    assert rc == 0
    report = json.loads(second_report.read_text(encoding="utf-8"))
    assert report["statement_refusals"]


def _minimal_refusal_report(reason: str, served: bool = False) -> dict:
    return {
        "published": [],
        "excluded": [{"ticker": "SNOW", "cik": "0001640147", "reason": reason}],
        "coverage": [
            {
                "cik": "0001640147",
                "served": int(served),
                "accessions": [
                    {
                        "accession": "0001640147-26-000001",
                        "admitted": True,
                        "served": served,
                    }
                ],
            }
        ],
    }


def test_a0_verify_admits_only_the_closed_refusal_vocabulary(tmp_path) -> None:
    store = producer.build_production_dataset_store(local_dir=tmp_path / "store")
    for slug in sorted(producer.STATEMENT_REFUSAL_SLUGS):
        producer.verify_report(
            _minimal_refusal_report(f"statement_reconstruction_refused:{slug}"), store
        )
    for bad in ("statement_reconstruction_refused:bogus", "statement_reconstruction_refused"):
        with pytest.raises(producer.PublisherError) as caught:
            producer.verify_report(_minimal_refusal_report(bad), store)
        assert caught.value.code == "verify_failed"
    with pytest.raises(producer.PublisherError, match="excluded issuer") as caught:
        producer.verify_report(
            _minimal_refusal_report(
                "statement_reconstruction_refused:displayed_table_absent", served=True
            ),
            store,
        )
    assert caught.value.code == "verify_failed"
