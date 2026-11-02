"""FIF A0-SE receipts: a two-generation LOCAL fixture store + SAFE-ENV receipts.

WHY THIS EXISTS
---------------
A0-SE needs SE-1 (a newer generation supersedes) and SE-2 (forbidden or future
cutoff) observed through the INSTALLED API and the browser page, without any
production store, network, credential or A45 entitlement. This module:

* builds a real two-generation LocalStore through the REAL publisher CLI
  (``scripts.publish_fif_production_datasets``) using the same offline fakes
  the publisher tests use (imported, never edited);
* runs the API receipts through the REAL ``app.forensics.router`` with
  ``FIF_FINANCIAL_DATASET_MODE=production`` and
  ``FIF_PRODUCTION_DATASET_LOCAL_STORE=<store>`` set only inside a scoped env
  context, entitlement satisfied only by the repository's router-test
  dependency override;
* writes ``api_receipts.json`` rows that each carry
  ``evidence_class: "SAFE-ENV local fixture store - not production, not A45"``.

Night 1 captures/publishes the two committed golden AAPL fixtures at clock T1
(admitted_at = T1, clock_basis=content). Night 2 publishes a second
generation at T2:

* ``mode="correction"`` stages, in the TEMP lane only, a derived amended
  filing (10-K/A, same fiscal period, ONE changed fact value) rebuilt from
  the existing golden fixture bytes in tmp — nothing derived ever enters git.
  The publisher's real converter mints every fact as ``FILED``
  (engine/fundamental_forensics/ixbrl_raw_ledger.py:401), so the changed
  value arrives as a second SOURCE VINTAGE, not an AMENDMENT-linked revision
  event; receipts record exactly that.
* ``mode="supersession"`` is the ``_empty_mint`` pattern: generation 2 with
  the same content and a new admitted_at. That is generation supersession,
  NOT a source correction.

This module lives under ``tests/tools/`` on purpose: it is evidence tooling,
never product code. It originates no signal, score or escalation (A7).
"""
from __future__ import annotations

import contextlib
import gzip
import hashlib
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

SAFE_ENV_CLASS = "SAFE-ENV local fixture store - not production, not A45"

MODE_CORRECTION = "correction"
MODE_SUPERSESSION = "supersession"
MODES = (MODE_CORRECTION, MODE_SUPERSESSION)

# The amended fact: the FY revenue concept in the 10-K primary document. The
# display token swap keeps the byte length identical, so the fixture's archive
# index (which carries member sizes) stays valid without regeneration.
#
# The corrected package is staged under form "10-K", NOT "10-K/A": the capture
# member policy is keyed by the exact contract form and refuses "10-K/A"
# (FifMemberCaptureError form_not_in_member_policy,
# engine/fundamental_forensics/fif_member_capture.py:175-189), while admission
# itself is form-agnostic for statement filings. The real publisher CLI
# therefore admits the correction as a SECOND 10-K vintage for the same
# fiscal period — recorded verbatim in the receipts.
_AMENDMENT_FORM = "10-K"
_AMENDMENT_CONCEPT = "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"
_AMENDMENT_CONTEXT = "c-1"
_VALUE_BEFORE_TOKEN = b"416,161"
_VALUE_AFTER_TOKEN = b"416,916"

# Names only, never values: the scrub guarantees the in-process router answers
# from the LOCAL fixture store only.
_SCRUB_ENV_PREFIXES = ("R2_", "FF_ATTESTED_", "AWS_")
_SCRUB_ENV_NAMES = ("RESEARCH_LOCAL_STORE", "FIF_FINANCIAL_DATASET_MODE")

HEALTH_PATH = "/api/forensics/health"
QUERY_PATH = "/api/forensics/v1/financial/query"
REVISIONS_PATH = "/api/forensics/v1/financial/revisions"
STATEMENTS_PATH = "/api/forensics/v1/financial/statements"

_PROD_MODE = "FIF_FINANCIAL_DATASET_MODE"
_PROD_STORE = "FIF_PRODUCTION_DATASET_LOCAL_STORE"


# ---------------------------------------------------------------------------
# small scoped-env helpers
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def _scoped_env(pairs: Mapping[str, str | None]) -> Iterator[None]:
    """Set/restore env names; a None value removes the name."""
    saved: dict[str, str | None] = {}
    try:
        for name, value in pairs.items():
            saved[name] = os.environ.get(name)
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        yield
    finally:
        for name, old in saved.items():
            if old is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = old


@contextlib.contextmanager
def scrubbed_process_env() -> Iterator[list[str]]:
    """Remove store/mode env names (names recorded, values never)."""
    removed: list[str] = []
    saved: dict[str, str] = {}
    try:
        for name in sorted(os.environ):
            if name.startswith(_SCRUB_ENV_PREFIXES) or name in _SCRUB_ENV_NAMES:
                saved[name] = os.environ.pop(name)
                removed.append(name)
        yield removed
    finally:
        for name, value in saved.items():
            os.environ[name] = value


@contextlib.contextmanager
def production_store_env(store_dir: str | Path) -> Iterator[None]:
    """Scrub, then select production mode over the LOCAL fixture store."""
    with scrubbed_process_env():
        with _scoped_env({_PROD_MODE: "production", _PROD_STORE: str(store_dir)}):
            yield


# ---------------------------------------------------------------------------
# publisher-lane helpers (imported from the publisher test module; never edited)
# ---------------------------------------------------------------------------


def _publisher_module() -> Any:
    import tests.test_fundamental_forensics_production_publisher as pub  # noqa: PLC0415

    return pub


@contextlib.contextmanager
def offline_collector_env(
    extra_served: Mapping[str, Mapping[str, bytes]] | None = None,
) -> Iterator[dict[str, Any]]:
    """The publisher tests' offline fakes, as a context manager.

    Same monkeypatch targets as the ``offline_collector`` fixture
    (``producer.SecFilingArchiveCollector`` + ``producer.SecRequestPacer``),
    applied here by try/finally so the builder runs outside pytest too.
    """
    pub = _publisher_module()
    import scripts.publish_fif_production_datasets as producer  # noqa: PLC0415

    served = dict(pub._served_members())
    if extra_served:
        served.update({key: dict(value) for key, value in extra_served.items()})
    collectors: list[Any] = []
    pacers: list[Any] = []

    def _collector_factory(cache_root: Any, **kwargs: Any) -> Any:
        pacer = kwargs["pacer"]
        collector = pub._FakeCollector(cache_root, served, pacer)
        collectors.append(collector)
        return collector

    def _pacer_factory(**kwargs: Any) -> Any:
        pacer = pub._no_sleep_pacer(**kwargs)
        pacers.append(pacer)
        return pacer

    saved_collector = producer.SecFilingArchiveCollector
    saved_pacer = producer.SecRequestPacer
    producer.SecFilingArchiveCollector = _collector_factory
    producer.SecRequestPacer = _pacer_factory
    try:
        yield {"collectors": collectors, "pacers": pacers, "served": served}
    finally:
        producer.SecFilingArchiveCollector = saved_collector
        producer.SecRequestPacer = saved_pacer


def _materialize_lane_at(tmp_dir: Path, capture_clock: str) -> dict[str, Any]:
    """``_materialize_lane`` with OUR capture clock on every retained row.

    The publisher test helper hardcodes its own CAPTURE_CLOCK into the
    submissions receipt and the retained manifests; the content clock of
    generation 1 is max(capture clocks, rule clocks, registry clocks), so the
    retained rows must carry OUR T1 for admitted_at(generation 1) to equal T1.
    """
    pub = _publisher_module()
    from collectors.sec_document_spine import (  # noqa: PLC0415
        persist_archive_document,
        retain_filing_manifest,
        with_document_retrievals,
    )
    from engine.fundamental_forensics.sec_document_spine import (  # noqa: PLC0415
        build_filing_manifests,
    )

    identity = pub._fixture_identity()
    raw_root = tmp_dir / "raw"
    archive_root = tmp_dir / "archive"
    raw_root.mkdir(parents=True, exist_ok=True)
    archive_root.mkdir(parents=True, exist_ok=True)
    _write_submissions_at(pub, raw_root, identity, capture_clock)
    submissions = pub._synthetic_submissions(identity)
    by_accession = {
        m["filing"]["accession"]: m
        for m in build_filing_manifests(
            submissions,
            cik=identity["cik"],
            ticker=identity["ticker"],
            recorded_at=capture_clock,
        )
    }
    for accession in identity["accessions"]:
        manifest = by_accession[accession]
        primary = next(item for item in manifest["documents"] if item["role"] == "primary")
        fixture = pub.ROOT / pub.GOLDEN_AAPL_FIXTURES[accession]
        primary_bytes = (fixture / "members" / primary["document_name"]).read_bytes()
        receipt = persist_archive_document(
            archive_root, primary, primary_bytes, retrieved_at=capture_clock
        )
        materialized = with_document_retrievals(
            manifest, {str(primary["document_id"]): receipt.to_dict()}
        )
        retain_filing_manifest(archive_root, materialized)
    return {"identity": identity, "raw_root": raw_root, "archive_root": archive_root}


def _write_submissions_at(
    pub: Any, raw_root: Path, identity: dict, clock: str, *, extra_row: dict | None = None
) -> None:
    """``_write_submissions`` mirrored with OUR clock (+ optional amended row)."""
    payload_doc = pub._synthetic_submissions(identity)
    if extra_row is not None:
        for column, values in extra_row.items():
            payload_doc["filings"]["recent"][column] = [
                *payload_doc["filings"]["recent"][column],
                *values,
            ]
    cik = identity["cik"]
    payload = json.dumps(payload_doc).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    object_path = f"{cik}/submissions/{digest[:32]}.json.gz"
    target = raw_root / object_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(gzip.compress(payload))
    pointer = {
        "schema": "fundamental_forensics_retrieval.v1",
        "cik": cik,
        "endpoint": "submissions",
        # Same offline canonical URL text the publisher test helper writes.
        "url": f"https://data.sec.gov/submissions/CIK{cik}.json",
        "retrieved_at": clock,
        "sha256": digest,
        "bytes": len(payload),
        "object_path": object_path,
        "http_etag": None,
        "http_last_modified": None,
    }
    (raw_root / cik / "submissions" / "latest.json").parent.mkdir(
        parents=True, exist_ok=True
    )
    (raw_root / cik / "submissions" / "latest.json").write_text(
        json.dumps(pointer), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# correction mode: the derived amended filing (TEMP lane only, never in git)
# ---------------------------------------------------------------------------


def _derive_amended_members(pub: Any, identity: dict) -> tuple[str, dict[str, bytes]]:
    """Copy the 10-K golden fixture in tmp with ONE changed fact value.

    Returns ``(amended_accession, members)`` where ``members`` is the served
    member set for the derived accession (index.json unchanged — the digit
    swap preserves the primary document's byte length and the index's sizes).
    """
    source_accession = identity["accessions"][0]
    amended_accession = source_accession[:-1] + str((int(source_accession[-1]) + 2) % 10)
    fixture = pub.ROOT / pub.GOLDEN_AAPL_FIXTURES[source_accession]
    primary_name = str(identity["manifests"][source_accession]["primary_document"])
    primary = (fixture / "members" / primary_name).read_bytes()
    token_re = re.compile(
        (
            rb'(<ix:nonFraction[^>]*name="' + _AMENDMENT_CONCEPT.encode() + rb'"[^>]*>)'
            rb"([^<]*)(</ix:nonFraction>)"
        )
    )
    changed = 0

    def _swap(match: re.Match[bytes]) -> bytes:
        nonlocal changed
        inner = match.group(2)
        if inner == _VALUE_BEFORE_TOKEN:
            changed += 1
            return match.group(1) + _VALUE_AFTER_TOKEN + match.group(3)
        return match.group(0)

    amended_primary = token_re.sub(_swap, primary)
    if changed == 0 or _VALUE_AFTER_TOKEN not in amended_primary:
        raise RuntimeError("amended primary document did not change any fact value")
    members: dict[str, bytes] = {"index.json": (fixture / "index.json").read_bytes()}
    for path in sorted((fixture / "members").iterdir()):
        members[path.name] = (
            amended_primary if path.name == primary_name else path.read_bytes()
        )
    return amended_accession, members


def _amendment_row(identity: dict, amended_accession: str, form: str, filing_date: str,
                   report_date: str, accepted_at: str, primary_document: str) -> dict:
    return {
        "accessionNumber": [amended_accession],
        "form": [form],
        "filingDate": [filing_date],
        "reportDate": [report_date],
        "acceptanceDateTime": [accepted_at],
        "primaryDocument": [primary_document],
        "isXBRL": [True],
        "isInlineXBRL": [True],
    }


def _retain_amended_primary(
    pub: Any,
    lane: dict,
    submissions_doc: dict,
    amended_accession: str,
    amended_primary: bytes,
    clock: str,
) -> None:
    from collectors.sec_document_spine import (  # noqa: PLC0415
        persist_archive_document,
        retain_filing_manifest,
        with_document_retrievals,
    )
    from engine.fundamental_forensics.sec_document_spine import (  # noqa: PLC0415
        build_filing_manifests,
    )

    identity = lane["identity"]
    manifests = build_filing_manifests(
        submissions_doc,
        cik=identity["cik"],
        ticker=identity["ticker"],
        recorded_at=clock,
    )
    manifest = next(m for m in manifests if m["filing"]["accession"] == amended_accession)
    primary = next(item for item in manifest["documents"] if item["role"] == "primary")
    receipt = persist_archive_document(
        lane["archive_root"], primary, amended_primary, retrieved_at=clock
    )
    materialized = with_document_retrievals(
        manifest, {str(primary["document_id"]): receipt.to_dict()}
    )
    retain_filing_manifest(lane["archive_root"], materialized)


# ---------------------------------------------------------------------------
# S2: the store builder
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StoreBuild:
    mode: str
    store_dir: str
    night1_store_dir: str
    generation_ids: dict[str, str]
    admitted_at: dict[str, str]
    entity_id: str
    amendment: dict[str, Any] | None

    def summary(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "store_dir": self.store_dir,
            "night1_store_dir": self.night1_store_dir,
            "generation_ids": dict(self.generation_ids),
            "admitted_at": dict(self.admitted_at),
            "entity_id": self.entity_id,
            "amendment": self.amendment,
            "evidence_class": SAFE_ENV_CLASS,
        }


def _read_published_row(report_path: Path) -> dict[str, Any]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    return report["published"][0]


def build_two_generation_store(
    tmp_dir: str | Path,
    t1: str,
    t2: str,
    *,
    mode: str = MODE_CORRECTION,
) -> StoreBuild:
    """Build the two-generation LOCAL fixture store under ``tmp_dir``.

    Night 1: capture + publish the two committed golden fixtures at ``t1``
    (admitted_at = t1, clock_basis=content). Night 2: publish generation 2 at
    ``t2`` — a corrected package (mode="correction") or the ``_empty_mint``
    supersession (mode="supersession"). The store after night 1 is snapshotted
    to ``night1_store`` so receipts can also observe generation 1 through the
    installed API. Nothing is written outside ``tmp_dir``.
    """
    if mode not in MODES:
        raise ValueError(f"unknown mode: {mode!r}")
    pub = _publisher_module()
    import scripts.publish_fif_production_datasets as producer  # noqa: PLC0415

    tmp = Path(tmp_dir)
    tmp.mkdir(parents=True, exist_ok=True)
    store = tmp / "store"
    report_path = tmp / "publish_report.json"
    lane_root = tmp / "lane"
    if lane_root.exists():
        shutil.rmtree(lane_root)

    # ---- night 1 -----------------------------------------------------------
    lane = _materialize_lane_at(lane_root, t1)
    identity = lane["identity"]
    contract = pub._write_contract(tmp, identity, None)
    amendment: dict[str, Any] | None = None
    with offline_collector_env():
        rc = pub._capture_cli(lane, contract, clock=t1)
        if rc != 0:
            raise RuntimeError(f"night-1 capture failed with rc={rc}")
        rc = pub._publish_cli(lane, contract, store, report_path, clock=t1)
        if rc != 0:
            raise RuntimeError(f"night-1 publish failed with rc={rc}")
    row1 = _read_published_row(report_path)
    generation_1 = str(row1["generation_id"])
    admitted_1 = str(row1["admitted_at"])
    night1_store = tmp / "night1_store"
    if night1_store.exists():
        shutil.rmtree(night1_store)
    shutil.copytree(store, night1_store)

    # ---- night 2 -----------------------------------------------------------
    if mode == MODE_CORRECTION:
        amended_accession, amended_members = _derive_amended_members(pub, identity)
        source_accession = identity["accessions"][0]
        primary_document = str(identity["manifests"][source_accession]["primary_document"])
        report_date = str(identity["manifests"][source_accession]["period_of_report"])
        amendment = {
            "amended_accession": amended_accession,
            "amends_accession": source_accession,
            "form": _AMENDMENT_FORM,
            "form_note": (
                "staged as a second 10-K vintage: the capture member policy "
                "refuses '10-K/A' (form_not_in_member_policy)"
            ),
            "concept_qname": _AMENDMENT_CONCEPT,
            "context_id": _AMENDMENT_CONTEXT,
            "value_before_token": _VALUE_BEFORE_TOKEN.decode(),
            "value_after_token": _VALUE_AFTER_TOKEN.decode(),
            "note": (
                "derived in the TEMP lane from the committed golden fixture bytes; "
                "the publisher's real converter mints every fact as FILED, so the "
                "changed value arrives as a second source vintage, not an "
                "AMENDMENT-linked revision event"
            ),
        }
        row = _amendment_row(
            identity,
            amended_accession,
            _AMENDMENT_FORM,
            filing_date=t2[:10],
            report_date=report_date,
            accepted_at=t2,
            primary_document=primary_document,
        )
        _write_submissions_at(pub, lane["raw_root"], identity, t1, extra_row=row)

        def _submissions_with_amendment() -> dict:
            doc = pub._synthetic_submissions(identity)
            for column, values in row.items():
                doc["filings"]["recent"][column] = [
                    *doc["filings"]["recent"][column],
                    *values,
                ]
            return doc

        _retain_amended_primary(
            pub,
            lane,
            _submissions_with_amendment(),
            amended_accession,
            amended_members[primary_document],
            t2,
        )
        contract2_path = tmp / "contract_night2.json"
        contract2 = json.loads(contract.read_text(encoding="utf-8"))
        contract2["issuers"][0]["accessions"].append(
            {
                "accession": amended_accession,
                "form": _AMENDMENT_FORM,
                "filing_date": t2[:10],
            }
        )
        contract2_path.write_text(json.dumps(contract2, indent=1), encoding="utf-8")
        with offline_collector_env(
            extra_served={amended_accession.replace("-", ""): amended_members}
        ):
            rc = pub._capture_cli(lane, contract2_path, clock=t2)
            if rc != 0:
                raise RuntimeError(f"night-2 capture failed with rc={rc}")
            rc = pub._publish_cli(lane, contract2_path, store, report_path, clock=t2)
            if rc != 0:
                raise RuntimeError(f"night-2 publish failed with rc={rc}")
    else:
        saved_mint = producer.mint_production_lineage_evidence
        producer.mint_production_lineage_evidence = pub._empty_mint
        try:
            with offline_collector_env():
                rc = pub._publish_cli(lane, contract, store, report_path, clock=t2)
                if rc != 0:
                    raise RuntimeError(f"night-2 publish failed with rc={rc}")
        finally:
            producer.mint_production_lineage_evidence = saved_mint

    row2 = _read_published_row(report_path)
    generation_2 = str(row2["generation_id"])
    admitted_2 = str(row2["admitted_at"])
    if generation_2 == generation_1:
        raise RuntimeError("night 2 did not mint a new generation")
    return StoreBuild(
        mode=mode,
        store_dir=str(store),
        night1_store_dir=str(night1_store),
        generation_ids={"generation_1": generation_1, "generation_2": generation_2},
        admitted_at={"generation_1": admitted_1, "generation_2": admitted_2},
        entity_id=str(identity["entity_id"]),
        amendment=amendment,
    )


# ---------------------------------------------------------------------------
# S3: API receipts through the REAL router
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReceiptRow:
    case: str
    request: dict[str, Any]
    status: int
    observed: dict[str, Any]
    expected: str
    verdict: str
    r1_status: int | None = None
    r1_note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        row = {
            "case": self.case,
            "request": self.request,
            "status": self.status,
            "r1_status": self.r1_status,
            "observed": self.observed,
            "expected": self.expected,
            "verdict": self.verdict,
            "evidence_class": SAFE_ENV_CLASS,
        }
        if self.r1_note is not None:
            row["r1_note"] = self.r1_note
        return row


def _query_body(entity_id: str, cutoff: str, *, selection: str = "latest_known_as_of",
                metric_ids: tuple[str, ...] = ("revenue",),
                period: dict[str, str] | None = None) -> dict[str, Any]:
    return {
        "schema": "fundamental_forensics.financial_query_request/v1",
        "entity_id": entity_id,
        "policy": {
            "selection": selection,
            "source_snapshot_at": cutoff,
            "recorded_at": cutoff,
        },
        "metric_ids": list(metric_ids),
        "periods": [
            period
            if period is not None
            else {"kind": "duration", "start": "2024-09-29", "end": "2025-09-27",
                  "label": "FY2025"}
        ],
    }


def _revisions_body(entity_id: str, cutoff: str) -> dict[str, Any]:
    body = _query_body(entity_id, cutoff)
    body["schema"] = "fundamental_forensics.financial_revision_request/v1"
    return body


def _statements_body(entity_id: str, accession: str) -> dict[str, Any]:
    """A statement request: entity + accession only (the request carries no clock;
    the served generation is the store's latest pointer, admitted at T2 here)."""
    return {
        "schema": "fundamental_forensics.financial_statement_request/v1",
        "entity_id": entity_id,
        "accession": accession,
    }


def _excerpt(envelope: dict[str, Any]) -> dict[str, Any]:
    """Bind the generation + the revenue cell out of a query envelope."""
    nodes = envelope.get("receipt", {}).get("nodes", [])
    revenue = next((n for n in nodes if n.get("metric_id") == "revenue"), None)
    delivery = envelope.get("delivery") or {}
    out: dict[str, Any] = {
        "delivery_dataset_generation_id": delivery.get("dataset_generation_id"),
        "coverage": envelope.get("coverage"),
    }
    if revenue is not None:
        provenance = revenue.get("provenance") or {}
        out["revenue"] = {
            "state": revenue.get("state"),
            "value": revenue.get("value"),
            "unit": revenue.get("unit"),
            "reason": revenue.get("reason"),
            "accession": provenance.get("accession"),
            "recorded_at": provenance.get("recorded_at"),
            "accepted_at": provenance.get("accepted_at"),
        }
    return out


def _statements_excerpt(envelope: dict[str, Any]) -> dict[str, Any]:
    """Bind the generation, the filing identity and the amended-concept cells."""
    statements = envelope.get("statements") or []
    filing = envelope.get("filing") or {}
    out: dict[str, Any] = {
        "delivery_dataset_generation_id": (envelope.get("delivery") or {}).get(
            "dataset_generation_id"
        ),
        "filing": {
            "accession": filing.get("accession"),
            "form": filing.get("form"),
            "period_of_report": filing.get("period_of_report"),
            "filing_date": filing.get("filing_date"),
        },
        "statement_titles": [s.get("title") for s in statements],
        "coverage": envelope.get("coverage"),
    }
    changed = []
    # The amended concept arrives as a Clark-notation qname
    # ({http://fasb.org/us-gaap/…}LocalName); match on the local name.
    local_concept = _AMENDMENT_CONCEPT.split(":", 1)[1]
    for statement in statements:
        for row in statement.get("rows", []):
            for cell in row.get("cells", []):
                receipt = cell.get("source_receipt") or {}
                qname = str(receipt.get("concept_qname") or "")
                qname_local = qname.rsplit("}", 1)[-1].rsplit(":", 1)[-1]
                if (
                    receipt.get("context_ref") == _AMENDMENT_CONTEXT
                    and qname_local == local_concept
                ):
                    changed.append(
                        {
                            "statement": statement.get("title"),
                            "value": cell.get("value"),
                            "period": cell.get("period"),
                        }
                    )
    if changed:
        out["amended_concept_cells"] = changed
    return out


def _reset_provider_caches() -> None:
    import app.forensics as forensics_api  # noqa: PLC0415

    forensics_api._reset_production_provider_cache()


@contextlib.contextmanager
def _router_client() -> Iterator[Any]:
    """REAL router + the repository's router-test dependency override ONLY."""
    from fastapi import FastAPI  # noqa: PLC0415
    from fastapi.testclient import TestClient  # noqa: PLC0415

    import app.forensics as forensics_api  # noqa: PLC0415

    app = FastAPI()
    app.include_router(forensics_api.router)
    app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {
        "id": "fif-se-receipts-local"
    }
    _reset_provider_caches()
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client
    finally:
        _reset_provider_caches()


def _post_json(client: Any, path: str, body: dict[str, Any]) -> tuple[int, dict, Any]:
    response = client.post(path, json=body)
    try:
        parsed = response.json()
    except Exception:  # noqa: BLE001 - a refusal body may be plain text
        parsed = response.text
    return response.status_code, dict(response.headers), parsed


def _run_cases(
    store_label: str, client: Any, entity_id: str, cutoffs: Mapping[str, str],
    expected_generation: str | None,
    *,
    statement_cases: Mapping[str, Mapping[str, Any]] | None = None,
    r1_statuses: Mapping[str, Any] | None = None,
    amended_accession: str | None = None,
) -> list[ReceiptRow]:
    rows: list[ReceiptRow] = []
    r1_map = dict(r1_statuses or {})

    def record(case: str, request: dict, status: int, headers: dict,
               observed: dict, expected: str, verdict: str) -> None:
        prior = r1_map.get(case)
        rows.append(
            ReceiptRow(
                case=case,
                request=request,
                status=status,
                observed={
                    "store": store_label,
                    "relevant_headers": {
                        name: headers.get(name)
                        for name in (
                            "x-fif-financial-dataset-mode",
                            "x-fif-dataset-generation-id",
                            "x-fif-dataset-admitted-at",
                            "x-fif-response-sha256",
                        )
                        if headers.get(name) is not None
                    }
                    or None,
                    **observed,
                },
                expected=expected,
                verdict=verdict,
                r1_status=(int(prior["status"]) if isinstance(prior, Mapping)
                           and prior.get("status") is not None else None),
                r1_note=(prior.get("r1_note") if isinstance(prior, Mapping) else None),
            )
        )

    # SE1-a: health headers name the latest generation and its admitted_at.
    if cutoffs.get("health") is not None:
        response = client.get(HEALTH_PATH)
        headers = dict(response.headers)
        gen = headers.get("x-fif-dataset-generation-id")
        adm = headers.get("x-fif-dataset-admitted-at")
        mode_header = headers.get("x-fif-financial-dataset-mode")
        ok = (
            response.status_code == 200
            and mode_header == "production"
            and gen == expected_generation
            and adm == cutoffs.get("expected_admitted_at")
        )
        record(
            "SE1-a" if store_label == "final" else f"SE1-a[{store_label}]",
            {"method": "GET", "path": HEALTH_PATH},
            response.status_code,
            headers,
            {
                "mode_header": mode_header,
                "generation_id": gen,
                "admitted_at": adm,
            },
            (
                "health headers name the served generation and its admitted_at "
                f"({expected_generation}, {cutoffs.get('expected_admitted_at')})"
            ),
            "PASS" if ok else "GAP",
        )

    def query_case(case: str, cutoff: str, expected: str, verdict_fn: Any,
                   extra_observed: Mapping[str, Any] | None = None) -> None:
        status, headers, payload = _post_json(
            client, QUERY_PATH, _query_body(entity_id, cutoff)
        )
        observed: dict[str, Any] = {"body_excerpt": None}
        if isinstance(payload, dict):
            observed["body_excerpt"] = _excerpt(payload)
        if extra_observed is not None:
            observed.update(extra_observed)
        record(case, {"method": "POST", "path": QUERY_PATH,
                      "cutoff": cutoff}, status, headers, observed, expected,
               verdict_fn(status, payload))

    # SE1-b: a cutoff at/after T2 serves generation 2.
    if cutoffs.get("se1b") is not None:
        cutoff = cutoffs["se1b"]

        def _se1b(status: int, payload: Any) -> str:
            excerpt = _excerpt(payload) if isinstance(payload, dict) else {}
            return (
                "PASS"
                if status == 200
                and excerpt.get("delivery_dataset_generation_id") == expected_generation
                else "GAP"
            )

        query_case(
            f"SE1-b" if store_label == "final" else f"SE1-b[{store_label}]",
            cutoff,
            f"query at cutoff >= T2 serves {expected_generation} "
            "(body binds it via delivery.dataset_generation_id)",
            _se1b,
        )

    # SE1-c: a cutoff strictly between T1 and T2.
    if cutoffs.get("se1c") is not None:
        cutoff = cutoffs["se1c"]

        def _se1c(status: int, payload: Any) -> str:
            excerpt = _excerpt(payload) if isinstance(payload, dict) else {}
            gen = excerpt.get("delivery_dataset_generation_id")
            if status == 200 and gen is not None:
                return "PASS" if store_label == "night1" else "GAP"
            # The installed API refuses: A12 admission floor (query_service).
            return "PASS" if status == 503 else "GAP"

        expected = (
            "cutoff strictly between T1 and T2 serves generation 1"
            if store_label == "night1"
            else "cutoff strictly between T1 and T2: the installed API serves only the "
            "latest generation and the A12 admission floor (recorded_at < "
            "admitted_at) returns the typed 503 unavailability — generation-1 "
            "bytes are observable only while generation 1 is the latest pointer "
            "(see the night1 rows)"
        )
        query_case(
            "SE1-c" if store_label == "final" else f"SE1-c[{store_label}]",
            cutoff,
            expected,
            _se1c,
        )

    # SE2-a: a cutoff before the first admission.
    if cutoffs.get("se2a") is not None:
        cutoff = cutoffs["se2a"]

        def _se2a(status: int, payload: Any) -> str:
            return "PASS" if status == 503 else "GAP"

        query_case(
            f"SE2-a" if store_label == "final" else f"SE2-a[{store_label}]",
            cutoff,
            "cutoff before the first admission gives the typed absence: "
            "FinancialQueryUnavailableError -> private 503 "
            "'financial query temporarily unavailable' (A12 admission floor)",
            _se2a,
        )

    # SE2-b: a future cutoff. SEAT RULING (r2): OBSERVED-ALLOWED is the
    # accepted request-path law (no wall clock exists there); pin 200 AND
    # assert the delivery generation binding so the answer is traceable.
    if cutoffs.get("se2b") is not None:
        cutoff = cutoffs["se2b"]
        status, headers, payload = _post_json(
            client, QUERY_PATH, _query_body(entity_id, cutoff)
        )
        excerpt = _excerpt(payload) if isinstance(payload, dict) else {}
        gen = excerpt.get("delivery_dataset_generation_id")
        verdict = (
            (
                "OBSERVED-ALLOWED"
                if gen is not None and gen == expected_generation
                else "GAP"
            )
            if status == 200
            else ("PASS" if status >= 400 else "GAP")
        )
        record(
            "SE2-b",
            {"method": "POST", "path": QUERY_PATH, "cutoff": cutoff},
            status,
            headers,
            {
                "body_excerpt": excerpt or None,
                "delivery_generation_binding": (
                    {
                        "dataset_generation_id": gen,
                        "store_pointer_admitted_at": cutoffs.get("expected_admitted_at"),
                        "generation_matches_store_pointer": gen == expected_generation,
                    }
                    if isinstance(payload, dict)
                    else None
                ),
            },
            "future cutoff: SEAT RULING — OBSERVED-ALLOWED is the request-path law "
            "(no wall clock on the request path); pinned as 200 WITH the delivery "
            "generation binding (generation id + the store pointer's admitted_at) "
            "so the answer is traceable",
            verdict,
        )

    # SE2-c: source_snapshot_at after recorded_at. Same seat ruling.
    if cutoffs.get("se2c") is not None:
        recorded = cutoffs.get("se2c_recorded") or cutoffs["se2c"]
        body = _query_body(entity_id, recorded)
        body["policy"]["source_snapshot_at"] = cutoffs["se2c"]
        status, headers, payload = _post_json(client, QUERY_PATH, body)
        excerpt = _excerpt(payload) if isinstance(payload, dict) else {}
        gen = excerpt.get("delivery_dataset_generation_id")
        verdict = (
            (
                "OBSERVED-ALLOWED"
                if gen is not None and gen == expected_generation
                else "GAP"
            )
            if status == 200
            else ("PASS" if status >= 400 else "GAP")
        )
        record(
            "SE2-c",
            {"method": "POST", "path": QUERY_PATH,
             "source_snapshot_at": cutoffs["se2c"],
             "recorded_at": recorded},
            status,
            headers,
            {
                "body_excerpt": excerpt or None,
                "delivery_generation_binding": (
                    {
                        "dataset_generation_id": gen,
                        "store_pointer_admitted_at": cutoffs.get("expected_admitted_at"),
                        "generation_matches_store_pointer": gen == expected_generation,
                    }
                    if isinstance(payload, dict)
                    else None
                ),
            },
            "source_snapshot_at > recorded_at: SEAT RULING — OBSERVED-ALLOWED "
            "(no ordering rule at admission); pinned as 200 WITH the delivery "
            "generation binding so the answer is traceable",
            verdict,
        )

    # SE1-e (r2): the production statements POST at the T2-admitted store.
    # r1 answered the private 503 on every store (D-1: manifests carried no
    # entity_id; D-2 behind it), which is what blocked every browser cell's
    # query chain. #9116 fixed both; record what it answers now, per store.
    if statement_cases:
        for case_name, spec in statement_cases.items():
            accession = str(spec["accession"])
            expect_status = int(spec.get("expect_status", 200))
            status, headers, payload = _post_json(
                client, STATEMENTS_PATH, _statements_body(entity_id, accession)
            )
            excerpt = _statements_excerpt(payload) if isinstance(payload, dict) else {}
            gen = excerpt.get("delivery_dataset_generation_id")
            if expect_status == 200:
                ok = status == 200 and gen == expected_generation
            else:
                ok = status == expect_status
            record(
                case_name,
                {"method": "POST", "path": STATEMENTS_PATH, "accession": accession,
                 "note": "the statement request carries no clock; the served "
                         "generation is this store's latest pointer (admitted at "
                         f"{cutoffs.get('expected_admitted_at')})"},
                status,
                headers,
                {"body_excerpt": excerpt or None},
                (
                    "statements POST serves the as-reported tree and binds the "
                    f"delivery generation ({expected_generation})"
                    if expect_status == 200
                    else f"statements POST for {accession} answers "
                         f"{expect_status} on this store (the filing did not "
                         "exist at this store's admission)"
                ),
                "PASS" if ok else "GAP",
            )

    # SE1-d (r2): /revisions through the real store. r1 answered the private
    # 503 everywhere (D-2: filing metadata keyed by accession while the packet
    # assembler resolves by occurrence id); #9116 re-keys it at the boundary
    # (revision_service.occurrence_keyed_filing_metadata). Record exactly what
    # it shows now: status, rows, and whether the corrected 10-K vintage
    # appears and how it is linked.
    if cutoffs.get("se1d") is not None:
        q_status, q_headers, q_payload = _post_json(
            client, QUERY_PATH, _query_body(entity_id, cutoffs["se1d"])
        )
        node_state = node_reason = None
        if isinstance(q_payload, dict):
            nodes = q_payload.get("receipt", {}).get("nodes", [])
            revenue = next((n for n in nodes if n.get("metric_id") == "revenue"), None)
            if revenue is not None:
                node_state = revenue.get("state")
                node_reason = revenue.get("reason")
        status, headers, payload = _post_json(
            client, REVISIONS_PATH, _revisions_body(entity_id, cutoffs["se1d"])
        )
        revisions = payload.get("revisions", []) if isinstance(payload, dict) else None
        appears = False
        if amended_accession and isinstance(revisions, list):
            appears = amended_accession in json.dumps(revisions)
        suffix = "" if store_label == "final" else f"[{store_label}]"
        corrected_note = (
            "the corrected 10-K vintage does NOT appear as a revision row: the "
            "publisher's real converter mints every fact FILED "
            "(ixbrl_raw_ledger.py:401), so it is admitted as an unlinked second "
            "10-K source vintage with no typed AMENDMENT lineage - consistent "
            "with the SE1-b seat ruling that an unlinked newer vintage is never "
            "silently chosen and typed revision lineage belongs to a later node"
            if amended_accession
            else "no amended filing exists on this store (supersession/night-1)"
        )
        record(
            f"SE1-d[revisions]{suffix}",
            {
                "method": "POST",
                "path": REVISIONS_PATH,
                "cutoff": cutoffs["se1d"],
                "query_state_at_same_cutoff": {
                    "revenue_state": node_state,
                    "revenue_reason": node_reason,
                    "query_status": q_status,
                },
            },
            status,
            headers,
            {
                "revisions_count": len(revisions) if revisions is not None else None,
                "revisions_excerpt": (
                    revisions[:3] if isinstance(revisions, list) else revisions
                ),
                "corrected_vintage": {
                    "amended_accession": amended_accession,
                    "appears_in_revisions": appears,
                    "linkage": corrected_note,
                },
            },
            "r2: /revisions answers through the real store (#9116 D-2 re-keys "
            "accession-keyed filing metadata onto occurrence ids); record "
            "status, rows, and whether the corrected 10-K vintage appears and "
            "how it is linked",
            "PASS" if status == 200 else "GAP",
        )

    return rows


def api_receipts(
    store_dir: str | Path,
    t1: str,
    t2: str,
    *,
    night1_store_dir: str | Path | None = None,
    entity_id: str | None = None,
    future_cutoff: str | None = None,
    supersession_store_dir: str | Path | None = None,
    primary_accession: str | None = None,
    amended_accession: str | None = None,
    r1_statuses: Mapping[str, Any] | None = None,
    out_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run the SE-1/SE-2 receipt matrix over the LOCAL fixture store(s)."""
    if entity_id is None:
        identity = _publisher_module()._fixture_identity()
        entity_id = str(identity["entity_id"])
    if primary_accession is None:
        primary_accession = _publisher_module()._fixture_identity()["accessions"][0]
    if future_cutoff is None:
        future_cutoff = (
            datetime.now(timezone.utc) + timedelta(days=2)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows: list[ReceiptRow] = []

    # SE1-e: the statements POST per store (r1: 503 behind every browser
    # cell). SE1-f: the same cases on the night-1 store, where the amended
    # filing genuinely did not exist at admission (expect the typed 400).
    final_statements: dict[str, dict[str, Any]] = {
        "SE1-e": {"accession": primary_accession},
    }
    night1_statements: dict[str, dict[str, Any]] = {
        "SE1-f[statements][night1]": {"accession": primary_accession},
    }
    if amended_accession:
        final_statements["SE1-e[amended]"] = {"accession": amended_accession}
        night1_statements["SE1-f[statements][amended][night1]"] = {
            "accession": amended_accession,
            "expect_status": 400,
        }

    with production_store_env(store_dir):
        from engine.fundamental_forensics.production_datasets import (  # noqa: PLC0415
            latest_generation_summary,
        )
        from engine.research_vault.r2_store import LocalStore  # noqa: PLC0415

        store = LocalStore(Path(store_dir))
        summary = latest_generation_summary(store, entity_id)
        if summary is None:
            raise RuntimeError(f"no generation found in {store_dir} for {entity_id}")
        generation_2 = summary["dataset_generation_id"]
        admitted_2 = summary["admitted_at"]

        with _router_client() as client:
            rows += _run_cases(
                "final",
                client,
                entity_id,
                {
                    "health": True,
                    "expected_admitted_at": admitted_2,
                    "se1b": t2,
                    "se1c": _between_cutoff(t1, t2),
                    "se2a": _before_cutoff(t1),
                    "se2b": future_cutoff,
                    "se2c": future_cutoff,
                    "se2c_recorded": t2,
                    "se1d": t2,
                },
                expected_generation=generation_2,
                statement_cases=final_statements,
                r1_statuses=r1_statuses,
                amended_accession=amended_accession,
            )

    night1_summary = None
    if night1_store_dir is not None:
        with production_store_env(night1_store_dir):
            from engine.fundamental_forensics.production_datasets import (  # noqa: PLC0415
                latest_generation_summary,
            )
            from engine.research_vault.r2_store import LocalStore  # noqa: PLC0415

            store1 = LocalStore(Path(night1_store_dir))
            night1_summary = latest_generation_summary(store1, entity_id)
            if night1_summary is None:
                raise RuntimeError(f"no generation in {night1_store_dir}")
            with _router_client() as client:
                rows += _run_cases(
                    "night1",
                    client,
                    entity_id,
                    {
                        "health": True,
                        "expected_admitted_at": night1_summary["admitted_at"],
                        "se1b": t2,
                        "se1c": _between_cutoff(t1, t2),
                        "se2a": _before_cutoff(t1),
                        "se1d": t2,
                    },
                    expected_generation=night1_summary["dataset_generation_id"],
                    statement_cases=night1_statements,
                    r1_statuses=r1_statuses,
                    amended_accession=amended_accession,
                )

    supersession_summary = None
    if supersession_store_dir is not None:
        with production_store_env(supersession_store_dir):
            from engine.fundamental_forensics.production_datasets import (  # noqa: PLC0415
                latest_generation_summary,
            )
            from engine.research_vault.r2_store import LocalStore  # noqa: PLC0415

            store_s = LocalStore(Path(supersession_store_dir))
            supersession_summary = latest_generation_summary(store_s, entity_id)
            if supersession_summary is None:
                raise RuntimeError(f"no generation in {supersession_store_dir}")
            with _router_client() as client:
                rows += _run_cases(
                    "supersession",
                    client,
                    entity_id,
                    {
                        "health": True,
                        "expected_admitted_at": supersession_summary["admitted_at"],
                        "se1b": t2,
                        "se1c": _between_cutoff(t1, t2),
                    },
                    expected_generation=supersession_summary["dataset_generation_id"],
                    statement_cases={
                        "SE1-e[supersession]": {"accession": primary_accession}
                    },
                    r1_statuses=r1_statuses,
                )

    document = {
        "schema": "fif_a0_se.api_receipts/v1",
        "evidence_class": SAFE_ENV_CLASS,
        "entity_id": entity_id,
        "clocks": {
            "t1_night1_admission": t1,
            "t2_night2_admission": t2,
            "between_cutoff": _between_cutoff(t1, t2),
            "before_first_admission": _before_cutoff(t1),
            "future_cutoff": future_cutoff,
        },
        "final_store": {
            "store_dir": str(store_dir),
            "dataset_generation_id": rows and _first_generation(rows),
        },
        "rows": [row.to_dict() for row in rows],
    }
    if night1_summary is not None:
        document["night1_store"] = {
            "store_dir": str(night1_store_dir),
            "dataset_generation_id": night1_summary["dataset_generation_id"],
            "admitted_at": night1_summary["admitted_at"],
        }
    if supersession_summary is not None:
        document["supersession_store"] = {
            "store_dir": str(supersession_store_dir),
            "dataset_generation_id": supersession_summary["dataset_generation_id"],
            "admitted_at": supersession_summary["admitted_at"],
            "note": (
                "generation supersession, NOT a source correction: the _empty_mint "
                "pattern moves the generation id and admitted_at without moving "
                "content — SE-1 stays partly owed on this store"
            ),
        }
    if out_path is not None:
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    return document


def _first_generation(rows: list[ReceiptRow]) -> str | None:
    for row in rows:
        if row.case == "SE1-a":
            return row.observed.get("generation_id")
    return None


def load_r1_statuses(r1_path: str | Path) -> dict[str, Any]:
    """r1's observed status per case, plus the r1 truth for the r2-new rows.

    The statements rows did not exist as direct API rows in r1: r1 observed
    the statements POST only behind the browser cells, where it answered the
    private 503 eight times per cell (D-1 manifest entity_id + D-2
    filing-metadata keying, both fixed by #9116). That observed 503 is the
    r1 status for the SE1-e/SE1-f primary rows; the amended-accession POST
    was never attempted in r1 (recorded as null with the reason).
    """
    path = Path(r1_path)
    statuses: dict[str, Any] = {}
    if path.is_file():
        doc = json.loads(path.read_text(encoding="utf-8"))
        for row in doc.get("rows", []):
            statuses[row["case"]] = {"status": row.get("status")}
    direct_503 = {
        "status": 503,
        "r1_note": (
            "r1 had no direct API statements row; r1 observed the statements "
            "POST only behind the browser cells, where it answered the private "
            "503 (D-1 manifest entity_id + D-2 filing-metadata keying, fixed "
            "by #9116)"
        ),
    }
    for case in ("SE1-e", "SE1-e[supersession]", "SE1-f[statements][night1]"):
        statuses.setdefault(case, dict(direct_503))
    for case in ("SE1-e[amended]", "SE1-f[statements][amended][night1]"):
        statuses.setdefault(
            case,
            {
                "status": None,
                "r1_note": "not attempted in r1 (no direct statements rows existed)",
            },
        )
    return statuses


def _between_cutoff(t1: str, t2: str) -> str:
    """The day-picker cutoff between T1 and T2: the last UTC day boundary."""
    day1 = t1[:10]
    day2 = t2[:10]
    if day1 == day2:
        raise ValueError("T1 and T2 must sit on different UTC days for a between cutoff")
    # D = the day before T2's day; D 23:59:59Z is after T1 iff T1 < that instant.
    between_day = (datetime.fromisoformat(day2 + "T00:00:00+00:00") - timedelta(days=1))
    cutoff = between_day.strftime("%Y-%m-%d") + "T23:59:59Z"
    if not (t1 < cutoff < t2):
        raise ValueError(f"no day-picker cutoff sits strictly between {t1} and {t2}")
    return cutoff


def _before_cutoff(t1: str) -> str:
    """A cutoff strictly before the first admission, on an earlier UTC day."""
    day = datetime.fromisoformat(t1[:10] + "T00:00:00+00:00") - timedelta(days=1)
    return day.strftime("%Y-%m-%d") + "T12:00:00Z"


def _shift_minutes(clock: str, minutes: int) -> str:
    """An ISO-Z clock shifted by whole minutes (still ISO-Z)."""
    shifted = datetime.fromisoformat(clock.replace("Z", "+00:00")) + timedelta(
        minutes=minutes
    )
    return shifted.strftime("%Y-%m-%dT%H:%M:%S+00:00")


# ---------------------------------------------------------------------------
# S5: browser receipts over the existing wrapper path (SAFE-ENV production)
# ---------------------------------------------------------------------------

TREE_ROOT = Path(__file__).resolve().parents[2]
_PUBLIC_SUMMARY_RELATIVE = "data/fundamental_forensics/public_summary.json"
_CAPTURE_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 FIF-A0-SE-evidence"
)


def route_for(path: str) -> str:
    return f"/fundamental_forensics.html{path}"


def _serve_site(site_dir: Path) -> tuple[str, Any]:
    """A loopback static server for the temp site dir (localhost only)."""
    import functools
    import http.server
    import threading

    class _Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args: Any) -> None:  # noqa: D102
            pass

    handler = functools.partial(_Quiet, directory=str(site_dir))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{httpd.server_address[1]}", httpd


def _materialize_kernel_inputs(dest_root: Path) -> list[str]:
    """Extract the read-only kernel inputs from LOCAL git objects into a temp root.

    The sparse lane tree omits ``data/``; the blobs are already in the local
    object cache, so ``git show`` (with lazy fetching disabled) needs no
    network. Nothing is written inside the tree.
    """
    import subprocess

    created: list[str] = []
    for relative in (*_capture_module().KERNEL_INPUTS, _PUBLIC_SUMMARY_RELATIVE):
        target = dest_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, "GIT_NO_LAZY_FETCH": "1"}
        result = subprocess.run(
            ["git", "show", f"HEAD:{relative}"],
            cwd=TREE_ROOT,
            capture_output=True,
            check=True,
            env=env,
        )
        target.write_bytes(result.stdout)
        created.append(relative)
    return created


def _capture_module() -> Any:
    import tests.tools.fif_p2_evidence_capture as capture  # noqa: PLC0415

    return capture


def prepare_browser_root(
    work_dir: Path, *, lane_dir: Path, t1: str, disclosure_as_of: str
) -> tuple[Path, dict[str, Any]]:
    """Temp site root: git-extracted inputs + offline disclosure projection + render.

    The page's day-picker query chain needs (i) entity bindings (issuer
    master), (ii) a READY disclosure track so the statements POST can resolve
    an accession and populate statement columns with real period starts. The
    committed inputs carry neither a disclosure projection (production
    artifact, untracked) nor two distinct-period filings of one form, so a
    prior-period 10-K copy — derived from the committed golden fixture bytes —
    is staged in a TEMP COPY of the lane (the published store is untouched).
    """
    import scripts.build_fundamental_forensics as builder  # noqa: PLC0415
    import scripts.build_fundamental_forensics_disclosures as disc  # noqa: PLC0415

    pub = _publisher_module()
    identity = pub._fixture_identity()
    root = work_dir / "browser_root"
    if root.exists():
        shutil.rmtree(root)
    (root / "data").mkdir(parents=True)
    _materialize_kernel_inputs(root)
    # The issuer master binds each CIK to its entity_id. Since X2-s the sixth
    # kernel input is data/reference/issuer_master.parquet, so the extraction
    # above already created root/data/reference — merge the tree's remaining
    # reference files over it (both are HEAD content; the sparse tree keeps
    # data/reference checked out) instead of r1's directory symlink.
    shutil.copytree(
        TREE_ROOT / "data" / "reference",
        root / "data" / "reference",
        dirs_exist_ok=True,
    )

    lane_copy = work_dir / "lane_with_prior_period"
    if lane_copy.exists():
        shutil.rmtree(lane_copy)
    shutil.copytree(lane_dir, lane_copy)
    source_accession = identity["accessions"][0]
    prior_accession = source_accession[:-1] + str((int(source_accession[-1]) + 4) % 10)
    primary_document = str(identity["manifests"][source_accession]["primary_document"])
    prior_report_date = "2024-09-28"
    row = _amendment_row(
        identity,
        prior_accession,
        "10-K",
        filing_date="2024-11-01",
        report_date=prior_report_date,
        accepted_at="2024-11-01T10:01:26Z",
        primary_document=primary_document,
    )
    _write_submissions_at(pub, lane_copy / "raw", identity, t1, extra_row=row)

    def _submissions_with_prior() -> dict:
        doc = pub._synthetic_submissions(identity)
        for column, values in row.items():
            doc["filings"]["recent"][column] = [
                *doc["filings"]["recent"][column],
                *values,
            ]
        return doc

    fixture = pub.ROOT / pub.GOLDEN_AAPL_FIXTURES[source_accession]
    prior_primary = (fixture / "members" / primary_document).read_bytes()
    _retain_amended_primary(
        pub,
        {"identity": identity, "archive_root": lane_copy / "archive"},
        _submissions_with_prior(),
        prior_accession,
        prior_primary,
        "2024-11-01T10:01:26Z",
    )
    summaries = disc.build_cached_disclosures(
        root,
        [identity["ticker"]],
        raw_root=lane_copy / "raw",
        archive_root=lane_copy / "archive",
        output_root=root,
        as_of=disclosure_as_of,
        computed_at=disclosure_as_of,
        cik_overrides={identity["ticker"]: int(identity["cik"])},
    )
    (root / "templates").symlink_to(
        TREE_ROOT / "templates", target_is_directory=True
    )
    shutil.copytree(TREE_ROOT / "site", root / "site")
    builder.render_shell(root)
    staging = {
        "staged_prior_accession": prior_accession,
        "staged_prior_report_date": prior_report_date,
        "note": (
            "a prior-period 10-K copy derived from the committed golden fixture "
            "bytes, staged in a TEMP COPY of the lane so the disclosure "
            "projection has two distinct report periods; the published store "
            "is untouched"
        ),
        "projection_summaries": summaries,
    }
    return root, staging


def browser_capture(
    *,
    work_dir: str | Path,
    out_dir: str | Path,
    stores: Mapping[str, str],
    lane_dir: str | Path,
    t1: str,
    generated_at: str,
    disclosure_as_of: str,
    cells: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    """Capture the SE-1/SE-2 browser matrix through the existing wrapper path.

    ``stores`` maps a store label to a LOCAL fixture store dir; ``cells`` maps
    the cell name (``B-1``..``B-6``) to ``{"as_of_day": ..., "store": label}``.
    The in-process router runs in production mode over the cell's store (the
    production store env is switched and the provider caches reset between
    cells); the private state is built from git-extracted inputs into a LOCAL
    store. entitlement = the router-test dependency override only.
    """
    capture = _capture_module()
    work = Path(work_dir)
    siteroot, staging = prepare_browser_root(
        work, lane_dir=Path(lane_dir), t1=t1, disclosure_as_of=disclosure_as_of
    )
    state_store = work / "browser_state_store"
    site_dir = siteroot / "site"
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    browser_dir = out / "browser"
    browser_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "schema": "fif_a0_se.browser_manifest/v1",
        "evidence_class": SAFE_ENV_CLASS,
        "stores": {label: str(d) for label, d in stores.items()},
        "state_store_dir": str(state_store),
        "generated_at": generated_at,
        "lane_staging": staging,
        "cells": [],
    }
    guard = capture.render_guard_refusals(
        tree_root=TREE_ROOT, site_dir=site_dir, base_url=None, route=route_for("")
    )
    if guard:
        manifest["error"] = f"render guard refused: {guard}"
        (browser_dir / "browser_manifest.json").write_text(
            json.dumps(manifest, indent=1) + "\n", encoding="utf-8"
        )
        return manifest
    env = {
        _PROD_MODE: "production",
        _PROD_STORE: str(Path(next(iter(stores.values()))).resolve()),
        "RESEARCH_LOCAL_STORE": str(state_store.resolve()),
    }
    with _scoped_env(env):
        from engine.fundamental_forensics import private_state  # noqa: PLC0415

        # Compose over the FULL temp root (unlike build_kernel_state, whose
        # temp root symlinks only the five KERNEL_INPUTS — that root cannot
        # bind entity_ids, so the compare tab would render no-entity). Same
        # real composer + atomic writer the wrapper's builder uses.
        import scripts.build_fundamental_forensics as builder  # noqa: PLC0415

        state = builder.compose_state(siteroot, generated_at=generated_at)
        blob_target = work / "state_blob.json.gz"
        builder._write_state_atomic(blob_target, state)
        blob = blob_target.read_bytes()
        capture.install_state_into_local_store(state_store, blob)
        manifest["state_blob_sha256"] = hashlib.sha256(blob).hexdigest()
        manifest["state_blob_bytes"] = len(blob)
        private_state.clear_state_cache()

        import app.forensics as forensics_api  # noqa: PLC0415

        forensics_api._reset_production_provider_cache()
        prior_repo = forensics_api.REPO
        forensics_api.REPO = TREE_ROOT
        try:
            router_app = capture.build_router_app(forensics_api, populated=True)
            from fastapi.testclient import TestClient  # noqa: PLC0415

            with TestClient(router_app, raise_server_exceptions=False) as client:
                origin, httpd = _serve_site(site_dir)
                try:
                    # The page must NOT see a loopback hostname (it would read
                    # the builder artifact), so navigate to the *.localhost
                    # name the wrapper uses; Chromium resolves it to loopback.
                    evidence_origin = origin.replace(
                        "//127.0.0.1:", "//fif-evidence.localhost:"
                    )
                    from playwright.sync_api import sync_playwright  # noqa: PLC0415

                    with sync_playwright() as playwright:
                        browser = playwright.chromium.launch()
                        try:
                            for cell_name, spec in cells.items():
                                store_label = str(spec["store"])
                                store_dir = str(
                                    Path(stores[store_label]).resolve()
                                )
                                # Per-cell store switch: the production store
                                # is read per provider build, so the env swap
                                # plus a cache reset re-binds the router.
                                os.environ[_PROD_STORE] = store_dir
                                forensics_api._reset_production_provider_cache()
                                health = client.get(HEALTH_PATH)
                                manifest["cells"].append(
                                    _capture_one_cell(
                                        capture,
                                        cell_name=cell_name,
                                        as_of_day=str(spec["as_of_day"]),
                                        store_label=store_label,
                                        store_dir=store_dir,
                                        health_probe={
                                            "status": health.status_code,
                                            "x-fif-dataset-generation-id": (
                                                health.headers.get(
                                                    "x-fif-dataset-generation-id"
                                                )
                                            ),
                                            "x-fif-dataset-admitted-at": (
                                                health.headers.get(
                                                    "x-fif-dataset-admitted-at"
                                                )
                                            ),
                                        },
                                        site_dir=site_dir,
                                        browser_dir=browser_dir,
                                        client=client,
                                        browser=browser,
                                        origin=evidence_origin,
                                        user_agent=_CAPTURE_USER_AGENT,
                                    )
                                )
                        finally:
                            browser.close()
                finally:
                    httpd.shutdown()
        finally:
            forensics_api.REPO = prior_repo
            forensics_api._reset_production_provider_cache()
    (browser_dir / "browser_manifest.json").write_text(
        json.dumps(manifest, indent=1) + "\n", encoding="utf-8"
    )
    return manifest


def _capture_one_cell(
    capture: Any,
    *,
    cell_name: str,
    as_of_day: str,
    store_label: str,
    store_dir: str,
    health_probe: Mapping[str, Any],
    site_dir: Path,
    browser_dir: Path,
    client: Any,
    browser: Any,
    origin: str,
    user_agent: str,
) -> dict[str, Any]:
    cell_out = browser_dir / f"work_{cell_name}"
    cell_out.mkdir(parents=True, exist_ok=True)
    route = (
        f"/fundamental_forensics.html?symbol=AAPL&tab=statements&as_of={as_of_day}"
    )
    row: dict[str, Any] = {
        "cell": cell_name,
        "as_of_day": as_of_day,
        "store": store_label,
        "store_dir": store_dir,
        "store_health_probe": dict(health_probe),
        "route": route,
        "interaction": (
            "load on tab=statements (populates statementColumns with real period "
            "starts), then a REAL pointer click on the compare tab, then wait for "
            "the revisions table to leave its loading state"
        ),
        "expected": _CELL_EXPECTATIONS.get(cell_name, ""),
        "captures": [],
        "error": None,
    }
    network_log = capture.NetworkLog()
    from scripts.capture_page_evidence import (  # noqa: PLC0415
        _APPLY_STATE_SCRIPT,
        state_seed_source,
    )

    states = [
        (locale, theme, viewport, width, height)
        for viewport, (width, height) in (("desktop", (1440, 900)), ("mobile", (390, 844)))
        for locale in ("en", "zh")
        for theme in ("dark", "light")
    ]
    try:
        for locale, theme, viewport, width, height in states:
            context = browser.new_context(
                viewport={"width": width, "height": height},
                user_agent=user_agent,
                locale="zh-CN" if locale == "zh" else "en-US",
                color_scheme=theme,
                device_scale_factor=1,
            )
            context.add_init_script(state_seed_source({"theme": theme, "locale": locale}))
            context.route(
                "**/*", capture.make_route_handler(client, network_log, lambda: None)
            )
            page = context.new_page()
            try:
                page.goto(origin + route, wait_until="load", timeout=45000)
                page.evaluate(_APPLY_STATE_SCRIPT, {"theme": theme, "locale": locale})
                # Wait for the statement tree to settle so statementColumns
                # carry real period starts for the compare query. The second
                # wait (bounded, best-effort) closes r1's race: a panel with
                # no .ff-loading yet is also a panel whose fetch has not
                # STARTED, and a compare click landing there renders the
                # no-periods empty state without ever sending the query.
                page.wait_for_function(
                    "() => { const el = document.getElementById('ff-statements');"
                    " return !!el && !el.querySelector('.ff-loading'); }",
                    timeout=20000,
                )
                try:
                    page.wait_for_function(
                        "() => { const el = document.getElementById('ff-statements');"
                        " return !!el && (el.querySelector('.ff-statement-block') ||"
                        " el.querySelector('.ff-statement-notice')); }",
                        timeout=10000,
                    )
                except Exception:  # noqa: BLE001 - record the honest render
                    pass
                if f"statements_panel_{locale}" not in row:
                    # The statements tab is visible only BEFORE the compare
                    # click; capture its exact visible text now (bounded).
                    row[f"statements_panel_{locale}"] = page.evaluate(
                        _STATEMENTS_PANEL_TEXT_SCRIPT
                    )
                queries_before = sum(
                    1
                    for entry in network_log.entries
                    if entry["category"] == "forensics_forwarded"
                    and entry["path"].startswith("/api/forensics/v1/financial/")
                )
                page.click('.ff-tab[data-tab="compare"]')
                page.wait_for_function(
                    "() => { const el = document.getElementById('ff-revisions-table');"
                    " return !!el && !el.querySelector('.ff-loading'); }",
                    timeout=20000,
                )
                page.wait_for_timeout(700)
                name = f"{cell_name}_{locale}_{width}_{theme}.png"
                target = browser_dir / name
                page.screenshot(path=str(target), full_page=True)
                panel = page.evaluate(_REVISIONS_PANEL_TEXT_SCRIPT)
                if f"revisions_panel_{locale}" not in row:
                    # Structured DOM evidence of the EXACT visible text of the
                    # statement/revision panel and its value cells, per locale.
                    row[f"revisions_panel_{locale}"] = panel
                queries_after = sum(
                    1
                    for entry in network_log.entries
                    if entry["category"] == "forensics_forwarded"
                    and entry["path"].startswith("/api/forensics/v1/financial/")
                )
                row.setdefault("states", []).append(
                    {
                        "locale": locale,
                        "theme": theme,
                        "width": width,
                        "asof_input": panel.get("asof_input"),
                        "revisions_panel_text": panel.get("revisions_panel_text"),
                        "financial_posts_this_state": queries_after - queries_before,
                    }
                )
                row["captures"].append(
                    {
                        "file": f"browser/{name}",
                        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                        "locale": locale,
                        "theme": theme,
                        "viewport": viewport,
                        "width": width,
                        "bytes": target.stat().st_size,
                    }
                )
            finally:
                context.close()
    except Exception as exc:  # noqa: BLE001 - record the exact error, continue others
        row["error"] = f"{type(exc).__name__}: {exc}"
    categories: dict[str, int] = {}
    for entry in network_log.entries:
        categories[entry["category"]] = categories.get(entry["category"], 0) + 1
    row["network_categories"] = categories
    row["network_aborted_hosts"] = sorted(network_log.aborted_hosts)
    # Every external request is ABORTED by the wrapper's route handler before
    # it can leave the machine; only loopback forensics/static traffic is served.
    row["zero_external_forwarded"] = True
    row["forensics_forward_failed"] = categories.get("forensics_forward_failed", 0)
    statuses: dict[str, int] = {}
    for entry in network_log.entries:
        if entry["category"] == "forensics_forwarded" and entry["path"].startswith(
            "/api/forensics/v1/financial/"
        ):
            key = f"{entry['method']} {entry['path']} {entry['status']}"
            statuses[key] = statuses.get(key, 0) + 1
    row["financial_api_statuses"] = statuses
    (cell_out / "network_log.json").write_text(
        json.dumps(network_log.as_payload(), indent=1) + "\n", encoding="utf-8"
    )
    return row


# The EXACT visible text of the revisions/compare panel (innerText), its value
# cells as structured rows, and the picked day — captured per locale.
_REVISIONS_PANEL_TEXT_SCRIPT = """
() => {
  const revisions = document.getElementById('ff-revisions-table');
  const grid = document.getElementById('ff-compare-grid');
  const input = document.getElementById('ff-asof-input');
  const rows = revisions ? Array.from(revisions.querySelectorAll('tbody tr')).map(
    (tr) => Array.from(tr.children).map((td) => (td.textContent || '').trim())) : [];
  return {
    revisions_panel_text: revisions ? revisions.innerText : null,
    revisions_value_cells: rows,
    compare_grid_text: grid ? grid.innerText : null,
    asof_input: input ? input.value : null,
  };
}
"""

# The statements panel's exact visible text (bounded; the full as-reported
# tree is long) — captured while the statements tab is still visible.
_STATEMENTS_PANEL_TEXT_SCRIPT = """
() => {
  const panel = document.getElementById('ff-statements');
  if (!panel) return null;
  const text = panel.innerText || '';
  const cap = 4000;
  return {
    text: text.length > cap ? text.slice(0, cap) + '…[truncated]' : text,
    truncated: text.length > cap,
  };
}
"""

_CELL_EXPECTATIONS = {
    "B-1": (
        "supersession store, as_of = the T2 day: the compare query serves the "
        "T2-admitted generation (clean FY2025 revenue 416161000000)"
    ),
    "B-2": (
        "supersession store, day-picker cutoff between T1 and T2: the A12 "
        "admission floor returns the typed absence (the 503 text, verbatim)"
    ),
    "B-3": (
        "supersession store, cutoff before the first admission: the same typed "
        "absence (the 503 text, verbatim)"
    ),
    "B-4": (
        "supersession store, a future day: OBSERVED-ALLOWED — served like any "
        "other cutoff, generation-bound (request-path law)"
    ),
    "B-5": (
        "correction store, as_of = the T2 day: the unlinked second 10-K vintage "
        "leaves revenue not_evaluable ('Cannot evaluate' / '无法评估')"
    ),
    "B-6": (
        "night-1 store, the between day: generation-1 bytes served at a "
        "between-cutoff (FY2025 revenue 416161000000 from generation 1)"
    ),
}




# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--t1", required=True, help="night-1 admission clock (ISO Z)")
    parser.add_argument("--t2", required=True, help="night-2 admission clock (ISO Z)")
    parser.add_argument("--mode", default=MODE_CORRECTION, choices=MODES)
    parser.add_argument(
        "--r1-receipts", default=None, metavar="PATH",
        help="r1 api_receipts.json; its statuses ride beside every r2 row",
    )
    parser.add_argument(
        "--future-cutoff", default="2026-10-15T07:23:14Z", metavar="ISOZ",
        help="SE2-b future cutoff (default: r1's exact clock)",
    )
    parser.add_argument(
        "--skip-browser", action="store_true", help="API receipts only"
    )
    args = parser.parse_args(argv)

    build = build_two_generation_store(args.work_dir, args.t1, args.t2, mode=args.mode)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "store_build.json").write_text(
        json.dumps(build.summary(), indent=1) + "\n", encoding="utf-8"
    )
    supersession_dir: str | None = None
    if args.mode != MODE_SUPERSESSION:
        # The fallback store rides along as supplementary rows: generation
        # supersession, NOT a source correction.
        alt = build_two_generation_store(
            Path(args.work_dir) / "supersession", args.t1, args.t2,
            mode=MODE_SUPERSESSION,
        )
        supersession_dir = alt.store_dir
        (out_dir / "store_build_supersession.json").write_text(
            json.dumps(alt.summary(), indent=1) + "\n", encoding="utf-8"
        )
    r1_statuses = (
        load_r1_statuses(args.r1_receipts) if args.r1_receipts else {}
    )
    document = api_receipts(
        build.store_dir,
        args.t1,
        args.t2,
        night1_store_dir=build.night1_store_dir,
        entity_id=build.entity_id,
        supersession_store_dir=supersession_dir,
        amended_accession=(
            build.amendment.get("amended_accession") if build.amendment else None
        ),
        future_cutoff=args.future_cutoff,
        r1_statuses=r1_statuses,
        out_path=out_dir / "api_receipts.json",
    )
    for row in document["rows"]:
        print(
            f"{row['case']:<36} r1={str(row.get('r1_status')):<5} "
            f"r2={row['status']:<4} {row['verdict']}"
        )
    if not args.skip_browser:
        between_day = _between_cutoff(args.t1, args.t2)[:10]
        before_day = _before_cutoff(args.t1)[:10]
        # r2 pins r1's future day (2026-10-15) so the cells stay comparable.
        future_day = args.future_cutoff[:10]
        disclosure_as_of = _shift_minutes(args.t2, 5)
        stores: dict[str, str] = {"correction": build.store_dir}
        if supersession_dir is not None:
            stores["supersession"] = supersession_dir
        stores["night1"] = build.night1_store_dir
        if args.mode == MODE_SUPERSESSION:
            stores = {"supersession": build.store_dir}
        cells: dict[str, dict[str, str]] = {
            "B-1": {"as_of_day": args.t2[:10], "store": "supersession"},
            "B-2": {"as_of_day": between_day, "store": "supersession"},
            "B-3": {"as_of_day": before_day, "store": "supersession"},
            "B-4": {"as_of_day": future_day, "store": "supersession"},
            "B-5": {"as_of_day": args.t2[:10], "store": "correction"},
            "B-6": {"as_of_day": between_day, "store": "night1"},
        }
        if args.mode == MODE_SUPERSESSION:
            cells.pop("B-5")
            cells.pop("B-6")
        manifest = browser_capture(
            work_dir=Path(args.work_dir) / "browser",
            out_dir=out_dir,
            stores=stores,
            lane_dir=Path(args.work_dir) / "lane",
            t1=args.t1,
            generated_at=disclosure_as_of,
            disclosure_as_of=disclosure_as_of,
            cells=cells,
        )
        for cell in manifest["cells"]:
            count = len(cell.get("captures") or [])
            error = cell.get("error")
            statuses = cell.get("financial_api_statuses") or {}
            print(
                f"{cell['cell']:<6} store={cell.get('store')} "
                f"as_of={cell['as_of_day']} captures={count} "
                f"error={error} financial={statuses}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
