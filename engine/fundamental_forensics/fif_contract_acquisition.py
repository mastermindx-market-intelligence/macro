"""C0-c E1: contract-keyed primary acquisition (fif_contract_acquisition).

Every D0 contract accession of every contract form (10-K, 10-Q, 8-K) gets a
primary plus a manifest acquired keyed by ACCESSION, never by a latest-N
selector. Orchestration is over incumbent functions ONLY:

* the row is located in ``filings.recent`` of the SAME verified latest.json
  the capture already reads (``read_verified_submissions``), otherwise in the
  unique covering ``filings.files[]`` page (E5 rule 2, ``select_submissions_page``);
* a page is retained ONLY by the incumbent
  ``SecForensicsCollector.fetch_historical_submissions_file`` through
  ``retain_submissions_page`` (E5-b reuse-first with MAJOR-1 qualification: a
  retained page is reused only while it still contains the accession or its
  derived range equals the current files[] entry's — SEC re-pages these shards
  newest-first, and a stale page is refetched through the incumbent path, not
  reused forever; no archive-root page namespace, no new receipt schema,
  ``latest.json`` never moves);
* manifests come from the incumbent ``build_filing_manifests`` — the recent
  payload as is, or the page wrapped as ``{cik, name, filings: {recent: <page>}}``
  (pages share recent's columnar shape, proven on the census page);
* the primary is fetched by the archive collector's
  ``fetch_primary_document`` and retained by ``retain_filing_manifest`` into
  the SAME archive root, after the reuse checks (an already-retained manifest,
  then ``find_reusable_primary_retrieval`` — a hit costs zero requests).

This module writes no incumbent namespace other than through the incumbent
writers, mints no wall clock (every clock is the caller's injected
``recorded_at``), and holds no ticker or CIK literal. Per-accession failures
are TYPED rows in the returned report (the run still completes); the only
run-abort is the ERRATA-5 E5-e integrity refusal ``submissions_page_receipt_
mismatch`` raised by the shared page helper. Page bytes and primary bytes both
count against the caller's budget (DEFAULT_RUN_BUDGET_BYTES, imported from
``fif_member_capture`` — no second number is minted here): every charged page
SUBTRACTS from the remaining budget, and the primary fetch is streamed-capped
at min(remaining budget, the collector's max_document_bytes ceiling) so an
over-budget primary is refused BEFORE anything is persisted (no orphan object)
— the post-fetch length check stays only as defence.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from collectors.fundamental_forensics_acquisition import (
    DEFAULT_MAX_SUBMISSIONS_BYTES,
    read_verified_submissions,
)
from collectors.sec_document_spine import (
    ArchiveResponseTooLarge,
    DEFAULT_MAX_DOCUMENT_BYTES,
    find_reusable_primary_retrieval,
    retain_filing_manifest,
    with_document_retrievals,
)

from .fif_member_capture import (
    DEFAULT_RUN_BUDGET_BYTES,
    FifMemberCaptureError,
    RETAINED_PACKAGE_INTEGRITY_CODES,
    find_retained_primary_manifest,
    retain_submissions_page,
    select_submissions_page,
    submissions_page_entry,
)
from .sec_document_spine import build_filing_manifests, canonical_cik

CONTRACT_ACQUISITION_RUN_SCHEMA = "fundamental_forensics.fif_contract_acquisition_run/v1"

# E1-d: the typed per-accession failure vocabulary. Shared with ERRATA-5
# (submissions_page_* / submissions_row_mismatch / accession_not_in_submissions
# reuse the member-capture module's codes) plus the two E1 additions and the
# budget refusal.
CONTRACT_ACQUISITION_FAILURE_CODES = frozenset(
    {
        "submissions_unavailable",
        "accession_not_in_submissions",
        "submissions_page_not_found",
        "submissions_page_ambiguous",
        "submissions_row_mismatch",
        "submissions_page_oversize",
        "primary_fetch_failed",
        "primary_oversize",
        "run_budget_exceeded",
    }
)

GOOD_OUTCOMES = frozenset({"retained_reused", "primary_reused", "primary_retained"})


class FifContractAcquisitionError(RuntimeError):
    """A typed per-accession E1 acquisition refusal.

    Carries exactly the E1-d codes that are NOT member-capture codes
    (``primary_fetch_failed``, ``primary_oversize``) plus the acquire-side
    budget refusal; the shared submissions-page codes arrive as
    ``FifMemberCaptureError`` from the page helpers and are handled the same
    way. Never carries a code outside CONTRACT_ACQUISITION_FAILURE_CODES.
    """

    def __init__(self, message: str, *, code: str) -> None:
        if code not in CONTRACT_ACQUISITION_FAILURE_CODES:
            raise ValueError(f"unknown contract acquisition refusal code: {code}")
        super().__init__(message)
        self.code = code


def assert_shared_pacer(
    *, submissions_collector: Any, archive_collector: Any, pacer: Any
) -> None:
    """A20 / E1-c (C): both collectors must ride the ONE shared SecRequestPacer."""
    for name, collector in (
        ("submissions", submissions_collector),
        ("archive", archive_collector),
    ):
        if getattr(collector, "_pacer", pacer) is not pacer:
            raise FifMemberCaptureError(
                f"contract acquisition requires the {name} collector to ride "
                "the shared SecRequestPacer",
                code="private_pacer",
            )


def _primary_byte_length(manifest: Mapping[str, Any]) -> int:
    for item in manifest.get("documents") or []:
        if isinstance(item, Mapping) and item.get("role") == "primary":
            length = item.get("byte_length")
            if isinstance(length, int) and not isinstance(length, bool):
                return length
    return 0


def _has_stored_primary(manifest: Mapping[str, Any]) -> bool:
    return any(
        isinstance(item, Mapping)
        and item.get("role") == "primary"
        and item.get("availability") == "stored"
        for item in manifest.get("documents") or []
    )


def _row_at_index(columns: Mapping[str, Any], index: int) -> dict[str, Any]:
    return {
        str(field): values[index]
        for field, values in columns.items()
        if isinstance(values, list) and index < len(values)
    }


def _check_row_against_contract(
    row: Mapping[str, Any], *, form: str, filing_date: str, accession: str
) -> None:
    """The shared row check (E1-d vocabulary, R8's twin): the located row's
    form and filingDate must equal the contract row's. A disagreement is
    ``submissions_row_mismatch`` — on BOTH the recent and the page path."""
    row_form = str(row.get("form") or "").strip().upper()
    row_date = str(row.get("filingDate") or "").strip()
    if row_form != str(form).strip().upper() or row_date != str(filing_date).strip():
        raise FifMemberCaptureError(
            f"submissions row disagrees with the contract row for {accession}: "
            f"form {row_form!r} vs {form!r}, filingDate {row_date!r} vs "
            f"{filing_date!r}",
            code="submissions_row_mismatch",
        )


def _decode_page(page_bytes: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(page_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FifMemberCaptureError(
            f"submissions page is not UTF-8 JSON: {exc}",
            code="submissions_page_not_found",
        ) from exc
    if not isinstance(payload, dict):
        raise FifMemberCaptureError(
            "submissions page is not a JSON object", code="submissions_page_not_found"
        )
    return payload


def acquire_contract_primaries(
    *,
    raw_root: Path,
    archive_root: Path,
    issuers: list[Mapping[str, Any]],
    submissions_collector: Any,
    archive_collector: Any,
    pacer: Any,
    recorded_at: str,
    run_budget_bytes: int = DEFAULT_RUN_BUDGET_BYTES,
    page_ceiling_bytes: int | None = None,
) -> dict[str, Any]:
    """Acquire every contract accession's primary + manifest, keyed by accession.

    Per-accession typed failures land in the report (the run completes with
    status ``partial``); only a retained-page integrity refusal aborts the
    run. The report carries per-issuer rows, charged/reused byte accounting,
    and the number of SEC requests this run issued. Pages are cached per name
    for the run; a cached REUSED page that lacks an accession gets ONE more
    qualification-scoped retain (MAJOR-1), so at most ONE fetch happens per
    page name per run.
    """
    ceiling = (
        DEFAULT_MAX_SUBMISSIONS_BYTES if page_ceiling_bytes is None else int(page_ceiling_bytes)
    )
    assert_shared_pacer(
        submissions_collector=submissions_collector,
        archive_collector=archive_collector,
        pacer=pacer,
    )
    budget = int(run_budget_bytes)
    report: dict[str, Any] = {
        "schema": CONTRACT_ACQUISITION_RUN_SCHEMA,
        "recorded_at": str(recorded_at),
        "run_budget_bytes": budget,
        "bytes_charged": 0,
        "bytes_reused": 0,
        "requests_issued": 0,
        "issuers": [],
    }
    for issuer in issuers:
        cik = canonical_cik(issuer["cik"])
        ticker = str(issuer.get("ticker") or "")
        issuer_row: dict[str, Any] = {"cik": cik, "ticker": ticker, "accessions": []}
        try:
            submissions, _receipt = read_verified_submissions(Path(raw_root), cik)
        except Exception as exc:  # noqa: BLE001 - typed per-issuer, never fatal
            for entry in issuer.get("accessions") or []:
                issuer_row["accessions"].append(
                    {
                        "accession": str(entry["accession"]),
                        "outcome": "acquire_failed:submissions_unavailable",
                        "error": str(exc),
                        "charged_bytes": 0,
                        "reused": False,
                    }
                )
            report["issuers"].append(issuer_row)
            continue
        recent = (submissions.get("filings") or {}).get("recent") or {}
        entity_name = str(submissions.get("name") or submissions.get("entityName") or "")
        recent_manifests_built = False
        manifests_by_accession: dict[str, Mapping[str, Any]] = {}
        # MAJOR-1 (4): the in-run page cache remembers whether each cached
        # page was FETCHED this run. At most ONE fetch per page name per run:
        # a REUSED cached page that lacks an accession gets one more
        # qualification-scoped retain (reuse a qualifying page or fetch once),
        # while a page FETCHED this run already reflects the live shard.
        page_payloads: dict[str, dict[str, Any]] = {}

        def _retain_page(page_name: str, page_entry: Mapping[str, Any], accession: str) -> dict[str, Any]:
            nonlocal budget
            page_bytes, charged, reused = retain_submissions_page(
                raw_root=Path(raw_root),
                cik=cik,
                page_name=page_name,
                submissions_collector=submissions_collector,
                retrieved_at=str(recorded_at),
                budget_remaining=budget,
                page_ceiling_bytes=ceiling,
                accession=accession,
                page_entry=page_entry,
            )
            report["bytes_charged"] += charged
            # MINOR-4 (a): page bytes leave the run budget, not just the report.
            budget -= charged
            if reused:
                report["bytes_reused"] += len(page_bytes)
            else:
                report["requests_issued"] += 1
            return {
                "payload": {
                    "cik": int(cik),
                    "name": entity_name,
                    "filings": {"recent": _decode_page(page_bytes)},
                },
                "fetched": not reused,
            }

        for accession_entry in issuer.get("accessions") or []:
            accession = str(accession_entry["accession"])
            form = str(accession_entry.get("form") or "")
            filing_date = str(accession_entry.get("filing_date") or "")
            row_out: dict[str, Any] = {
                "accession": accession,
                "outcome": None,
                "charged_bytes": 0,
                "reused": False,
            }
            try:
                # Reuse check 1 (E1-b): an already-retained stored primary
                # costs zero requests and zero budget.
                retained = find_retained_primary_manifest(
                    Path(archive_root), cik=cik, accession=accession
                )
                if retained is not None:
                    row_out.update(outcome="retained_reused", reused=True)
                    report["bytes_reused"] += _primary_byte_length(retained)
                    issuer_row["accessions"].append(row_out)
                    continue
                row_index: int | None = None
                if isinstance(recent.get("accessionNumber"), list):
                    if accession in recent["accessionNumber"]:
                        row_index = recent["accessionNumber"].index(accession)
                if row_index is not None:
                    _check_row_against_contract(
                        _row_at_index(recent, row_index),
                        form=form,
                        filing_date=filing_date,
                        accession=accession,
                    )
                    if not recent_manifests_built:
                        manifests_by_accession.update(
                            {
                                m["filing"]["accession"]: m
                                for m in build_filing_manifests(
                                    submissions,
                                    cik=cik,
                                    ticker=ticker or None,
                                    recorded_at=str(recorded_at),
                                )
                            }
                        )
                        recent_manifests_built = True
                else:
                    # E5 rule 2: the unique covering page, selected from the
                    # SAME verified latest.json (E5-d).
                    page_name = select_submissions_page(
                        submissions, filing_date=filing_date
                    )
                    page_entry = submissions_page_entry(submissions, page_name)
                    if page_name not in page_payloads:
                        page_payloads[page_name] = _retain_page(
                            page_name, page_entry, accession
                        )
                    cached = page_payloads[page_name]
                    cached_accessions = (
                        cached["payload"]["filings"]["recent"].get("accessionNumber")
                        or []
                    )
                    if accession not in cached_accessions and not cached["fetched"]:
                        # MAJOR-1 (4): a REUSED cached page may be stale (SEC
                        # re-paged the shard under the same URL). One more
                        # qualification-scoped retain for THIS accession: it
                        # reuses a qualifying retained page or fetches once.
                        page_payloads[page_name] = _retain_page(
                            page_name, page_entry, accession
                        )
                        cached = page_payloads[page_name]
                    page_recent = cached["payload"]["filings"]["recent"]
                    page_accessions = page_recent.get("accessionNumber") or []
                    if accession not in page_accessions:
                        # Only a page FETCHED this run — or a reused page that
                        # still lacks the accession after the second retain —
                        # reaches here: the genuine typed refusal.
                        raise FifMemberCaptureError(
                            f"accession is absent from its covering submissions "
                            f"page: {accession}",
                            code="accession_not_in_submissions",
                        )
                    _check_row_against_contract(
                        _row_at_index(page_recent, page_accessions.index(accession)),
                        form=form,
                        filing_date=filing_date,
                        accession=accession,
                    )
                    if accession not in manifests_by_accession:
                        manifests_by_accession.update(
                            {
                                m["filing"]["accession"]: m
                                for m in build_filing_manifests(
                                    cached["payload"],
                                    cik=cik,
                                    ticker=ticker or None,
                                    recorded_at=str(recorded_at),
                                )
                            }
                        )
                manifest = manifests_by_accession.get(accession)
                if manifest is None:
                    raise FifMemberCaptureError(
                        "accession is absent from the located submissions rows: "
                        f"{accession}",
                        code="accession_not_in_submissions",
                    )
                # Retain the DECLARED manifest before the network leg (the
                # incumbent discipline: the durable receipt proves which
                # accession was admitted at this clock even if the fetch fails).
                retain_filing_manifest(Path(archive_root), manifest)
                # Reuse check 2 (E1-b): a prior verified primary receipt is
                # attached verbatim — zero requests, zero budget.
                reused_receipt = find_reusable_primary_retrieval(
                    Path(archive_root), manifest
                )
                if reused_receipt is not None:
                    materialized = with_document_retrievals(
                        manifest, {str(reused_receipt["document_id"]): reused_receipt}
                    )
                    retain_filing_manifest(Path(archive_root), materialized)
                    row_out.update(outcome="primary_reused", reused=True)
                    report["bytes_reused"] += _primary_byte_length(materialized)
                    issuer_row["accessions"].append(row_out)
                    continue
                if budget < 1:
                    raise FifContractAcquisitionError(
                        "run byte budget exhausted before primary fetch",
                        code="run_budget_exceeded",
                    )
                # MINOR-4 (b): cap the streamed primary fetch at min(budget,
                # document ceiling) so an over-budget primary is refused by
                # the incumbent streamed cap BEFORE anything is persisted —
                # no orphan object. A budget-bound refusal (cap below the
                # document ceiling) maps to run_budget_exceeded; a
                # ceiling-bound one to primary_oversize.
                document_ceiling = getattr(
                    archive_collector, "max_document_bytes", None
                )
                if (
                    isinstance(document_ceiling, bool)
                    or not isinstance(document_ceiling, int)
                    or document_ceiling < 1
                ):
                    document_ceiling = DEFAULT_MAX_DOCUMENT_BYTES
                cap = min(budget, document_ceiling)
                try:
                    materialized = archive_collector.fetch_primary_document(
                        manifest,
                        retrieved_at=str(recorded_at),
                        max_document_bytes=cap,
                    )
                except ArchiveResponseTooLarge as exc:
                    if cap < document_ceiling:
                        raise FifContractAcquisitionError(
                            f"primary fetch exceeds the remaining run byte "
                            f"budget: {accession} (cap {cap} < ceiling "
                            f"{document_ceiling})",
                            code="run_budget_exceeded",
                        ) from exc
                    raise FifContractAcquisitionError(
                        f"primary document exceeds the byte ceiling: {accession} "
                        f"({exc})",
                        code="primary_oversize",
                    ) from exc
                except Exception as exc:  # noqa: BLE001 - transport failures are typed
                    raise FifContractAcquisitionError(
                        f"primary fetch failed for {accession}: {exc}",
                        code="primary_fetch_failed",
                    ) from exc
                if not _has_stored_primary(materialized):
                    raise FifContractAcquisitionError(
                        f"primary fetch did not retain a stored primary: {accession}",
                        code="primary_fetch_failed",
                    )
                length = _primary_byte_length(materialized)
                if length > budget:
                    raise FifContractAcquisitionError(
                        "primary fetch exceeded the remaining run byte budget",
                        code="run_budget_exceeded",
                    )
                budget -= length
                report["bytes_charged"] += length
                report["requests_issued"] += 1
                retain_filing_manifest(Path(archive_root), materialized)
                row_out.update(outcome="primary_retained", charged_bytes=length)
            except (FifMemberCaptureError, FifContractAcquisitionError) as exc:
                if (
                    isinstance(exc, FifMemberCaptureError)
                    and exc.code in RETAINED_PACKAGE_INTEGRITY_CODES
                ):
                    # E5-e: run-level integrity refusal — never a per-accession
                    # row, never a refetch-over. Crash class.
                    raise
                row_out.update(outcome=f"acquire_failed:{exc.code}", error=str(exc))
            issuer_row["accessions"].append(row_out)
        report["issuers"].append(issuer_row)
    outcomes = [
        row["outcome"] for issuer in report["issuers"] for row in issuer["accessions"]
    ]
    report["status"] = (
        "complete"
        if outcomes and all(outcome in GOOD_OUTCOMES for outcome in outcomes)
        else "partial"
    )
    report["run_budget_remaining"] = budget
    return report


__all__ = [
    "CONTRACT_ACQUISITION_FAILURE_CODES",
    "CONTRACT_ACQUISITION_RUN_SCHEMA",
    "FifContractAcquisitionError",
    "GOOD_OUTCOMES",
    "acquire_contract_primaries",
    "assert_shared_pacer",
]
