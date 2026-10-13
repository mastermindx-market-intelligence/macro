"""FIF C0-b: publish production issuer datasets from lane-retained bytes (hard gate).

Scheduled-lane producer for the D3 production dataset store. Six subcommands,
one frozen coverage contract, and NO ticker or CIK literal anywhere — the
issuer universe is read from the contract at runtime:

* ``targets`` derives the wave-2 ``--target TICKER=CIK`` extras the contract
  adds over the incumbent pinned targets file, and hard-fails if the union
  would exceed ``--max-tickers``. The first wave-2 invocation consumes its
  stdout verbatim, so no issuer ever rides a YAML literal.
* ``acquire-contract`` (C0-c E1) acquires every contract accession's primary
  plus manifest keyed by ACCESSION — never a latest-N selector — reusing
  retained manifests/pages/primaries first (zero requests on a hit), locating
  rows in the verified latest.json's recent window or its unique covering
  ``filings.files[]`` page, retaining pages ONLY through the incumbent
  historical-shard fetch, and reporting per-accession typed codes with a
  line-start ``::warning title=fif-contract-acquire::`` on a partial run.
* ``capture-members`` performs the D1 member-capture pass (see
  ``engine/fundamental_forensics/fif_member_capture.py``) over the warm
  ``--raw-root``/``--archive-root`` trees under the ONE shared
  ``SecRequestPacer``. It is offline on every input except the SEC archive
  fetches it makes through the incumbent collector.
* ``contract-acquire-summary`` (D13) reads the ISOLATED contract lane's
  wave-2 result: ``complete`` is silent, a typed ``partial`` prints one
  line-start ``::warning title=fif-contract-acquire::`` per shortfall (never
  fatal — a contract issuer's bounded acquire is partial by construction),
  and a missing/unreadable/malformed result is the typed
  ``contract_acquire_result_unreadable`` refusal (crash class).
* ``publish`` admits every retained package per contract issuer, computes the
  CLOCK RULE admission clock, mints lineage evidence through the S2-p seam,
  publishes one immutable generation per published issuer through
  ``publish_production_dataset``, and read-back-verifies that ``latest.json``
  NAMES each generation. Every other contract issuer gets exactly one typed
  exclusion row (closed vocabulary) — never silence.
* ``verify`` re-asserts the run report covers every contract issuer exactly
  once and that the store pointer names every published generation.

CLOCK RULE (binding): ``admitted_at = max(capture_recorded_at of every
admitted package, CONFIRMATION_RULE_AVAILABLE_AT,
CONFIRMATION_CHAIN_RULE_AVAILABLE_AT, every registry available_at clock)`` —
content-derived, never ``now()``. The registry snapshot does expose
``available_at`` rule/mapping clocks (metric_catalog/mappings/formulas), so
they join the max.

FUTURE-CLOCK REFUSAL (seat amendment (a)): if the computed ``admitted_at`` is
later than the run's ``--recorded-at``, publish hard-fails BEFORE any store
write with the typed code ``admitted_at_after_recorded_at``, never clamping
either clock.

Hard-fail shape: every failure exits non-zero and prints one line-start
``::error`` on STDERR (``print(..., file=sys.stderr, flush=True)``, never
through a logger) — this is a publication gate, not the
``build_fundamental_forensics`` swallow-all shape.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import traceback
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from collectors.edgar_forensics import SecForensicsCollector, _user_agent  # noqa: E402
from collectors.fundamental_forensics_acquisition import (  # noqa: E402
    DEFAULT_MAX_SUBMISSIONS_BYTES,
)
from collectors.sec_document_spine import SecFilingArchiveCollector  # noqa: E402
from collectors.sec_request_pacer import SecRequestPacer  # noqa: E402
from engine.fundamental_forensics.admitted_filing_package import (  # noqa: E402
    AdmittedFilingPackageError,
    admit_retained_filing_package,
)
from engine.fundamental_forensics.sec_document_spine import canonical_cik  # noqa: E402
from engine.fundamental_forensics.fif_member_capture import (  # noqa: E402
    DEFAULT_RUN_BUDGET_BYTES,
    RETAINED_PACKAGE_INTEGRITY_CODES,
    FifMemberCaptureError,
    capture_fif_filing_packages,
    read_retained_fif_packages,
    refuse_repository_fixture_inputs,
)
from engine.fundamental_forensics.fif_contract_acquisition import (  # noqa: E402
    CONTRACT_ACQUISITION_RUN_SCHEMA,
    acquire_contract_primaries,
)
from engine.fundamental_forensics.financial_intelligence_packet import EntityInput  # noqa: E402
from engine.fundamental_forensics.ixbrl_raw_ledger import convert_parsed_filings  # noqa: E402
from engine.fundamental_forensics.lineage_evidence import (  # noqa: E402
    CONFIRMATION_CHAIN_RULE_AVAILABLE_AT,
    CONFIRMATION_RULE_AVAILABLE_AT,
    LineageEvidenceError,
)
from engine.fundamental_forensics.models import parse_utc, utc_text  # noqa: E402
from engine.fundamental_forensics.production_lineage import (  # noqa: E402
    mint_production_lineage_evidence,
)
from engine.fundamental_forensics.production_datasets import (  # noqa: E402
    ProductionDatasetError,
    ProductionDatasetMaterial,
    build_production_dataset_store,
    load_latest_generation,
    lineage_from_role_payload,
    production_manifest_key,
    publish_production_dataset,
    snapshot_core_registry_payload,
)
from engine.fundamental_forensics.query_service import CanonicalEntityBinding  # noqa: E402
from collectors.sec_filing_parser import (  # noqa: E402
    SecFilingParseError,
    parse_sec_filing_document,
)

COVERAGE_CONTRACT_SCHEMA = "fundamental_forensics.coverage_contract/v1"
PUBLISH_REPORT_SCHEMA = "fundamental_forensics.fif_production_publish_report/v1"
CONTRACT_ACQUIRE_SUMMARY_SCHEMA = "fundamental_forensics.fif_contract_acquire_summary/v1"
EXCLUSION_IDENTITY_NOT_FROZEN = "identity_not_frozen"
EXCLUSION_NO_RETAINED_PACKAGE = "no_retained_package"
# C0-c ERRATA-6 rule 5: an issuer whose only admitted packages are 8-K event
# packages publishes nothing new for that issuer — one typed exclusion row,
# never silence, never a generation write.
EXCLUSION_ONLY_EVENT_PACKAGES = "only_event_packages"
PUBLISHER_ERROR_CODES = frozenset(
    {
        "contract_malformed",
        "targets_overflow",
        "admitted_at_after_recorded_at",
        "publish_failed",
        "verify_failed",
        "lineage_mint_failed",
        "golden_input_refused",
        # ERRATA E1: a retained package that fails integrity verification
        # (RETAINED_PACKAGE_INTEGRITY_CODES) fails the WHOLE run — capture
        # exits non-zero after its report, and publish refuses before any
        # store write. Never a per-issuer exclusion.
        "retained_package_integrity",
        # ERRATA-3 1.a: a latest.json that exists but cannot be verified is a
        # hard typed failure, never treated as absence.
        "latest_pointer_unreadable",
        # ERRATA-3 1.c: changed content with no lawful clock later than the
        # latest published clock refuses instead of rewinding the pointer.
        "admission_clock_not_after_latest",
        # D13: the isolated contract-acquire lane's result/summary is missing,
        # unreadable, or outside the closed shape — the acquisition state is
        # UNKNOWN, so capture/publish must refuse rather than guess.
        "contract_acquire_result_unreadable",
    }
)


class PublisherError(RuntimeError):
    """A typed hard failure of the publication gate (rc != 0 + ::error)."""

    def __init__(self, message: str, *, code: str) -> None:
        if code not in PUBLISHER_ERROR_CODES:
            raise ValueError(f"unknown publisher error code: {code}")
        super().__init__(message)
        self.code = code


def _fail(message: str, *, code: str) -> None:
    raise PublisherError(message, code=code)


def _error_annotation(title: str, message: str) -> None:
    # D8: stderr, never stdout — the workflow captures this script's stdout via
    # ``$(...)`` for the ``targets`` subcommand, so a stdout annotation is
    # swallowed there. GitHub parses workflow commands from both streams, and
    # stderr is the one every caller leaves visible. Still a bare print with a
    # line-start ``::error``, never a logger.
    print(f"::error title={title}::{message}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Contract + targets
# ---------------------------------------------------------------------------


def load_fif_coverage_contract(path: Path) -> dict[str, Any]:
    """Read the frozen issuer coverage contract. Identity is never hardcoded."""
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PublisherError(
            f"coverage contract is unreadable: {path}", code="contract_malformed"
        ) from exc
    if not isinstance(document, dict) or not isinstance(document.get("issuers"), list):
        _fail(f"coverage contract shape is invalid: {path}", code="contract_malformed")
    if document.get("schema") != COVERAGE_CONTRACT_SCHEMA:
        _fail(f"unsupported coverage contract schema: {path}", code="contract_malformed")
    issuers: list[dict[str, Any]] = []
    seen_ciks: set[str] = set()
    for issuer in document["issuers"]:
        if not isinstance(issuer, dict):
            _fail("coverage contract issuer is malformed", code="contract_malformed")
        cik = issuer.get("cik")
        ticker = issuer.get("ticker")
        if not isinstance(cik, str) or not isinstance(ticker, str) or not cik or not ticker:
            _fail("coverage contract issuer identity is malformed", code="contract_malformed")
        if cik in seen_ciks:
            _fail(f"coverage contract repeats a CIK: {cik}", code="contract_malformed")
        seen_ciks.add(cik)
        accessions = issuer.get("accessions")
        if not isinstance(accessions, list) or not accessions:
            _fail(
                f"coverage contract issuer lists no accessions: {ticker}",
                code="contract_malformed",
            )
        for entry in accessions:
            if not isinstance(entry, dict) or not isinstance(entry.get("accession"), str):
                _fail(
                    f"coverage contract accession entry is malformed: {ticker}",
                    code="contract_malformed",
                )
        binding = issuer.get("security_master_binding")
        if binding is not None and not isinstance(binding, dict):
            _fail(
                f"coverage contract security_master_binding is malformed: {ticker}",
                code="contract_malformed",
            )
        issuers.append(issuer)
    document["issuers"] = issuers
    return document


def _run_targets(args: argparse.Namespace) -> int:
    contract = load_fif_coverage_contract(args.coverage_file)
    try:
        from scripts.run_fundamental_forensics_wave2 import load_targets_file

        incumbent = load_targets_file(Path(args.targets_file))
    except Exception as exc:  # noqa: BLE001 - OperatorFlowError and friends
        raise PublisherError(
            f"incumbent targets file is unreadable: {args.targets_file}",
            code="contract_malformed",
        ) from exc
    incumbent_by_ticker = {}
    for entry in incumbent:
        ticker, _, cik = entry.partition("=")
        incumbent_by_ticker[ticker.upper()] = cik
    contract_pairs: list[tuple[str, str]] = []
    for issuer in contract["issuers"]:
        ticker = str(issuer["ticker"]).upper()
        cik = str(issuer["cik"])
        known = incumbent_by_ticker.get(ticker)
        if known is not None and known != cik:
            _fail(
                f"coverage contract CIK disagrees with the incumbent target: {ticker}",
                code="contract_malformed",
            )
        contract_pairs.append((ticker, cik))
    union = dict(incumbent_by_ticker)
    for ticker, cik in contract_pairs:
        union.setdefault(ticker, cik)
    if len(union) > args.max_tickers:
        _fail(
            f"contract union with incumbent targets exceeds --max-tickers "
            f"({len(union)} > {args.max_tickers})",
            code="targets_overflow",
        )
    for ticker, cik in contract_pairs:
        if ticker not in incumbent_by_ticker:
            print(f"--target {ticker}={cik}", flush=True)
    return 0


# ---------------------------------------------------------------------------
# contract-acquire-summary (D13: the isolated, non-gating contract lane)
# ---------------------------------------------------------------------------


def _parse_final_json_object(text: str) -> dict[str, Any]:
    """Parse the LAST complete top-level JSON object in a stdout capture.

    C5: wave-2 prints its outcome JSON as its final stdout write and every
    logger line rides stderr, so a plain ``json.loads`` would already work —
    but the summary must not BREAK if a future stray line lands on stdout, so
    the parse is robust by construction: scan every candidate start, prefer
    the object whose decode consumes the remainder (the printed outcome ends
    at EOF), and fall back to the object with the furthest reach. Nested
    objects never win: an inner start always leaves trailing text.
    """
    decoder = json.JSONDecoder()
    candidates: list[tuple[int, int, dict[str, Any]]] = []
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, end = decoder.raw_decode(text, index)
        except ValueError:
            continue
        if isinstance(value, dict):
            candidates.append((index, end, value))
    if not candidates:
        raise ValueError("no JSON object found")
    for index, end, value in reversed(candidates):
        if not text[end:].strip():
            return value
    return max(candidates, key=lambda item: (item[1], -item[0]))[2]


def _contract_acquire_shortfalls(acquire: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Every form whose coverage is not complete, as frozen shortfall rows.

    A ticker-level failure (e.g. a submissions outage) keeps its form receipts
    in a non-complete state, so it surfaces here as 0/``required`` rows rather
    than silence. Malformed rows are the typed unreadable refusal: the
    acquisition state must never be guessed at.
    """
    receipts = acquire.get("ticker_receipts")
    if not isinstance(receipts, list):
        _fail(
            "contract acquire result has no ticker_receipts list",
            code="contract_acquire_result_unreadable",
        )
    rows: list[dict[str, Any]] = []
    for receipt in receipts:
        if not isinstance(receipt, Mapping):
            _fail(
                "contract acquire ticker receipt is malformed",
                code="contract_acquire_result_unreadable",
            )
        for form in receipt.get("forms") or []:
            if not isinstance(form, Mapping) or not isinstance(form.get("form"), str):
                _fail(
                    "contract acquire form receipt is malformed",
                    code="contract_acquire_result_unreadable",
                )
            if str(form.get("status") or "") == "complete":
                continue
            selected = form.get("selected_accessions")
            required = form.get("requested_comparables")
            if not isinstance(selected, list) or type(required) is not int:
                _fail(
                    "contract acquire form receipt is malformed",
                    code="contract_acquire_result_unreadable",
                )
            rows.append(
                {
                    "ticker": str(receipt.get("ticker") or ""),
                    "cik": str(receipt.get("cik") or ""),
                    "form": str(form["form"]),
                    "selected": len(selected),
                    "required": required,
                }
            )
    return rows


def _validated_summary_shape(document: Any, *, origin: str) -> dict[str, Any]:
    """Validate one contract-acquire summary object (file or embedded block)."""
    if not isinstance(document, Mapping) or document.get(
        "schema"
    ) != CONTRACT_ACQUIRE_SUMMARY_SCHEMA:
        _fail(
            f"contract acquire summary shape is invalid: {origin}",
            code="contract_acquire_result_unreadable",
        )
    status = document.get("status")
    if status not in ("complete", "partial"):
        _fail(
            f"contract acquire summary status is outside the closed vocabulary: {status!r}",
            code="contract_acquire_result_unreadable",
        )
    shortfalls = document.get("shortfalls")
    if not isinstance(shortfalls, list):
        _fail(
            f"contract acquire summary shortfalls are malformed: {origin}",
            code="contract_acquire_result_unreadable",
        )
    for row in shortfalls:
        if not isinstance(row, Mapping) or set(row) != {
            "ticker",
            "cik",
            "form",
            "selected",
            "required",
        }:
            _fail(
                f"contract acquire summary shortfall row is malformed: {origin}",
                code="contract_acquire_result_unreadable",
            )
    out = {
        "schema": CONTRACT_ACQUIRE_SUMMARY_SCHEMA,
        "status": str(status),
        "shortfalls": [dict(row) for row in shortfalls],
    }
    # C0-c E1 (amendment E): acquire-contract merges its own run report into
    # the summary file under ``acquire_contract``; carry it onward verbatim so
    # capture/publish reports expose one acquisition-state trail. Absent on
    # summaries written before acquire-contract ran — lawful.
    acquire_contract = document.get("acquire_contract")
    if acquire_contract is not None:
        if (
            not isinstance(acquire_contract, Mapping)
            or acquire_contract.get("schema") != CONTRACT_ACQUISITION_RUN_SCHEMA
        ):
            _fail(
                f"contract acquire summary acquire_contract block is malformed: {origin}",
                code="contract_acquire_result_unreadable",
            )
        out["acquire_contract"] = dict(acquire_contract)
    return out


def _run_contract_acquire_summary(args: argparse.Namespace) -> int:
    path = Path(args.result)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise PublisherError(
            f"contract acquire result is unreadable: {path}",
            code="contract_acquire_result_unreadable",
        ) from exc
    try:
        outcome = _parse_final_json_object(text)
    except ValueError as exc:
        raise PublisherError(
            f"contract acquire result carries no JSON outcome object: {path}",
            code="contract_acquire_result_unreadable",
        ) from exc
    results = outcome.get("results")
    acquire = results.get("acquire") if isinstance(results, Mapping) else None
    if not isinstance(acquire, Mapping) or not isinstance(acquire.get("status"), str):
        _fail(
            f"contract acquire result has no results.acquire.status: {path}",
            code="contract_acquire_result_unreadable",
        )
    status = str(acquire["status"])
    if status not in ("complete", "partial"):
        _fail(
            f"contract acquire status is outside the closed vocabulary: {status!r}",
            code="contract_acquire_result_unreadable",
        )
    shortfalls = _contract_acquire_shortfalls(acquire)
    summary = {
        "schema": CONTRACT_ACQUIRE_SUMMARY_SCHEMA,
        "status": status,
        "shortfalls": shortfalls,
    }
    _write_report(summary, args.report_path)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2), flush=True)
    if status == "complete":
        return 0
    # R4: a typed partial is EXPECTED for the contract lane — one line-start
    # ::warning per shortfall (bare print, flush=True; never a logger), and
    # the shortfalls ride the summary into the capture/publish reports.
    if shortfalls:
        for row in shortfalls:
            print(
                f"::warning title=fif-contract-acquire::{row['ticker']} {row['form']} "
                f"{row['selected']}/{row['required']} comparables selected at as_of "
                f"(partial contract acquire; shortfall recorded)",
                flush=True,
            )
    else:
        print(
            "::warning title=fif-contract-acquire::acquire status partial with no "
            "shortfall rows (unexpected result shape; shortfall recorded)",
            flush=True,
        )
    return 0


# ---------------------------------------------------------------------------
# acquire-contract (C0-c E1: contract-keyed primary acquisition)
# ---------------------------------------------------------------------------


def _run_acquire_contract(args: argparse.Namespace) -> int:
    contract = load_fif_coverage_contract(args.coverage_file)
    raw_root = Path(args.raw_root)
    archive_root = Path(args.archive_root)
    refuse_repository_fixture_inputs(raw_root, archive_root)
    recorded_at = _require_clock(args.recorded_at, "--recorded-at")
    user_agent = _resolve_user_agent(args)
    if "@" not in user_agent:
        _fail("SEC user agent must identify an application and contact email", code="contract_malformed")
    # E1-c amendment (C): ONE SecRequestPacer shared by the SecForensicsCollector
    # (pages) and the SecFilingArchiveCollector (primaries); a privately paced
    # collector is the typed private_pacer refusal (asserted inside the engine).
    pacer = SecRequestPacer(min_interval_seconds=args.min_interval_seconds)
    submissions_collector = SecForensicsCollector(
        raw_root,
        user_agent=user_agent,
        min_interval_seconds=args.min_interval_seconds,
        max_response_bytes=DEFAULT_MAX_SUBMISSIONS_BYTES,
        pacer=pacer,
    )
    archive_collector = SecFilingArchiveCollector(
        archive_root,
        user_agent=user_agent,
        min_interval_seconds=args.min_interval_seconds,
        max_document_bytes=args.max_document_bytes,
        pacer=pacer,
    )
    report = acquire_contract_primaries(
        raw_root=raw_root,
        archive_root=archive_root,
        issuers=list(contract["issuers"]),
        submissions_collector=submissions_collector,
        archive_collector=archive_collector,
        pacer=pacer,
        recorded_at=utc_text(recorded_at) or "",
        run_budget_bytes=args.run_budget_bytes,
    )
    # Evidence first (D6 discipline): the report is printed and written BEFORE
    # any refusal or warning below.
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2), flush=True)
    _write_report(report, args.report_path)
    if args.contract_acquire_summary:
        # Amendment (E): the run's per-accession codes ride the SAME summary
        # file capture already reads (--contract-acquire-report), so no other
        # workflow step or file handoff changes. Shape-checked load, then one
        # rewrite with the acquire_contract block attached.
        summary = _load_contract_acquire_summary(args.contract_acquire_summary)
        summary["acquire_contract"] = report
        Path(args.contract_acquire_summary).write_text(
            json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    failures = [
        row
        for issuer in report["issuers"]
        for row in issuer["accessions"]
        if str(row.get("outcome") or "").startswith("acquire_failed:")
    ]
    if failures:
        # Amendment (E): a partial run emits the line-start
        # ``::warning title=fif-contract-acquire::`` per failing accession
        # (bare print with flush; never a logger, never fatal).
        for row in failures:
            print(
                f"::warning title=fif-contract-acquire::{row['accession']} "
                f"{row['outcome']} (contract-keyed acquire partial; typed code "
                "recorded)",
                flush=True,
            )
    return 0


# ---------------------------------------------------------------------------
# capture-members
# ---------------------------------------------------------------------------


def _resolve_user_agent(args: argparse.Namespace) -> str:
    if args.user_agent:
        return str(args.user_agent)
    return _user_agent(_ROOT)


def _load_contract_acquire_summary(path_value: Any) -> dict[str, Any] | None:
    """D13 W3: read the contract-acquire summary file for the capture report.

    Fail closed BEFORE any SEC fetch: an unreadable or wrong-shaped summary is
    the typed ``contract_acquire_result_unreadable`` refusal — the capture
    report must never silently drop the contract acquisition state it was
    handed (the publish report carries the block onward from here).
    """
    if not path_value:
        return None
    try:
        document = json.loads(Path(path_value).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PublisherError(
            f"contract acquire summary is unreadable: {path_value}",
            code="contract_acquire_result_unreadable",
        ) from exc
    return _validated_summary_shape(document, origin=str(path_value))


def _run_capture_members(args: argparse.Namespace) -> int:
    contract = load_fif_coverage_contract(args.coverage_file)
    raw_root = Path(args.raw_root)
    archive_root = Path(args.archive_root)
    refuse_repository_fixture_inputs(raw_root, archive_root)
    recorded_at = _require_clock(args.recorded_at, "--recorded-at")
    contract_acquire_summary = _load_contract_acquire_summary(args.contract_acquire_report)
    user_agent = _resolve_user_agent(args)
    if "@" not in user_agent:
        _fail("SEC user agent must identify an application and contact email", code="contract_malformed")
    pacer = SecRequestPacer(min_interval_seconds=args.min_interval_seconds)
    collector = SecFilingArchiveCollector(
        archive_root,
        user_agent=user_agent,
        min_interval_seconds=args.min_interval_seconds,
        max_document_bytes=args.max_document_bytes,
        pacer=pacer,
    )
    # C0-c ERRATA-5 rule 3: the page-fetch collector rides the SAME shared
    # pacer (A20) and the incumbent 16 MiB submissions ceiling; pages are
    # retained only through the incumbent historical-shard fetch
    # (publish_latest=False), so latest.json never moves.
    submissions_collector = SecForensicsCollector(
        raw_root,
        user_agent=user_agent,
        min_interval_seconds=args.min_interval_seconds,
        max_response_bytes=DEFAULT_MAX_SUBMISSIONS_BYTES,
        pacer=pacer,
    )
    report = capture_fif_filing_packages(
        raw_root=raw_root,
        archive_root=archive_root,
        issuers=list(contract["issuers"]),
        collector=collector,
        pacer=pacer,
        recorded_at=utc_text(recorded_at) or "",
        run_budget_bytes=args.run_budget_bytes,
        submissions_collector=submissions_collector,
    )
    if contract_acquire_summary is not None:
        # D13 W3: the isolated contract acquire's state rides the capture
        # report verbatim (schema/status/shortfalls); publish carries the same
        # block onward. Report ONLY — no manifest or generation byte moves.
        report["contract_acquire"] = contract_acquire_summary
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2), flush=True)
    # D6: the capture report is an artifact too — written BEFORE any refusal
    # below, so a red capture night still leaves its evidence on disk.
    if args.report_path:
        target = Path(args.report_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    # ERRATA E1: any accession that failed retained-package integrity makes
    # the whole capture exit non-zero (report first, refusal second). Other
    # capture failures (fetch/budget/mint) keep today's row-level behavior.
    integrity_failures = []
    for issuer in report["issuers"]:
        for row in issuer["accessions"]:
            outcome = str(row.get("outcome") or "")
            if not outcome.startswith("member_capture_failed:"):
                continue
            code = outcome.split(":", 1)[1]
            if code in RETAINED_PACKAGE_INTEGRITY_CODES:
                integrity_failures.append(
                    f"{issuer['cik']}/{row['accession']}: {code}"
                )
    if integrity_failures:
        _fail(
            "retained-package integrity refusal — a retained package failed "
            "verify-before-reuse, so nothing may publish tonight and no clock "
            "was re-minted: " + "; ".join(integrity_failures),
            code="retained_package_integrity",
        )
    return 0


# ---------------------------------------------------------------------------
# CLOCK RULE helpers
# ---------------------------------------------------------------------------


def _registry_available_clocks(payload: Mapping[str, Any]) -> list[datetime]:
    """Every ``available_at`` clock the registry snapshot exposes, parsed.

    D10: fail closed. An ``available_at`` that exists but cannot be parsed is
    the typed ``contract_malformed`` refusal, never a silently dropped clock —
    a malformed registry must not quietly under-clock the CLOCK RULE max (and
    with it the generation id and pointer ordering).
    """
    found: list[datetime] = []

    def _scan(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, value in node.items():
                if key == "available_at":
                    if not isinstance(value, str) or not value.strip():
                        _fail(
                            "registry available_at is not a non-empty string: "
                            f"{value!r}",
                            code="contract_malformed",
                        )
                    try:
                        parsed = parse_utc(value.strip(), field="registry available_at")
                    except ValueError as exc:
                        raise PublisherError(
                            f"registry available_at is unparseable: {value!r} ({exc})",
                            code="contract_malformed",
                        ) from exc
                    if parsed is None:
                        _fail(
                            f"registry available_at is unparseable: {value!r}",
                            code="contract_malformed",
                        )
                    found.append(parsed)
                _scan(value)
        elif isinstance(node, (list, tuple)):
            for item in node:
                _scan(item)

    _scan(payload)
    return found


def _rule_clocks() -> list[datetime]:
    return [CONFIRMATION_RULE_AVAILABLE_AT, CONFIRMATION_CHAIN_RULE_AVAILABLE_AT]


def _require_clock(value: str, field: str) -> datetime:
    try:
        parsed = parse_utc(value, field=field)
    except ValueError as exc:
        raise PublisherError(
            f"{field} is not an aware ISO-8601 UTC clock: {value}",
            code="contract_malformed",
        ) from exc
    if parsed is None:
        _fail(f"{field} is required", code="contract_malformed")
    return parsed


# ---------------------------------------------------------------------------
# publish
# ---------------------------------------------------------------------------


def _convert_admitted_packages(packages: Sequence[Any]):
    """Ledger + filing metadata over admitted packages, duck-typed.

    Composition of the incumbent converter's own two halves
    (``parse_sec_filing_document`` + ``convert_parsed_filings``) so the
    producer's direct imports stay off every golden entry point (spec §3
    guard); the conversion core is package-agnostic and the admitted packages
    are proven duck-compatible.
    """
    pairs = []
    for package in packages:
        primary = package.manifest["primary_document"]
        try:
            parsed = parse_sec_filing_document(package.members[primary], document_name=primary)
        except SecFilingParseError as exc:
            raise PublisherError(
                f"admitted primary document cannot be re-parsed: {primary} ({exc})",
                code="publish_failed",
            ) from exc
        pairs.append((package, parsed))
    return convert_parsed_filings(pairs)


def _mint_lineage_evidence(ledger: Any, packages: Sequence[Any], *, system_available_at):
    """The ONE S2-p seam call, wrapped (D11): a ``LineageEvidenceError`` is the
    typed ``lineage_mint_failed`` refusal (rc != 0, line-start ``::error``),
    never a silent empty bundle and never the generic ``publish_failed`` code.
    Only ``LineageEvidenceError`` maps; any other exception propagates."""
    try:
        return mint_production_lineage_evidence(
            ledger, packages, system_available_at=system_available_at
        )
    except LineageEvidenceError as exc:
        raise PublisherError(
            f"lineage mint refused: {exc}", code="lineage_mint_failed"
        ) from exc


def _issuer_binding(issuer: Mapping[str, Any]) -> CanonicalEntityBinding | None:
    binding = issuer.get("security_master_binding")
    if not isinstance(binding, Mapping):
        return None
    issuer_id = binding.get("issuer_id")
    if not isinstance(issuer_id, str) or not issuer_id:
        return None
    cik = str(issuer["cik"])
    return CanonicalEntityBinding(
        entity_id=issuer_id,
        cik=cik,
        ticker=str(issuer["ticker"]),
        source_entity_id=cik,
    )


@dataclass(frozen=True)
class _StagedIssuer:
    """One contract issuer with its admitted package set, ready to plan.

    ERRATA-6: ``admitted_packages`` is the MATERIAL set only (an admitted
    package whose witness-bound form is exactly ``8-K`` is admitted and
    counted but NEVER enters the build_production_dataset_store material, so
    its capture clock cannot contribute to T_c or the ERRATA-3 floor —
    otherwise every 8-K capture would mint a content-identical generation
    with a new admitted_at). ``event_accessions`` names the admitted 8-Ks for
    the report-only ``admitted_event_accessions`` key.
    """

    issuer: Mapping[str, Any]
    binding: CanonicalEntityBinding
    admitted_packages: tuple[Any, ...]
    capture_clocks: tuple[datetime, ...]
    event_accessions: tuple[str, ...] = ()

    @property
    def admitted_accessions(self) -> tuple[str, ...]:
        material = tuple(
            str(package.manifest["accession"]) for package in self.admitted_packages
        )
        return tuple(sorted({*material, *self.event_accessions}))


def _load_capture_failures(path_value: Any) -> dict[str, list[tuple[str, str]]]:
    """D6: per-CIK capture-failure codes from the capture report, if given.

    A --capture-report that is unreadable or wrong-shaped is the typed
    ``contract_malformed`` refusal (fail closed: publish must not silently
    lose the capture outcomes it was handed).
    """
    if not path_value:
        return {}
    try:
        document = json.loads(Path(path_value).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PublisherError(
            f"capture report is unreadable: {path_value}", code="contract_malformed"
        ) from exc
    if not isinstance(document, dict) or not isinstance(document.get("issuers"), list):
        _fail(f"capture report shape is invalid: {path_value}", code="contract_malformed")
    failures: dict[str, list[tuple[str, str]]] = {}
    for issuer in document["issuers"]:
        if not isinstance(issuer, dict) or not isinstance(issuer.get("cik"), str):
            _fail("capture report issuer row is malformed", code="contract_malformed")
        rows: list[tuple[str, str]] = []
        for row in issuer.get("accessions") or []:
            if not isinstance(row, dict):
                _fail(
                    "capture report accession row is malformed",
                    code="contract_malformed",
                )
            outcome = str(row.get("outcome") or "")
            if outcome.startswith("member_capture_failed:"):
                rows.append((outcome.split(":", 1)[1], str(row.get("error") or outcome)))
        failures[issuer["cik"]] = rows
    return failures


def _acquire_outcomes(capture_doc: Mapping[str, Any] | None) -> dict[str, dict[str, str]]:
    """Per-CIK per-accession acquire-contract outcomes from the capture
    report's ``contract_acquire.acquire_contract`` block (E1 amendment E)."""
    if not isinstance(capture_doc, Mapping):
        return {}
    block = capture_doc.get("contract_acquire")
    if not isinstance(block, Mapping):
        return {}
    acquire_contract = block.get("acquire_contract")
    if not isinstance(acquire_contract, Mapping):
        return {}
    outcomes: dict[str, dict[str, str]] = {}
    for issuer in acquire_contract.get("issuers") or []:
        if not isinstance(issuer, Mapping) or not isinstance(issuer.get("cik"), str):
            continue
        rows = outcomes.setdefault(issuer["cik"], {})
        for row in issuer.get("accessions") or []:
            if isinstance(row, Mapping) and isinstance(row.get("accession"), str):
                rows[row["accession"]] = str(row.get("outcome") or "")
    return outcomes


def _coverage_rows(
    contract: Mapping[str, Any],
    staged: Sequence[_StagedIssuer],
    capture_doc: Mapping[str, Any] | None,
    excluded: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """E4 + ERRATA-6 rule 4: one coverage row per contract issuer.

    ``captured``/``admitted``/``served`` per accession — an 8-K counts
    captured=true, admitted=true, served=false; no product-facing coverage
    tier may count an 8-K as served. r4/D1: an ``only_event_packages``
    issuer is excluded and never staged, yet its admitted 8-Ks — carried
    report-only on its exclusion row — still count admitted (never served).
    Each MISSING accession carries its typed code, joined across the acquire
    and capture reports (the acquire code wins when capture says
    ``no_retained_primary``). REPORT ONLY: this block never enters manifest
    or generation bytes.
    """
    staged_by_cik = {str(row.binding.cik): row for row in staged}
    admitted_events_by_cik: dict[str, set[str]] = {}
    for exclusion in excluded:
        if exclusion.get("reason") != EXCLUSION_ONLY_EVENT_PACKAGES:
            continue
        events = admitted_events_by_cik.setdefault(str(exclusion["cik"]), set())
        events.update(
            str(accession)
            for accession in exclusion.get("admitted_event_accessions") or ()
        )
    capture_by_cik = _capture_outcomes_from_doc(capture_doc)
    acquire_by_cik = _acquire_outcomes(capture_doc)
    coverage: list[dict[str, Any]] = []
    for issuer in contract["issuers"]:
        cik = str(issuer["cik"])
        capture_rows = capture_by_cik.get(cik, {})
        acquire_rows = acquire_by_cik.get(cik, {})
        staged_row = staged_by_cik.get(cik)
        admitted = set(staged_row.admitted_accessions) if staged_row else set()
        # An excluded only-event-packages issuer has no staged row; its 8-Ks
        # still count admitted (served stays staged-only, so never served).
        admitted |= admitted_events_by_cik.get(cik, set())
        served = (
            {
                str(package.manifest["accession"])
                for package in staged_row.admitted_packages
            }
            if staged_row
            else set()
        )
        accession_rows: list[dict[str, Any]] = []
        for entry in issuer.get("accessions") or []:
            accession = str(entry["accession"])
            outcome = capture_rows.get(accession, "")
            captured = outcome in ("captured", "retained_reused") or accession in admitted
            row = {
                "accession": accession,
                "captured": captured,
                "admitted": accession in admitted,
                "served": accession in served,
            }
            if not captured:
                code = (
                    outcome.split(":", 1)[1]
                    if outcome.startswith("member_capture_failed:")
                    else (outcome or "not_attempted")
                )
                if code == "no_retained_primary":
                    acquire_outcome = acquire_rows.get(accession, "")
                    if acquire_outcome.startswith("acquire_failed:"):
                        code = acquire_outcome.split(":", 1)[1]
                row["missing_code"] = code
            accession_rows.append(row)
        coverage.append(
            {
                "ticker": str(issuer["ticker"]),
                "cik": cik,
                "contract_accessions": len(accession_rows),
                "captured": sum(1 for row in accession_rows if row["captured"]),
                "admitted": sum(1 for row in accession_rows if row["admitted"]),
                "served": sum(1 for row in accession_rows if row["served"]),
                "accessions": accession_rows,
            }
        )
    return coverage


def _capture_outcomes_from_doc(
    capture_doc: Mapping[str, Any] | None
) -> dict[str, dict[str, str]]:
    if not isinstance(capture_doc, Mapping) or not isinstance(
        capture_doc.get("issuers"), list
    ):
        return {}
    outcomes: dict[str, dict[str, str]] = {}
    for issuer in capture_doc["issuers"]:
        if not isinstance(issuer, dict) or not isinstance(issuer.get("cik"), str):
            continue
        rows = outcomes.setdefault(issuer["cik"], {})
        for row in issuer.get("accessions") or []:
            if isinstance(row, dict) and isinstance(row.get("accession"), str):
                rows[row["accession"]] = str(row.get("outcome") or "")
    return outcomes


def _print_coverage_shortfalls(coverage: Sequence[Mapping[str, Any]]) -> None:
    """E4: a shortfall never blocks publish, but it is printed LOUDLY."""
    for issuer in coverage:
        for row in issuer["accessions"]:
            if not row.get("captured"):
                print(
                    f"::warning title=fif-production-coverage::{issuer['ticker']} "
                    f"{row['accession']} not captured "
                    f"({row.get('missing_code')}); coverage shortfall recorded",
                    flush=True,
                )


def _load_contract_acquire_block(path_value: Any) -> dict[str, Any] | None:
    """D13 W3: the capture report's ``contract_acquire`` block, validated.

    The block is written by capture-members from the contract lane's summary
    file; carrying it into the publish report keeps one acquisition-state
    trail across capture -> publish. An absent block (a capture run without
    --contract-acquire-report) is lawful; a PRESENT but malformed block is the
    typed refusal — never silently dropped.
    """
    if not path_value:
        return None
    try:
        document = json.loads(Path(path_value).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PublisherError(
            f"capture report is unreadable: {path_value}", code="contract_malformed"
        ) from exc
    if not isinstance(document, dict) or not isinstance(document.get("issuers"), list):
        _fail(f"capture report shape is invalid: {path_value}", code="contract_malformed")
    block = document.get("contract_acquire")
    if block is None:
        return None
    return _validated_summary_shape(block, origin=f"{path_value}#contract_acquire")


def _stage_contract_issuers(
    issuers: Sequence[Mapping[str, Any]],
    *,
    archive_root: Path,
    capture_failures: Mapping[str, Sequence[tuple[str, str]]] | None = None,
) -> tuple[list[_StagedIssuer], list[dict[str, Any]]]:
    """Stage every contract issuer: bind identity, read + admit the CONTRACT
    accessions' retained packages, and collect their capture clocks. Every
    non-publishing issuer gets exactly one typed exclusion row."""
    staged: list[_StagedIssuer] = []
    excluded: list[dict[str, Any]] = []
    for issuer in issuers:
        ticker = str(issuer["ticker"])
        binding = _issuer_binding(issuer)
        if binding is None:
            excluded.append(
                {"ticker": ticker, "cik": issuer["cik"], "reason": EXCLUSION_IDENTITY_NOT_FROZEN}
            )
            continue
        cik = str(issuer["cik"])
        try:
            retained = read_retained_fif_packages(
                archive_root,
                cik=cik,
                accessions=[
                    str(entry["accession"]) for entry in issuer.get("accessions") or []
                ],
            )
        except FifMemberCaptureError as exc:
            if exc.code == "golden_input_refused":
                # Golden contamination is a run-level integrity refusal, never
                # a per-issuer exclusion.
                _fail(str(exc), code="golden_input_refused")
            if exc.code in RETAINED_PACKAGE_INTEGRITY_CODES:
                # ERRATA E1: a tampered/partially-restored package refuses the
                # WHOLE run — nothing is published tonight, no generation is
                # written, no latest.json moves. This raise happens in the
                # staging loop, before any store exists.
                _fail(str(exc), code="retained_package_integrity")
            excluded.append(
                {
                    "ticker": ticker,
                    "cik": cik,
                    "reason": f"member_capture_failed:{exc.code}",
                    "detail": str(exc),
                }
            )
            continue
        if not retained:
            # D6: when the capture report names this issuer's accessions as
            # capture failures, file the capture code — not the misleading
            # no_retained_package (which claims nothing was ever attempted).
            issuer_failures = list((capture_failures or {}).get(cik) or ())
            if issuer_failures:
                code, detail = issuer_failures[0]
                excluded.append(
                    {
                        "ticker": ticker,
                        "cik": cik,
                        "reason": f"member_capture_failed:{code}",
                        "detail": detail,
                    }
                )
            else:
                excluded.append(
                    {"ticker": ticker, "cik": cik, "reason": EXCLUSION_NO_RETAINED_PACKAGE}
                )
            continue
        admitted = []
        event_accessions: list[str] = []
        refusals: list[str] = []
        capture_clocks: list[datetime] = []
        for package in retained:
            try:
                admitted_package = admit_retained_filing_package(
                    index_bytes=package.index_bytes,
                    manifest=dict(package.manifest),
                    members=dict(package.members),
                    witness_bytes=package.witness_bytes,
                    capture_recorded_at=package.capture_recorded_at,
                )
            except AdmittedFilingPackageError as exc:
                refusals.append(f"admission_refused:{exc.code}")
                continue
            # A0 (R-1): bind the admitted package to the staged issuer BEFORE
            # it can reach the store material. The capture manifest carries
            # no entity identity, while the served statement path binds at
            # the issuer level and refuses a package whose manifest
            # entity_id/cik disagree with the issuer binding — so the binding
            # is stamped here, once, at the only publisher seam, from the
            # SAME binding the issuer is staged with (never derived from a
            # ticker). A package whose own identity cross-claims another
            # issuer is refused, never relabelled. No digest inside
            # AdmittedFilingPackage covers the manifest mapping (the index,
            # member, and witness digests bind bytes that this stamp does not
            # touch), so the frozen-dataclass replace is integrity-neutral.
            if canonical_cik(admitted_package.manifest.get("cik")) != binding.cik:
                refusals.append("admission_refused:issuer_cik_mismatch")
                continue
            manifest_entity_id = admitted_package.manifest.get("entity_id")
            if (
                isinstance(manifest_entity_id, str)
                and manifest_entity_id
                and manifest_entity_id != binding.entity_id
            ):
                refusals.append("admission_refused:issuer_entity_mismatch")
                continue
            if manifest_entity_id != binding.entity_id:
                admitted_package = replace(
                    admitted_package,
                    manifest={**admitted_package.manifest, "entity_id": binding.entity_id},
                )
            # ERRATA-6 rule 1: an admitted 8-K is counted but NEVER passed
            # into the build_production_dataset_store material (the false R6
            # premise: production_datasets._statement_trees_role_payload
            # calls reconstruct_primary_statements on EVERY package).
            if str(admitted_package.manifest.get("form") or "") == "8-K":
                event_accessions.append(str(admitted_package.manifest["accession"]))
                continue
            admitted.append(admitted_package)
            # ERRATA-6 rule 3: only MATERIAL packages contribute clocks.
            capture_clocks.append(
                _require_clock(package.capture_recorded_at, "capture_recorded_at")
            )
        if not admitted:
            reason = (
                EXCLUSION_ONLY_EVENT_PACKAGES
                if event_accessions
                else (refusals[0] if refusals else EXCLUSION_NO_RETAINED_PACKAGE)
            )
            exclusion = {
                "ticker": ticker,
                "cik": cik,
                "reason": reason,
                "detail": "; ".join(sorted(set(refusals))),
            }
            if reason == EXCLUSION_ONLY_EVENT_PACKAGES:
                # r4/D1 (ERRATA-6 rule 4): this issuer is never staged, but its
                # admitted 8-Ks must stay countable as admitted — carry them
                # REPORT-ONLY on the exclusion row so _coverage_rows can count
                # them admitted (never served) without staging the issuer. The
                # accessions still never enter material, manifest, generation,
                # index or role bytes, and their clocks never enter T_c.
                exclusion["admitted_event_accessions"] = sorted(set(event_accessions))
            excluded.append(exclusion)
            continue
        staged.append(
            _StagedIssuer(
                issuer=issuer,
                binding=binding,
                admitted_packages=tuple(admitted),
                capture_clocks=tuple(capture_clocks),
                event_accessions=tuple(sorted(set(event_accessions))),
            )
        )
    return staged, excluded


def _content_clock(
    capture_clocks: Sequence[datetime], registry_clocks: Sequence[datetime]
) -> datetime:
    """T_c (ERRATA-3): max(capture clocks, rule clocks, registry clocks)."""
    return max([*capture_clocks, *_rule_clocks(), *registry_clocks])


def _build_material(
    staged: _StagedIssuer,
    *,
    registry_payload: Mapping[str, Any],
    registry_clocks: Sequence[datetime],
    admitted_at: datetime,
) -> ProductionDatasetMaterial:
    """Build one issuer's material at the GIVEN clock (never now())."""
    ledger, filing_metadata, _report = _convert_admitted_packages(
        staged.admitted_packages
    )
    floor = min(staged.capture_clocks)
    # The S2-p seam, DIRECT (spec §3): the module-level import above names
    # ``mint_production_lineage_evidence`` and nothing else — never a mint
    # layer or golden provider. One call per published issuer, clock-equal to
    # the material's admission clock, return landing UNCHANGED. D11: the seam
    # call rides the wrapper so a LineageEvidenceError is typed
    # lineage_mint_failed instead of generic publish_failed.
    lineage_evidence = _mint_lineage_evidence(
        ledger, staged.admitted_packages, system_available_at=admitted_at
    )
    binding = staged.binding
    issuer = staged.issuer
    return ProductionDatasetMaterial(
        binding=binding,
        entity=EntityInput(
            entity_id=binding.entity_id,
            cik=binding.cik,
            ticker=binding.ticker,
            name=str(issuer.get("legal_name") or binding.ticker),
            identity_basis="sec-cik",
            source_entity_id=binding.source_entity_id,
        ),
        ledger=ledger,
        filing_metadata=filing_metadata,
        registry_payload=registry_payload,
        admitted_at=admitted_at,
        source_recorded_at_floor=floor,
        packages=tuple(staged.admitted_packages),
        lineage_evidence=tuple(lineage_evidence),
        security_id=str(issuer["security_master_binding"].get("security_id") or "") or None,
        listing_key=str(issuer["security_master_binding"].get("listing_key") or "") or None,
    )


@dataclass
class _IssuerPlan:
    """One issuer's ERRATA-3 plan: outcome, clock basis, and the material
    built at the chosen clock (the commit phase reuses it verbatim)."""

    staged: _StagedIssuer
    outcome: str
    clock_basis: str
    admitted_at: datetime
    generation_id: str
    manifest_key: str
    lineage_receipt_count: int
    material: Any = field(repr=False, default=None)

    # M1 (reviewer minor, C0-c): the outcome/clock_basis pairing is a
    # programming invariant, enforced at construction. ``published`` pairs
    # with a content or run-recorded clock basis; ``unchanged`` pairs with
    # latest_unchanged ONLY. Any other pair is a constructor ValueError
    # naming the pair — never a silently inconsistent report row.
    _VALID_OUTCOME_CLOCK_BASIS = frozenset(
        {
            ("published", "content"),
            ("published", "run_recorded_at"),
            ("unchanged", "latest_unchanged"),
        }
    )

    def __post_init__(self) -> None:
        pair = (str(self.outcome), str(self.clock_basis))
        if pair not in self._VALID_OUTCOME_CLOCK_BASIS:
            raise ValueError(
                f"invalid issuer-plan outcome/clock_basis pair: {pair!r}"
            )


def _plan_issuer(
    staged: _StagedIssuer,
    *,
    real_store: Any,
    scratch_store: Any,
    registry_payload: Mapping[str, Any],
    registry_clocks: Sequence[datetime],
    recorded_at: datetime,
) -> _IssuerPlan:
    """ERRATA-3 1: plan ONE issuer with ZERO real-store writes.

    a. Read L = load_latest_generation; a pointer that exists but cannot be
       verified is the typed ``latest_pointer_unreadable``, never absence.
    b. Clock-independent UNCHANGED test: with L present and
       ``floor <= L.admitted_at``, build the candidate at L's own admission
       clock into the SCRATCH store and compare generation ids — equal means
       outcome ``unchanged`` and NO real-store write for this issuer. Any
       exception in that comparison build means CHANGED (the authoritative
       build below re-raises real errors).
    c. Clock choice: T_c if (L is None or T_c > L.published_at); else T_r if
       T_r > L.published_at; else the typed ``admission_clock_not_after_latest``
       naming T_c, T_r and L.published_at, raised before any real-store write.
       L.published_at == L.admitted_at by the pointer payload's construction
       (``production_datasets._pointer_payload`` writes published_at=admitted_at).
    e. Build the authoritative candidate at the chosen clock in the scratch
       store — the lineage mint and every role must build before ANY real
       write begins.
    """
    binding = staged.binding
    t_c = _content_clock(staged.capture_clocks, registry_clocks)
    floor = min(staged.capture_clocks)
    try:
        latest = load_latest_generation(real_store, binding.entity_id)
    except ProductionDatasetError as exc:
        raise PublisherError(
            f"latest.json for {binding.entity_id} exists but cannot be verified "
            f"(latest_pointer_unreadable): {exc}",
            code="latest_pointer_unreadable",
        ) from exc
    except PublisherError:
        raise
    except Exception as exc:  # noqa: BLE001 - M2: a transient store read is typed
        raise PublisherError(
            f"latest.json transient store read for {binding.entity_id} "
            f"({type(exc).__name__}: {exc}) cannot be verified "
            "(latest_pointer_unreadable)",
            code="latest_pointer_unreadable",
        ) from exc
    if latest is not None and floor <= latest.admitted_at:
        try:
            comparison_material = _build_material(
                staged,
                registry_payload=registry_payload,
                registry_clocks=registry_clocks,
                admitted_at=latest.admitted_at,
            )
            comparison = publish_production_dataset(scratch_store, comparison_material)
        except Exception:  # noqa: BLE001 - treat as CHANGED; the plan below re-raises
            comparison = None
        else:
            if comparison.generation_id == latest.generation_id:
                return _IssuerPlan(
                    staged=staged,
                    outcome="unchanged",
                    clock_basis="latest_unchanged",
                    admitted_at=latest.admitted_at,
                    generation_id=latest.generation_id,
                    manifest_key=production_manifest_key(
                        binding.entity_id, latest.generation_id
                    ),
                    lineage_receipt_count=len(
                        tuple(comparison_material.lineage_evidence)
                    ),
                    material=comparison_material,
                )
    if latest is None or t_c > latest.admitted_at:
        chosen, basis = t_c, "content"
    elif recorded_at > latest.admitted_at:
        chosen, basis = recorded_at, "run_recorded_at"
    else:
        raise PublisherError(
            "admission_clock_not_after_latest: neither the content clock "
            f"t_c={utc_text(t_c)} nor the run clock "
            f"t_r={utc_text(recorded_at)} is later than the latest published "
            f"clock latest_published_at={utc_text(latest.admitted_at)} for "
            f"{binding.entity_id}, and no clock is ever clamped, rewound, or "
            "re-stamped to force agreement",
            code="admission_clock_not_after_latest",
        )
    material = _build_material(
        staged,
        registry_payload=registry_payload,
        registry_clocks=registry_clocks,
        admitted_at=chosen,
    )
    scratch_publication = publish_production_dataset(scratch_store, material)
    return _IssuerPlan(
        staged=staged,
        outcome="published",
        clock_basis=basis,
        admitted_at=chosen,
        generation_id=scratch_publication.generation_id,
        manifest_key=scratch_publication.manifest_key,
        lineage_receipt_count=len(tuple(material.lineage_evidence)),
        material=material,
    )


def _issuer_summary(plan: _IssuerPlan) -> dict[str, Any]:
    binding = plan.staged.binding
    return {
        "entity_id": binding.entity_id,
        "ticker": binding.ticker,
        "cik": binding.cik,
    }


def _report_row(
    plan: _IssuerPlan,
    *,
    generation_id: str,
    manifest_key: str,
    admitted_at: datetime | str,
) -> dict[str, Any]:
    """One ``published`` report row (outcome published OR unchanged)."""
    admitted_text = (
        admitted_at if isinstance(admitted_at, str) else (utc_text(admitted_at) or "")
    )
    return {
        **_issuer_summary(plan),
        "outcome": plan.outcome,
        "clock_basis": plan.clock_basis,
        "generation_id": generation_id,
        "manifest_key": manifest_key,
        "admitted_at": admitted_text,
        "source_recorded_at_floor": utc_text(min(plan.staged.capture_clocks)) or "",
        "admitted_accessions": [
            str(package.manifest["accession"])
            for package in plan.staged.admitted_packages
        ],
        # ERRATA-6 rule 2: the 8-K accessions appear ONLY here — a report-only
        # key of the publish report; never in manifest, generation, index or
        # role bytes.
        "admitted_event_accessions": list(plan.staged.event_accessions),
        "lineage_receipt_count": plan.lineage_receipt_count,
    }


def _commit_code(exc: BaseException) -> str:
    """The typed publisher code a COMMIT-phase failure reports (ERRATA-3 2)."""
    if isinstance(exc, PublisherError):
        return exc.code
    if isinstance(exc, FifMemberCaptureError):
        if exc.code == "golden_input_refused":
            return "golden_input_refused"
        if exc.code in RETAINED_PACKAGE_INTEGRITY_CODES:
            return "retained_package_integrity"
    return "publish_failed"


def _report_base(
    recorded_at: datetime, registry_clocks: Sequence[datetime]
) -> dict[str, Any]:
    return {
        "schema": PUBLISH_REPORT_SCHEMA,
        "recorded_at": utc_text(recorded_at) or "",
        "rule_clocks": {
            "confirmation_rule_available_at": utc_text(CONFIRMATION_RULE_AVAILABLE_AT),
            "confirmation_chain_rule_available_at": utc_text(
                CONFIRMATION_CHAIN_RULE_AVAILABLE_AT
            ),
            "registry_available_at": sorted(
                {utc_text(clock) for clock in registry_clocks}
            ),
        },
    }


def _write_report(report: Mapping[str, Any], report_path_value: Any) -> None:
    if not report_path_value:
        return
    target = Path(report_path_value)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _demote_coverage_after_commit_failure(
    coverage: Sequence[Mapping[str, Any]],
    *,
    failed_cik: str,
    failed_code: str,
    not_attempted_ciks: set[str],
) -> list[dict[str, Any]]:
    """MINOR-5: the PARTIAL report's coverage must reflect the commit loop.

    Coverage is computed before planning and the commit loop, so without this
    demotion the partial report would claim served=true for an issuer whose
    commit failed or was never attempted. Every accession row of the FAILED
    issuer gets served=False plus ``served_withheld: "commit_failed:<code>"``;
    every NOT-ATTEMPTED issuer's rows get served=False plus
    ``served_withheld: "commit_not_attempted"``; those issuers' ``served``
    counts are recomputed. Published and unchanged issuers keep served.
    REPORT ONLY — this never enters manifest or generation bytes.
    """
    demoted: dict[str, str] = {}
    if failed_cik:
        demoted[failed_cik] = f"commit_failed:{failed_code}"
    for cik in not_attempted_ciks:
        demoted.setdefault(cik, "commit_not_attempted")
    if not demoted:
        return [dict(row) for row in coverage]
    out: list[dict[str, Any]] = []
    for issuer_row in coverage:
        row = dict(issuer_row)
        withheld = demoted.get(str(row.get("cik") or ""))
        if withheld is not None:
            accessions = []
            for item in row.get("accessions") or []:
                entry = dict(item)
                entry["served"] = False
                entry["served_withheld"] = withheld
                accessions.append(entry)
            row["accessions"] = accessions
            row["served"] = sum(1 for entry in accessions if entry["served"])
        out.append(row)
    return out


def _run_publish(args: argparse.Namespace) -> int:
    contract = load_fif_coverage_contract(args.coverage_file)
    raw_root = Path(args.raw_root)
    archive_root = Path(args.archive_root)
    refuse_repository_fixture_inputs(raw_root, archive_root)
    recorded_at = _require_clock(args.recorded_at, "--recorded-at")
    registry_payload = snapshot_core_registry_payload(Path(args.repo_root))
    registry_clocks = _registry_available_clocks(registry_payload)

    staged, excluded = _stage_contract_issuers(
        contract["issuers"],
        archive_root=archive_root,
        capture_failures=_load_capture_failures(args.capture_report),
    )
    # D13 W3: the contract acquire state rides the publish report too (report
    # ONLY — no generation byte moves; the block was validated against the
    # frozen summary shape above).
    contract_acquire = _load_contract_acquire_block(args.capture_report)
    # C0-c E4: the publish coverage row (report only). The capture document —
    # outcomes plus its contract_acquire.acquire_contract block — is the join
    # input for per-accession typed codes.
    capture_doc: dict[str, Any] | None = None
    if args.capture_report:
        try:
            capture_doc = json.loads(Path(args.capture_report).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            capture_doc = None
    coverage = _coverage_rows(contract, staged, capture_doc, excluded)

    # FUTURE-CLOCK REFUSAL (seat amendment (a)) — still FIRST and unchanged
    # (ERRATA-3 1.d): every issuer's CLOCK RULE is computed BEFORE any store
    # exists or writes — a later admitted_at than the run's recorded-at
    # refuses the whole run, never clamps a clock, never mints a future-dated
    # generation. The chosen clock is therefore always <= T_r.
    for staged_row in staged:
        computed = _content_clock(staged_row.capture_clocks, registry_clocks)
        if computed > recorded_at:
            _fail(
                "admitted_at_after_recorded_at: computed admitted_at "
                f"{utc_text(computed)} is later than --recorded-at {utc_text(recorded_at)}",
                code="admitted_at_after_recorded_at",
            )

    store = (
        build_production_dataset_store(Path(args.store_dir))
        if args.store_dir
        else build_production_dataset_store()
    )
    if store is None:
        _fail("production dataset store is not configured", code="publish_failed")

    # ERRATA-3 1 + 4: PLAN over ALL issuers into a SCRATCH store (a fresh
    # tempdir local store — no engine "pure plan" split; production_datasets
    # stays unowned and untouched). No real write begins until EVERY issuer's
    # plan succeeds; publish order is deterministic by entity_id.
    scratch_dir = tempfile.mkdtemp(prefix="fif-production-plan-")
    try:
        scratch_store = build_production_dataset_store(local_dir=Path(scratch_dir))
        plans = [
            _plan_issuer(
                staged_row,
                real_store=store,
                scratch_store=scratch_store,
                registry_payload=registry_payload,
                registry_clocks=registry_clocks,
                recorded_at=recorded_at,
            )
            for staged_row in sorted(staged, key=lambda item: item.binding.entity_id)
        ]
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)

    # COMMIT (ERRATA-3 2): publish each planned non-unchanged issuer to the
    # REAL store at its chosen clock, then read-back-verify the pointer NAMES
    # the generation. A commit-phase failure still writes the PARTIAL report
    # (committed / failed + typed code / not-attempted) to --report-path
    # before exiting non-zero.
    published: list[dict[str, Any]] = []
    failed: dict[str, Any] | None = None
    not_attempted: list[dict[str, Any]] = []
    for plan in plans:
        # M3: an UNCHANGED plan needs no real-store write, so it is reported
        # as its unchanged row in ``published`` (same row shape) whether it
        # comes before OR after the failed issuer; ``not_attempted`` lists
        # ONLY skipped plans whose outcome is "published".
        if plan.outcome == "unchanged":
            # Equal generation id at L's own clock: NO real-store write for
            # this issuer; latest.json already names the generation.
            published.append(
                _report_row(
                    plan,
                    generation_id=plan.generation_id,
                    manifest_key=plan.manifest_key,
                    admitted_at=plan.admitted_at,
                )
            )
            continue
        if failed is not None:
            not_attempted.append(_issuer_summary(plan))
            continue
        try:
            publication = publish_production_dataset(store, plan.material)
            # Read-back self-check: the POINTER must NAME the generation just
            # written, not merely exist beside it.
            latest = load_latest_generation(store, plan.staged.binding.entity_id)
            if latest is None or latest.generation_id != publication.generation_id:
                _fail(
                    "latest.json does not name the published generation for "
                    f"{plan.staged.binding.entity_id}",
                    code="verify_failed",
                )
        except Exception as exc:  # noqa: BLE001 - partial report, then typed exit
            failed = {
                **_issuer_summary(plan),
                "code": _commit_code(exc),
                "error": f"{type(exc).__name__}: {exc}",
            }
            continue
        published.append(
            _report_row(
                plan,
                generation_id=publication.generation_id,
                manifest_key=publication.manifest_key,
                admitted_at=publication.admitted_at,
            )
        )

    if failed is not None:
        # MINOR-5: demote coverage before writing the partial report — the
        # failed issuer's rows are served=False + served_withheld
        # commit_failed:<code>, the not-attempted issuer's rows are
        # served=False + commit_not_attempted; committed issuers keep served.
        coverage = _demote_coverage_after_commit_failure(
            coverage,
            failed_cik=str(failed.get("cik") or ""),
            failed_code=str(failed.get("code") or ""),
            not_attempted_ciks={
                str(row.get("cik") or "") for row in not_attempted
            },
        )
        partial = {
            **_report_base(recorded_at, registry_clocks),
            "published": published,
            "excluded": excluded,
            "failed": failed,
            "not_attempted": not_attempted,
            "coverage": coverage,
        }
        if contract_acquire is not None:
            partial["contract_acquire"] = contract_acquire
        _write_report(partial, args.report_path)
        print(json.dumps(partial, ensure_ascii=False, sort_keys=True, indent=2), flush=True)
        _fail(
            f"commit-phase publish failure for {failed['ticker']} "
            f"({failed['code']}): {failed['error']}",
            code=failed["code"],
        )

    report = {
        **_report_base(recorded_at, registry_clocks),
        "published": published,
        "excluded": excluded,
        "coverage": coverage,
    }
    if contract_acquire is not None:
        report["contract_acquire"] = contract_acquire
    _write_report(report, args.report_path)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2), flush=True)
    # E4: a shortfall never blocks publish, but it is printed loudly.
    _print_coverage_shortfalls(coverage)
    verify_report(report, store)
    return 0


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------


def project_census_reachability(summary: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """q8's offline acceptance projection over the committed census summary.

    Every contract accession is REACHABLE when its row sits in ``recent``
    with no covering pages, or under exactly one covering ``filings.files[]``
    page; anything else is a typed residual (``submissions_page_not_found``
    for zero covering pages off recent, ``submissions_page_ambiguous`` for
    more than one covering page — whatever ``location`` says).
    """
    residuals = {"submissions_page_not_found", "submissions_page_ambiguous"}
    projection: dict[str, dict[str, Any]] = {}
    for issuer in summary.get("issuers") or []:
        reachable = 0
        residual_rows: list[dict[str, str]] = []
        for entry in issuer.get("accessions") or []:
            covering = entry.get("covering_pages") or []
            location = entry.get("location")
            # r4/D2: reachability is PAGE-DERIVED — recent with NO covering
            # pages, or exactly ONE covering page. A non-empty ``location``
            # string never rescues a 0-page row (submissions_page_not_found)
            # or collapses a 2+-page row (submissions_page_ambiguous).
            if (location == "recent" and not covering) or len(covering) == 1:
                reachable += 1
                continue
            residual_rows.append(
                {
                    "accession": str(entry.get("accession") or ""),
                    "missing_code": (
                        "submissions_page_ambiguous"
                        if len(covering) > 1
                        else "submissions_page_not_found"
                    ),
                }
            )
        projection[str(issuer.get("ticker") or "")] = {
            "reachable": reachable,
            "total": len(issuer.get("accessions") or []),
            "residuals": residual_rows,
            "residual_codes": sorted(
                {row["missing_code"] for row in residual_rows} & residuals
            ),
        }
    return projection


def verify_report(report: Mapping[str, Any], store: Any) -> None:
    """Assert the report covers the contract exactly once and pointers NAME generations."""
    published = report.get("published")
    excluded = report.get("excluded")
    if not isinstance(published, list) or not isinstance(excluded, list):
        _fail("publish report is malformed", code="verify_failed")
    seen: dict[str, str] = {}
    for row in (*published, *excluded):
        if not isinstance(row, Mapping):
            _fail("publish report row is malformed", code="verify_failed")
        key = str(row.get("cik") or "")
        if not key:
            _fail("publish report row carries no identity", code="verify_failed")
        if key in seen:
            _fail(
                f"contract issuer appears more than once in the publish report: {key}",
                code="verify_failed",
            )
        seen[key] = str(row.get("reason") or row.get("generation_id") or "")
    for row in excluded:
        reason = str(row.get("reason") or "")
        lawful = (
            reason == EXCLUSION_IDENTITY_NOT_FROZEN
            or reason == EXCLUSION_NO_RETAINED_PACKAGE
            or reason == EXCLUSION_ONLY_EVENT_PACKAGES
            or reason.startswith("admission_refused:")
            or reason.startswith("member_capture_failed:")
        )
        if not lawful:
            _fail(f"exclusion reason is outside the closed vocabulary: {reason}", code="verify_failed")
        # r4/D1 (ERRATA-6 rule 4): the report-only admitted-8-K key is lawful
        # ONLY on an only_event_packages exclusion and must be a list of
        # non-empty accession strings.
        events = row.get("admitted_event_accessions")
        if events is not None and (
            reason != EXCLUSION_ONLY_EVENT_PACKAGES
            or not isinstance(events, list)
            or not all(isinstance(item, str) and item for item in events)
        ):
            _fail(
                "exclusion admitted_event_accessions is malformed: " f"{reason}",
                code="verify_failed",
            )
    # E4: the coverage block (when present) must cover every contract issuer
    # exactly once and never count an 8-K as served without being admitted.
    coverage = report.get("coverage")
    if coverage is not None:
        if not isinstance(coverage, list):
            _fail("publish report coverage block is malformed", code="verify_failed")
        seen_ciks = set()
        for issuer_row in coverage:
            if not isinstance(issuer_row, Mapping) or not isinstance(
                issuer_row.get("cik"), str
            ):
                _fail("coverage issuer row is malformed", code="verify_failed")
            if issuer_row["cik"] in seen_ciks:
                _fail(
                    f"coverage issuer appears more than once: {issuer_row['cik']}",
                    code="verify_failed",
                )
            seen_ciks.add(issuer_row["cik"])
            for row in issuer_row.get("accessions") or []:
                if not isinstance(row, Mapping) or not isinstance(
                    row.get("accession"), str
                ):
                    _fail("coverage accession row is malformed", code="verify_failed")
                if row.get("served") and not row.get("admitted"):
                    _fail(
                        "coverage row serves an unadmitted accession",
                        code="verify_failed",
                    )
                # MINOR-5: served_withheld (partial-report demotion marker) is
                # lawful only as a non-empty string on a NOT-served row.
                withheld = row.get("served_withheld")
                if withheld is not None and (
                    not isinstance(withheld, str)
                    or not withheld
                    or row.get("served")
                ):
                    _fail(
                        f"coverage served_withheld is malformed: {withheld!r}",
                        code="verify_failed",
                    )
        # r4/D1 (ERRATA-6 rule 4): every 8-K named admitted on an exclusion
        # row must appear admitted=True and served=False in its issuer's
        # coverage row.
        coverage_by_cik = {str(item["cik"]): item for item in coverage}
        for row in excluded:
            events = row.get("admitted_event_accessions") or []
            if not events:
                continue
            issuer_row = coverage_by_cik.get(str(row.get("cik") or ""))
            if issuer_row is None:
                _fail(
                    "coverage block omits an excluded issuer with admitted 8-Ks",
                    code="verify_failed",
                )
            by_accession = {
                str(item.get("accession")): item
                for item in issuer_row.get("accessions") or []
            }
            for accession in events:
                accession_row = by_accession.get(str(accession))
                if (
                    accession_row is None
                    or not accession_row.get("admitted")
                    or accession_row.get("served")
                ):
                    _fail(
                        "coverage row misreports an excluded issuer's admitted "
                        f"8-K: {accession}",
                        code="verify_failed",
                    )
    for row in published:
        generation_id = str(row.get("generation_id") or "")
        entity_id = str(row.get("entity_id") or "")
        if not generation_id or not entity_id:
            _fail("published row is missing its generation identity", code="verify_failed")
        # ERRATA-3 3: closed vocabularies for the per-issuer outcome columns.
        outcome = str(row.get("outcome") or "")
        clock_basis = str(row.get("clock_basis") or "")
        if outcome not in ("published", "unchanged"):
            _fail(
                f"published row outcome is outside the closed vocabulary: {outcome}",
                code="verify_failed",
            )
        if clock_basis not in ("content", "run_recorded_at", "latest_unchanged"):
            _fail(
                "published row clock_basis is outside the closed vocabulary: "
                f"{clock_basis}",
                code="verify_failed",
            )
        latest = load_latest_generation(store, entity_id)
        if latest is None or latest.generation_id != generation_id:
            _fail(
                f"latest.json does not name the published generation for {entity_id}",
                code="verify_failed",
            )


def _run_verify(args: argparse.Namespace) -> int:
    contract = load_fif_coverage_contract(args.coverage_file)
    try:
        report = json.loads(Path(args.report_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PublisherError(
            f"publish report is unreadable: {args.report_path}", code="verify_failed"
        ) from exc
    store = (
        build_production_dataset_store(Path(args.store_dir))
        if args.store_dir
        else build_production_dataset_store()
    )
    if store is None:
        _fail("production dataset store is not configured", code="verify_failed")
    verify_report(report, store)
    contract_ciks = {str(issuer["cik"]) for issuer in contract["issuers"]}
    seen = {
        str(row.get("cik"))
        for row in (*report.get("published", []), *report.get("excluded", []))
        if isinstance(row, Mapping)
    }
    missing = contract_ciks - seen
    extra = seen - contract_ciks
    if missing or extra:
        _fail(
            f"publish report does not cover the contract exactly once "
            f"(missing={sorted(missing)}, unknown={sorted(extra)})",
            code="verify_failed",
        )
    coverage = report.get("coverage") or []
    coverage_summary = [
        {
            "ticker": row.get("ticker"),
            "cik": row.get("cik"),
            "captured": row.get("captured"),
            "admitted": row.get("admitted"),
            "served": row.get("served"),
            "contract_accessions": row.get("contract_accessions"),
        }
        for row in coverage
        if isinstance(row, Mapping)
    ]
    print(
        json.dumps(
            {
                "schema": report.get("schema"),
                "verified": True,
                "issuers": len(seen),
                "coverage": coverage_summary,
            },
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    targets = subparsers.add_parser("targets", help="Print --target extras derived from the contract")
    targets.add_argument("--coverage-file", type=Path, required=True)
    targets.add_argument("--targets-file", type=Path, required=True)
    # ERRATA E2-R: the ticker cap is REQUIRED with no default — the single
    # value lives in the workflow (defined exactly once there) and the
    # publisher carries no second literal.
    targets.add_argument("--max-tickers", type=int, required=True)

    capture = subparsers.add_parser("capture-members", help="D1 member capture over retained primaries")
    capture.add_argument("--coverage-file", type=Path, required=True)
    capture.add_argument("--raw-root", type=Path, required=True)
    capture.add_argument("--archive-root", type=Path, required=True)
    capture.add_argument("--recorded-at", required=True, help="Explicit UTC capture clock")
    capture.add_argument("--user-agent", default=None, help="SEC user agent override (tests inject one)")
    capture.add_argument("--min-interval-seconds", type=float, default=0.12)
    capture.add_argument("--max-document-bytes", type=int, default=32 * 1024 * 1024)
    # D12: the run budget's single source is the capture module's constant —
    # the publisher carries no second 256 MiB literal.
    capture.add_argument("--run-budget-bytes", type=int, default=DEFAULT_RUN_BUDGET_BYTES)
    capture.add_argument(
        "--contract-acquire-report",
        type=Path,
        default=None,
        help="The contract acquire step's summary JSON; its contract_acquire block is copied into the capture report",
    )
    capture.add_argument(
        "--report-path",
        type=Path,
        default=None,
        help="Write the JSON capture report here (the workflow uploads it)",
    )

    summary = subparsers.add_parser(
        "contract-acquire-summary",
        help="D13: summarize the isolated contract acquire (partial -> ::warning, never fatal)",
    )
    summary.add_argument(
        "--result",
        type=Path,
        required=True,
        help="The isolated contract wave-2 run's stdout result JSON",
    )
    summary.add_argument(
        "--report-path",
        type=Path,
        default=None,
        help="Write the JSON summary here (the workflow uploads it)",
    )

    acquire = subparsers.add_parser(
        "acquire-contract",
        help="C0-c E1: contract-keyed primary + manifest acquisition for every contract accession",
    )
    acquire.add_argument("--coverage-file", type=Path, required=True)
    acquire.add_argument("--raw-root", type=Path, required=True)
    acquire.add_argument("--archive-root", type=Path, required=True)
    acquire.add_argument("--recorded-at", required=True, help="Explicit UTC acquisition clock")
    acquire.add_argument("--user-agent", default=None, help="SEC user agent override (tests inject one)")
    acquire.add_argument("--min-interval-seconds", type=float, default=0.12)
    acquire.add_argument("--max-document-bytes", type=int, default=32 * 1024 * 1024)
    # E1-c amendment (B): acquire-contract is its own process with its OWN
    # pre-fetch budget; the single source of the number is the capture
    # module's constant — no second literal.
    acquire.add_argument("--run-budget-bytes", type=int, default=DEFAULT_RUN_BUDGET_BYTES)
    acquire.add_argument(
        "--contract-acquire-summary",
        type=Path,
        default=None,
        help="Merge this run's report into the contract-acquire summary file as its acquire_contract block",
    )
    acquire.add_argument(
        "--report-path",
        type=Path,
        default=None,
        help="Write the JSON acquisition report here",
    )

    publish = subparsers.add_parser("publish", help="Publish production generations (hard gate)")
    publish.add_argument("--coverage-file", type=Path, required=True)
    publish.add_argument("--raw-root", type=Path, required=True)
    publish.add_argument("--archive-root", type=Path, required=True)
    publish.add_argument("--recorded-at", required=True, help="Explicit UTC run clock")
    publish.add_argument("--store-dir", type=Path, default=None, help="Explicit local directory store")
    publish.add_argument("--repo-root", type=Path, default=_ROOT)
    publish.add_argument("--report-path", type=Path, default=None)
    publish.add_argument(
        "--capture-report",
        type=Path,
        default=None,
        help="The capture step's report; capture failures file as member_capture_failed:<code>",
    )

    verify = subparsers.add_parser("verify", help="Re-verify a publish report against the store")
    verify.add_argument("--coverage-file", type=Path, required=True)
    verify.add_argument("--report-path", type=Path, required=True)
    verify.add_argument("--store-dir", type=Path, default=None)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "targets":
            return _run_targets(args)
        if args.command == "capture-members":
            return _run_capture_members(args)
        if args.command == "contract-acquire-summary":
            return _run_contract_acquire_summary(args)
        if args.command == "acquire-contract":
            return _run_acquire_contract(args)
        if args.command == "publish":
            return _run_publish(args)
        if args.command == "verify":
            return _run_verify(args)
        parser.error(f"unknown command: {args.command}")
        return 2
    except PublisherError as exc:
        # M2: a TYPED refusal prints exactly its line-start ::error — no raw
        # traceback noise on stderr (the typed code + message, which names the
        # underlying exception type, is the evidence).
        _error_annotation(f"fif_production_datasets-{exc.code}", str(exc))
        return 1
    except (
        FifMemberCaptureError,
        AdmittedFilingPackageError,
        Exception,
    ) as exc:
        traceback.print_exc(file=sys.stderr)
        code = "publish_failed"
        if isinstance(exc, FifMemberCaptureError):
            if exc.code == "golden_input_refused":
                code = "golden_input_refused"
            elif exc.code in RETAINED_PACKAGE_INTEGRITY_CODES:
                code = "retained_package_integrity"
            else:
                code = f"member_capture_failed-{exc.code}"
        _error_annotation(f"fif_production_datasets-{code}", f"{type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
