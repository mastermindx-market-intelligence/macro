"""FIF C0-b: publish production issuer datasets from lane-retained bytes (hard gate).

Scheduled-lane producer for the D3 production dataset store. Four subcommands,
one frozen coverage contract, and NO ticker or CIK literal anywhere — the
issuer universe is read from the contract at runtime:

* ``targets`` derives the wave-2 ``--target TICKER=CIK`` extras the contract
  adds over the incumbent pinned targets file, and hard-fails if the union
  would exceed ``--max-tickers``. The first wave-2 invocation consumes its
  stdout verbatim, so no issuer ever rides a YAML literal.
* ``capture-members`` performs the D1 member-capture pass (see
  ``engine/fundamental_forensics/fif_member_capture.py``) over the warm
  ``--raw-root``/``--archive-root`` trees under the ONE shared
  ``SecRequestPacer``. It is offline on every input except the SEC archive
  fetches it makes through the incumbent collector.
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
``::error`` (``print(..., flush=True)``, never through a logger) — this is a
publication gate, not the ``build_fundamental_forensics`` swallow-all shape.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from collectors.edgar_forensics import _user_agent  # noqa: E402
from collectors.sec_document_spine import SecFilingArchiveCollector  # noqa: E402
from collectors.sec_request_pacer import SecRequestPacer  # noqa: E402
from engine.fundamental_forensics.admitted_filing_package import (  # noqa: E402
    AdmittedFilingPackageError,
    admit_retained_filing_package,
)
from engine.fundamental_forensics.fif_member_capture import (  # noqa: E402
    FifMemberCaptureError,
    capture_fif_filing_packages,
    read_retained_fif_packages,
    refuse_repository_fixture_inputs,
)
from engine.fundamental_forensics.financial_intelligence_packet import EntityInput  # noqa: E402
from engine.fundamental_forensics.ixbrl_raw_ledger import convert_parsed_filings  # noqa: E402
from engine.fundamental_forensics.lineage_evidence import (  # noqa: E402
    CONFIRMATION_CHAIN_RULE_AVAILABLE_AT,
    CONFIRMATION_RULE_AVAILABLE_AT,
)
from engine.fundamental_forensics.models import parse_utc, utc_text  # noqa: E402
from engine.fundamental_forensics.production_datasets import (  # noqa: E402
    ProductionDatasetMaterial,
    build_production_dataset_store,
    load_latest_generation,
    lineage_from_role_payload,
    publish_production_dataset,
    snapshot_core_registry_payload,
)
from engine.fundamental_forensics.query_service import CanonicalEntityBinding  # noqa: E402
from collectors.sec_filing_parser import (  # noqa: E402
    SecFilingParseError,
    parse_sec_filing_document,
)

# The S2-p seam module (engine/fundamental_forensics/production_lineage.py)
# does not exist at this lane's base; it is imported lazily INSIDE the publish
# call path so the base stays importable, and tests install a fake via
# sys.modules. Phase B (after S2-p merges) removes the fake.
_LINEAGE_SEAM_MODULE = "engine.fundamental_forensics.production_lineage"

COVERAGE_CONTRACT_SCHEMA = "fundamental_forensics.coverage_contract/v1"
PUBLISH_REPORT_SCHEMA = "fundamental_forensics.fif_production_publish_report/v1"
EXCLUSION_IDENTITY_NOT_FROZEN = "identity_not_frozen"
EXCLUSION_NO_RETAINED_PACKAGE = "no_retained_package"
PUBLISHER_ERROR_CODES = frozenset(
    {
        "contract_malformed",
        "targets_overflow",
        "admitted_at_after_recorded_at",
        "publish_failed",
        "verify_failed",
        "lineage_mint_failed",
        "golden_input_refused",
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
    print(f"::error title={title}::{message}", flush=True)


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
# capture-members
# ---------------------------------------------------------------------------


def _resolve_user_agent(args: argparse.Namespace) -> str:
    if args.user_agent:
        return str(args.user_agent)
    return _user_agent(_ROOT)


def _run_capture_members(args: argparse.Namespace) -> int:
    contract = load_fif_coverage_contract(args.coverage_file)
    raw_root = Path(args.raw_root)
    archive_root = Path(args.archive_root)
    refuse_repository_fixture_inputs(raw_root, archive_root)
    recorded_at = _require_clock(args.recorded_at, "--recorded-at")
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
    report = capture_fif_filing_packages(
        raw_root=raw_root,
        archive_root=archive_root,
        issuers=list(contract["issuers"]),
        collector=collector,
        pacer=pacer,
        recorded_at=utc_text(recorded_at) or "",
        run_budget_bytes=args.run_budget_bytes,
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2), flush=True)
    return 0


# ---------------------------------------------------------------------------
# CLOCK RULE helpers
# ---------------------------------------------------------------------------


def _registry_available_clocks(payload: Mapping[str, Any]) -> list[datetime]:
    """Every ``available_at`` clock the registry snapshot exposes, parsed."""
    found: list[datetime] = []

    def _scan(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, value in node.items():
                if key == "available_at" and isinstance(value, str) and value.strip():
                    try:
                        parsed = parse_utc(value.strip(), field="registry available_at")
                    except ValueError:
                        parsed = None
                    if parsed is not None:
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


def _mint_lineage_evidence(ledger: Any, packages: Sequence[Any], *, system_available_at: datetime):
    """Lazy S2-p seam: mint lineage evidence through the frozen signature.

    The module is imported at call time because it does not exist at this
    lane's base; a module-level import would break the base. The mint runs
    exactly once per published issuer and its return value lands UNCHANGED in
    ``ProductionDatasetMaterial.lineage_evidence``.
    """
    module = importlib.import_module(_LINEAGE_SEAM_MODULE)
    mint = getattr(module, "mint_production_lineage_evidence", None)
    if not callable(mint):
        _fail(
            f"{_LINEAGE_SEAM_MODULE} does not expose mint_production_lineage_evidence",
            code="lineage_mint_failed",
        )
    return mint(ledger, packages, system_available_at=system_available_at)


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


def _publish_one_issuer(
    *,
    store: Any,
    issuer: Mapping[str, Any],
    binding: CanonicalEntityBinding,
    admitted_packages: tuple[Any, ...],
    capture_clocks: list[datetime],
    registry_payload: Mapping[str, Any],
    registry_clocks: list[datetime],
    repo_root: Path,
) -> dict[str, Any]:
    ledger, filing_metadata, _report = _convert_admitted_packages(admitted_packages)
    admitted_at = max(
        [
            *capture_clocks,
            *_rule_clocks(),
            *registry_clocks,
        ]
    )
    floor = min(capture_clocks)
    lineage_evidence = _mint_lineage_evidence(
        ledger, admitted_packages, system_available_at=admitted_at
    )
    material_binding = binding
    material = ProductionDatasetMaterial(
        binding=material_binding,
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
        packages=tuple(admitted_packages),
        lineage_evidence=tuple(lineage_evidence),
        security_id=str(issuer["security_master_binding"].get("security_id") or "") or None,
        listing_key=str(issuer["security_master_binding"].get("listing_key") or "") or None,
    )
    publication = publish_production_dataset(store, material)
    # Read-back self-check: the POINTER must NAME the generation just written,
    # not merely exist beside it.
    latest = load_latest_generation(store, binding.entity_id)
    if latest is None or latest.generation_id != publication.generation_id:
        _fail(
            f"latest.json does not name the published generation for {binding.entity_id}",
            code="verify_failed",
        )
    return {
        "entity_id": binding.entity_id,
        "ticker": binding.ticker,
        "cik": binding.cik,
        "generation_id": publication.generation_id,
        "manifest_key": publication.manifest_key,
        "admitted_at": publication.admitted_at,
        "source_recorded_at_floor": utc_text(floor) or "",
        "admitted_accessions": [
            str(package.manifest["accession"]) for package in admitted_packages
        ],
        "lineage_receipt_count": len(tuple(lineage_evidence)),
    }


def _run_publish(args: argparse.Namespace) -> int:
    contract = load_fif_coverage_contract(args.coverage_file)
    raw_root = Path(args.raw_root)
    archive_root = Path(args.archive_root)
    refuse_repository_fixture_inputs(raw_root, archive_root)
    recorded_at = _require_clock(args.recorded_at, "--recorded-at")
    registry_payload = snapshot_core_registry_payload(Path(args.repo_root))
    registry_clocks = _registry_available_clocks(registry_payload)

    published: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    staged: list[tuple[Mapping[str, Any], CanonicalEntityBinding, tuple[Any, ...], list[datetime]]] = []
    for issuer in contract["issuers"]:
        ticker = str(issuer["ticker"])
        binding = _issuer_binding(issuer)
        if binding is None:
            excluded.append(
                {"ticker": ticker, "cik": issuer["cik"], "reason": EXCLUSION_IDENTITY_NOT_FROZEN}
            )
            continue
        cik = str(issuer["cik"])
        try:
            retained = read_retained_fif_packages(archive_root, cik=cik)
        except FifMemberCaptureError as exc:
            if exc.code == "golden_input_refused":
                # Golden contamination is a run-level integrity refusal, never
                # a per-issuer exclusion.
                _fail(str(exc), code="golden_input_refused")
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
            excluded.append(
                {"ticker": ticker, "cik": cik, "reason": EXCLUSION_NO_RETAINED_PACKAGE}
            )
            continue
        admitted = []
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
            admitted.append(admitted_package)
            capture_clocks.append(
                _require_clock(package.capture_recorded_at, "capture_recorded_at")
            )
        if not admitted:
            excluded.append(
                {
                    "ticker": ticker,
                    "cik": cik,
                    "reason": refusals[0] if refusals else EXCLUSION_NO_RETAINED_PACKAGE,
                    "detail": "; ".join(sorted(set(refusals))),
                }
            )
            continue
        staged.append((issuer, binding, tuple(admitted), capture_clocks))

    # FUTURE-CLOCK REFUSAL (seat amendment (a)): every issuer's CLOCK RULE is
    # computed BEFORE any store exists or writes — a later admitted_at than
    # the run's recorded-at refuses the whole run, never clamps a clock, and
    # never mints a future-dated generation.
    for issuer, _binding, _packages, capture_clocks in staged:
        computed = max([*capture_clocks, *_rule_clocks(), *registry_clocks])
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
    for issuer, binding, admitted_packages, capture_clocks in staged:
        row = _publish_one_issuer(
            store=store,
            issuer=issuer,
            binding=binding,
            admitted_packages=admitted_packages,
            capture_clocks=capture_clocks,
            registry_payload=registry_payload,
            registry_clocks=registry_clocks,
            repo_root=Path(args.repo_root),
        )
        published.append(row)

    report = {
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
        "published": published,
        "excluded": excluded,
    }
    if args.report_path:
        report_path = Path(args.report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2), flush=True)
    verify_report(report, store)
    return 0


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------


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
            or reason.startswith("admission_refused:")
            or reason.startswith("member_capture_failed:")
        )
        if not lawful:
            _fail(f"exclusion reason is outside the closed vocabulary: {reason}", code="verify_failed")
    for row in published:
        generation_id = str(row.get("generation_id") or "")
        entity_id = str(row.get("entity_id") or "")
        if not generation_id or not entity_id:
            _fail("published row is missing its generation identity", code="verify_failed")
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
    print(
        json.dumps(
            {"schema": report.get("schema"), "verified": True, "issuers": len(seen)},
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
    targets.add_argument("--max-tickers", type=int, default=15)

    capture = subparsers.add_parser("capture-members", help="D1 member capture over retained primaries")
    capture.add_argument("--coverage-file", type=Path, required=True)
    capture.add_argument("--raw-root", type=Path, required=True)
    capture.add_argument("--archive-root", type=Path, required=True)
    capture.add_argument("--recorded-at", required=True, help="Explicit UTC capture clock")
    capture.add_argument("--user-agent", default=None, help="SEC user agent override (tests inject one)")
    capture.add_argument("--min-interval-seconds", type=float, default=0.12)
    capture.add_argument("--max-document-bytes", type=int, default=32 * 1024 * 1024)
    capture.add_argument("--run-budget-bytes", type=int, default=256 * 1024 * 1024)

    publish = subparsers.add_parser("publish", help="Publish production generations (hard gate)")
    publish.add_argument("--coverage-file", type=Path, required=True)
    publish.add_argument("--raw-root", type=Path, required=True)
    publish.add_argument("--archive-root", type=Path, required=True)
    publish.add_argument("--recorded-at", required=True, help="Explicit UTC run clock")
    publish.add_argument("--store-dir", type=Path, default=None, help="Explicit local directory store")
    publish.add_argument("--repo-root", type=Path, default=_ROOT)
    publish.add_argument("--report-path", type=Path, default=None)

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
        if args.command == "publish":
            return _run_publish(args)
        if args.command == "verify":
            return _run_verify(args)
        parser.error(f"unknown command: {args.command}")
        return 2
    except PublisherError as exc:
        traceback.print_exc(file=sys.stderr)
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
            code = (
                exc.code
                if exc.code == "golden_input_refused"
                else f"member_capture_failed-{exc.code}"
            )
        _error_annotation(f"fif_production_datasets-{code}", f"{type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
