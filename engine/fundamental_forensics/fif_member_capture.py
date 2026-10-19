"""Issuer-generic nine-component filing-package capture from retained lane bytes (FIF C0-b).

For each contract accession whose primary document the wave-2 lane already
retained, this module fetches the archive ``index.json`` plus the five XBRL
role members by primary-stem suffix through the EXISTING
``SecFilingArchiveCollector.fetch_document`` under the ONE shared
``SecRequestPacer`` (A20 — a caller-supplied collector pacing privately is a
typed refusal), mints the acceptance-witness slice from the ALREADY retained
Submissions bytes in the raw root, and writes one package subtree::

    <archive_root>/fif-packages/<cik>/<accession>/
        package_manifest.json            # this module's schema, never golden
        index.json                       # the fetched archive index bytes
        sec_submissions_witness.json     # the minted witness slice
        members/<name>                   # the six retained role members

``fif-packages/`` lives under ``--archive-root`` and the observation-root
outside-law (``fundamental_forensics_acquisition``) is untouched. ERRATA E1
corrected the original claim that the source sync never syncs this prefix:
``source_sync`` rglobs the WHOLE archive root, so packages ARE snapshotted from
night 2. Reuse of a restored package is therefore VERIFY-BEFORE-REUSE and FAILS
CLOSED — the digests inside the package manifest are the anchor, and an
integrity-code refusal (``RETAINED_PACKAGE_INTEGRITY_CODES``) never re-captures
with a new clock and never publishes that night. The wave-2 receipt
schema, the exactly-two comparables law, and every already-retained object are
never edited here.

This module mints no wall clock (every clock is caller-supplied) and performs
SEC I/O only through the injected collector, so tests drive it entirely with
fakes. No ticker or CIK literal appears here: identity comes from the frozen
coverage contract and the retained manifests.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import secrets
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from xml.etree import ElementTree as ET

from collectors.edgar_forensics import historical_submissions_url
from collectors.fundamental_forensics_acquisition import read_verified_submissions
from collectors.sec_document_spine import read_archive_document
from .filing_package import _MEMBER_STATES
from .sec_document_spine import (
    HARD_MAX_ARCHIVE_DOCUMENT_BYTES,
    HARD_MAX_ARCHIVE_INDEX_MEMBERS,
    archive_document_url,
    archive_index_url,
    canonical_cik,
)

FIF_MEMBER_CAPTURE_PACKAGE_SCHEMA = "fundamental_forensics.fif_member_capture_package/v1"
# The committed golden fixture manifest schemas are a different corpus. Since
# D9 the schema check is an ALLOW-list on FIF_MEMBER_CAPTURE_PACKAGE_SCHEMA
# above, so this set is documentation of that foreign corpus (kept for the
# docstring's vocabulary), not the enforcement: production generations are
# built from lane-retained bytes, never fixture trees.
GOLDEN_PACKAGE_SCHEMAS = frozenset(
    {
        "fundamental_forensics.golden_filing_package/v1",
    }
)
PACKAGE_PREFIX = "fif-packages"
WITNESS_NAME = "sec_submissions_witness.json"
INDEX_NAME = "index.json"
MANIFEST_NAME = "package_manifest.json"
MEMBERS_DIR = "members"
# Finished packages are assembled in a staging prefix OUTSIDE every
# <cik>/<accession> reader path, then renamed into place as a directory —
# readers never observe a half-written package, and a leftover staging dir
# (a killed run) is never read back as one.
STAGING_DIR_NAME = ".staging"

# ERRATA E1: the codes that make a RETAINED package untrustworthy. A package
# whose reuse verification raises one of these must FAIL CLOSED — it is never
# silently re-captured with tonight's clock (that would re-mint the capture
# clock the CLOCK RULE and generation id derive from), and publish refuses the
# WHOLE run rather than excluding the issuer. Defined once here; the producer
# imports it for its run-level refusal.
RETAINED_PACKAGE_INTEGRITY_CODES = frozenset(
    {
        "package_bytes_mismatch",
        "package_manifest_malformed",
        "inventory_mismatch",
        "golden_input_refused",
        # C0-c E5-e (seat-accepted): retained page bytes that fail their
        # receipt verification are the same class as package_bytes_mismatch —
        # run-level integrity, nonzero exit, never a refetch-over.
        "submissions_page_receipt_mismatch",
    }
)

# C0-c ERRATA-5: the per-accession submissions-page vocabulary, shared with
# E1's contract acquisition (fif_contract_acquisition.py). ``accession_not_in_
# submissions`` already existed. A page that cannot be located, cannot be
# disambiguated, disagrees with the contract row, or breaks the E5-a ceiling
# is a per-accession refusal — never a run abort.
PAGE_REFUSAL_CODES = frozenset(
    {
        "submissions_page_not_found",
        "submissions_page_ambiguous",
        "submissions_row_mismatch",
        "submissions_page_oversize",
        # raisable vocabulary for the run-level integrity refusal (E5-e: the
        # seat ruling moved it INTO RETAINED_PACKAGE_INTEGRITY_CODES; it stays
        # here too because FifMemberCaptureError validates against this set).
        "submissions_page_receipt_mismatch",
        # C0-c ERRATA-4 R1: a contract form outside the member policy.
        "form_not_in_member_policy",
    }
)


# Census byte ceilings: 32 MiB per member, 20k members per archive index, and
# a per-run budget across every fetched member document.
MAX_MEMBER_BYTES = HARD_MAX_ARCHIVE_DOCUMENT_BYTES
MAX_INDEX_MEMBERS = HARD_MAX_ARCHIVE_INDEX_MEMBERS
DEFAULT_RUN_BUDGET_BYTES = 256 * 1024 * 1024

# Primary stem -> the five XBRL role members fetched by suffix.
MEMBER_SUFFIX_ROLES: tuple[tuple[str, str], ...] = (
    (".xsd", "schema"),
    ("_pre.xml", "presentation"),
    ("_cal.xml", "calculation"),
    ("_def.xml", "definition"),
    ("_lab.xml", "label"),
)

_REFUSAL_CODES = frozenset(
    {
        "golden_input_refused",
        "private_pacer",
        "no_retained_primary",
        "submissions_unavailable",
        "accession_not_in_submissions",
        "identity_mismatch",
        "member_missing_from_index",
        "member_fetch_failed",
        "malformed_member",
        "member_oversize",
        "member_count_exceeded",
        "run_budget_exceeded",
        "statement_roles_mint_failed",
        "package_manifest_malformed",
        "package_bytes_mismatch",
        "inventory_mismatch",
        "staging_device_mismatch",
        # C0-c ERRATA-5 / E1-d: the shared submissions-page vocabulary.
        "submissions_page_not_found",
        "submissions_page_ambiguous",
        "submissions_row_mismatch",
        "submissions_page_oversize",
        # raisable vocabulary for the run-level integrity refusal (E5-e: the
        # seat ruling moved it INTO RETAINED_PACKAGE_INTEGRITY_CODES; it stays
        # here too because FifMemberCaptureError validates against this set).
        "submissions_page_receipt_mismatch",
        # C0-c ERRATA-4 R1: a contract form outside the member policy.
        "form_not_in_member_policy",
    }
)

# C0-c ERRATA-4 R1: the member set is keyed by the CONTRACT form — it is
# NEVER inferred from file content. 10-K/10-Q require all five members
# (unchanged); 8-K requires schema, presentation and label, with calculation
# and definition OPTIONAL (R2: absent only when the accession's own archive
# index does not name the member).
MEMBER_POLICY_BY_FORM: dict[str, dict[str, tuple[tuple[str, str], ...]]] = {
    "10-K": {"required": MEMBER_SUFFIX_ROLES, "optional": ()},
    "10-Q": {"required": MEMBER_SUFFIX_ROLES, "optional": ()},
    "8-K": {
        "required": (
            (".xsd", "schema"),
            ("_pre.xml", "presentation"),
            ("_lab.xml", "label"),
        ),
        "optional": (
            ("_cal.xml", "calculation"),
            ("_def.xml", "definition"),
        ),
    },
}
ABSENT_MEMBER_REASON = "absent_in_archive_index"


def member_policy_for(form: str) -> dict[str, tuple[tuple[str, str], ...]]:
    """The form-keyed member policy, or the typed R1 refusal."""
    policy = MEMBER_POLICY_BY_FORM.get(str(form or "").strip().upper())
    if policy is None:
        raise FifMemberCaptureError(
            f"contract form is not in the member policy: {form!r}",
            code="form_not_in_member_policy",
        )
    return policy

_STATEMENT_DEFINITION_SEPARATOR = " - Statement - "
_TRAILING_PARENTHETICAL = re.compile(r"\s*\([^()]*\)\s*$")


class FifMemberCaptureError(RuntimeError):
    """A typed member-capture or retained-package refusal.

    The closed ``code`` vocabulary is the suffix the producer reports as
    ``member_capture_failed:<code>``; it never falls back to silence.
    """

    def __init__(self, message: str, *, code: str) -> None:
        if code not in _REFUSAL_CODES:
            raise ValueError(f"unknown member capture refusal code: {code}")
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class RetainedFifPackage:
    """One digest-verified package subtree read back from the capture prefix."""

    cik: str
    accession: str
    manifest: Mapping[str, Any]
    index_bytes: bytes
    members: Mapping[str, bytes]
    witness_bytes: bytes
    package_dir: Path

    @property
    def capture_recorded_at(self) -> str:
        return str(self.manifest["capture_recorded_at"])


def refuse_repository_fixture_inputs(*roots: Path) -> None:
    """Refuse any input root that resolves inside a repository fixture tree."""
    for root in roots:
        resolved = Path(root).resolve()
        for part_index, _part in enumerate(resolved.parts):
            joined = "/".join(resolved.parts[part_index : part_index + 2])
            if joined == "tests/fixtures":
                raise FifMemberCaptureError(
                    f"member capture input root is a repository fixture tree: {root}",
                    code="golden_input_refused",
                )


def package_dir_for(archive_root: Path, cik: str, accession: str) -> Path:
    return Path(archive_root) / PACKAGE_PREFIX / cik / accession


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _utc_text(value: str | datetime, *, field: str) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise FifMemberCaptureError(
                f"{field} requires an aware UTC clock", code="identity_mismatch"
            )
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise FifMemberCaptureError(
            f"{field} requires an aware ISO-8601 UTC clock", code="identity_mismatch"
        ) from exc
    if parsed.tzinfo is None:
        raise FifMemberCaptureError(
            f"{field} requires an aware ISO-8601 UTC clock", code="identity_mismatch"
        )
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Retained-manifest discovery (read-only over the wave-2 archive vocabulary)
# ---------------------------------------------------------------------------


def _manifest_retention_order(manifest: Mapping[str, Any]) -> tuple[str, str]:
    clocks = manifest.get("clocks") or {}
    return (
        str((clocks.get("recorded_at") if isinstance(clocks, Mapping) else None) or ""),
        str(manifest.get("manifest_id") or ""),
    )


def find_retained_primary_manifest(
    archive_root: Path, *, cik: str, accession: str
) -> dict[str, Any] | None:
    """Earliest retained wave-2 manifest whose primary document is stored.

    Read-only over ``archive_root/manifests/<cik>/<accession>/``; the wave-2
    receipt schema and every retained object stay untouched.
    """
    from collectors.sec_document_spine import stored_manifest_content_index

    try:
        index = stored_manifest_content_index(Path(archive_root), cik=cik, accession=accession)
    except Exception as exc:  # noqa: BLE001 - a hostile store is a typed miss, never a crash
        raise FifMemberCaptureError(
            f"retained manifest store is unreadable for accession {accession}: {exc}",
            code="package_manifest_malformed",
        ) from exc
    candidates = [
        manifest
        for manifest in index.values()
        if any(
            isinstance(item, Mapping)
            and item.get("role") == "primary"
            and item.get("availability") == "stored"
            for item in (manifest.get("documents") or [])
        )
    ]
    if not candidates:
        return None
    return sorted(candidates, key=_manifest_retention_order)[0]


def _primary_name_of(manifest: Mapping[str, Any]) -> str:
    for item in manifest.get("documents") or []:
        if isinstance(item, Mapping) and item.get("role") == "primary":
            name = item.get("document_name")
            if isinstance(name, str) and name:
                return name
    raise FifMemberCaptureError(
        "retained filing manifest has no primary document", code="no_retained_primary"
    )


# ---------------------------------------------------------------------------
# Witness mint (from ALREADY retained Submissions bytes; no second fetch)
# ---------------------------------------------------------------------------


def mint_acceptance_witness(
    *,
    raw_root: Path,
    cik: str,
    accession: str,
    primary_document: str,
    filing_date: str = "",
    submissions_collector: Any = None,
    retrieved_at: str = "",
    budget_remaining: int = DEFAULT_RUN_BUDGET_BYTES,
    page_ceiling_bytes: int | None = None,
) -> tuple[bytes, dict[str, str], dict[str, Any] | None]:
    """Bind the Submissions-row slice for one accession to exact manifest fields.

    ERRATA-5: if the accession is in ``filings.recent`` the binding is
    byte-unchanged (rule 1). Otherwise the witness binds from the UNIQUE
    covering ``filings.files[]`` page of the SAME verified latest.json (rules
    2-5, E5-c/E5-d): the page is reuse-or-fetched under the run budget
    (``retain_submissions_page``), the accession must appear in it, and every
    bound field carries the same checks as the recent path. Only the
    ``source_url``/``source_path`` VALUES differ (``filings.files[<name>]
    [accessionNumber=<acc>]`` and the page URL); the JSON keys and sort order
    are identical (E5-c). MAJOR-1: reuse is qualification-aware — a verified
    retained page is reused only while it still contains the accession or its
    derived range equals the current files[] entry's; a stale page (SEC
    re-paged the shard) is refetched through the incumbent path.

    Returns ``(witness_bytes, bound_fields, page_info)`` where ``page_info``
    is None on the recent path and ``{"name", "charged_bytes", "reused"}`` on
    the page path (the caller charges the page bytes to the run budget).
    """
    from collectors.fundamental_forensics_acquisition import (
        DEFAULT_MAX_SUBMISSIONS_BYTES,
    )

    try:
        submissions, receipt = read_verified_submissions(Path(raw_root), cik)
    except Exception as exc:  # noqa: BLE001 - AcquisitionError and friends are typed here
        raise FifMemberCaptureError(
            f"retained Submissions bytes are unavailable for CIK {cik}: {exc}",
            code="submissions_unavailable",
        ) from exc
    recent = (submissions.get("filings") or {}).get("recent") or {}
    accessions = recent.get("accessionNumber")
    page_info: dict[str, Any] | None = None
    page_source_url = ""
    if isinstance(accessions, list) and accession in accessions:
        row_columns: Mapping[str, Any] = recent
        row_index: int = accessions.index(accession)
        source_url = str(receipt.get("url") or "")
        source_path = f"filings.recent[accessionNumber={accession}]"
    else:
        # ERRATA-5 rule 2: the unique covering page, selected from the SAME
        # verified latest.json document (E5-d — no second Submissions fetch).
        files_inventory = (submissions.get("filings") or {}).get("files") or []
        if not str(filing_date or "").strip() or not files_inventory:
            raise FifMemberCaptureError(
                f"accession is absent from the retained Submissions rows: {accession}",
                code="accession_not_in_submissions",
            )
        if submissions_collector is None:
            raise FifMemberCaptureError(
                f"accession is outside filings.recent and no submissions "
                f"collector was provided to fetch its page: {accession}",
                code="submissions_unavailable",
            )
        page_name = select_submissions_page(submissions, filing_date=filing_date)
        # MAJOR-1 (3): the page_entry from the SAME verified latest.json (E5-d)
        # rides with the accession so retain_submissions_page can qualify a
        # retained page (containment or derived-range equality) instead of
        # reusing any URL-matching bytes forever.
        page_entry = submissions_page_entry(submissions, page_name)
        page_bytes, charged, reused = retain_submissions_page(
            raw_root=Path(raw_root),
            cik=cik,
            page_name=page_name,
            submissions_collector=submissions_collector,
            retrieved_at=retrieved_at,
            budget_remaining=budget_remaining,
            page_ceiling_bytes=(
                DEFAULT_MAX_SUBMISSIONS_BYTES
                if page_ceiling_bytes is None
                else page_ceiling_bytes
            ),
            accession=accession,
            page_entry=page_entry,
        )
        try:
            page_payload = json.loads(page_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise FifMemberCaptureError(
                f"submissions page is not UTF-8 JSON: {page_name} ({exc})",
                code="submissions_unavailable",
            ) from exc
        if not isinstance(page_payload, dict):
            raise FifMemberCaptureError(
                f"submissions page is not a JSON object: {page_name}",
                code="submissions_unavailable",
            )
        page_accessions = page_payload.get("accessionNumber")
        if not isinstance(page_accessions, list) or accession not in page_accessions:
            raise FifMemberCaptureError(
                f"accession is absent from the retained Submissions rows: {accession}",
                code="accession_not_in_submissions",
            )
        row_columns = page_payload
        row_index = page_accessions.index(accession)
        page_source_url = historical_submissions_url(cik, page_name)
        source_url = page_source_url
        source_path = f"filings.files[{page_name}][accessionNumber={accession}]"
        page_info = {"name": page_name, "charged_bytes": charged, "reused": reused}

    def _cell(field: str) -> Any:
        values = row_columns.get(field)
        if isinstance(values, list) and row_index < len(values):
            return values[row_index]
        return None

    bound: dict[str, str] = {}
    for field in (
        "form",
        "filingDate",
        "reportDate",
        "acceptanceDateTime",
        "primaryDocument",
    ):
        value = _cell(field)
        if not isinstance(value, str) or not value.strip():
            raise FifMemberCaptureError(
                f"Submissions row is missing {field} for accession {accession}",
                code="accession_not_in_submissions",
            )
        bound[field] = value.strip()
    # Normalize the acceptance clock ONCE so the manifest field and the
    # witness slice carry byte-identical text (admission binds them).
    bound["acceptanceDateTime"] = _utc_text(
        bound["acceptanceDateTime"], field="acceptanceDateTime"
    )
    bound["accessionNumber"] = accession
    if bound["primaryDocument"] != primary_document:
        raise FifMemberCaptureError(
            "Submissions primaryDocument disagrees with the retained manifest",
            code="identity_mismatch",
        )
    witness = {
        "source_url": source_url,
        "source_path": source_path,
        "accessionNumber": accession,
        "form": bound["form"],
        "filingDate": bound["filingDate"],
        "reportDate": bound["reportDate"],
        "acceptanceDateTime": bound["acceptanceDateTime"],
        "primaryDocument": bound["primaryDocument"],
    }
    if not witness["source_url"]:
        raise FifMemberCaptureError(
            "retained Submissions receipt carries no source_url", code="submissions_unavailable"
        )
    payload = (json.dumps(witness, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return payload, bound, page_info


# ---------------------------------------------------------------------------
# Submissions pages (C0-c ERRATA-5: the retained-page witness/acquire path)
# ---------------------------------------------------------------------------


def select_submissions_page(
    submissions: Mapping[str, Any], *, filing_date: str
) -> str:
    """ERRATA-5 rule 2: the UNIQUE ``filings.files[]`` entry covering the date.

    Reads the SAME verified latest.json document the recent path reads (E5-d):
    there is no second Submissions fetch. Selection is by the inclusive
    [filingFrom, filingTo] range only; zero covering entries is
    ``submissions_page_not_found``, more than one is
    ``submissions_page_ambiguous``. Never guess.
    """
    files = (submissions.get("filings") or {}).get("files") or []
    date = str(filing_date or "").strip()
    covering: list[str] = []
    for entry in files:
        if not isinstance(entry, Mapping):
            continue
        name = entry.get("name")
        start = str(entry.get("filingFrom") or "")
        end = str(entry.get("filingTo") or "")
        if not isinstance(name, str) or not name:
            continue
        if not start or not end or not date:
            continue
        if start <= date <= end:
            covering.append(name)
    if not covering:
        raise FifMemberCaptureError(
            f"no filings.files[] page covers filing_date {date!r}",
            code="submissions_page_not_found",
        )
    if len(set(covering)) > 1 or len(covering) > 1:
        raise FifMemberCaptureError(
            f"filings.files[] pages overlap at filing_date {date!r}: {sorted(set(covering))}",
            code="submissions_page_ambiguous",
        )
    return covering[0]


def submissions_page_entry(
    submissions: Mapping[str, Any], page_name: str
) -> dict[str, Any]:
    """MAJOR-1 (3): the UNIQUE ``filings.files[]`` entry with this name.

    Read from the SAME verified latest.json document the recent path reads
    (E5-d — no second Submissions fetch); it is the page_entry handed to
    ``retain_submissions_page`` so retained-page qualification can compare a
    candidate's derived range against the CURRENT inventory range. Typed
    ``submissions_page_not_found`` when absent, ``submissions_page_ambiguous``
    when the inventory names the page more than once.
    """
    files = (submissions.get("filings") or {}).get("files") or []
    matches = [
        dict(entry)
        for entry in files
        if isinstance(entry, Mapping) and entry.get("name") == page_name
    ]
    if not matches:
        raise FifMemberCaptureError(
            f"filings.files[] carries no page named {page_name!r} in the "
            "verified latest.json",
            code="submissions_page_not_found",
        )
    if len(matches) > 1:
        raise FifMemberCaptureError(
            f"filings.files[] names page {page_name!r} more than once",
            code="submissions_page_ambiguous",
        )
    return matches[0]


def _read_retrieval_object(raw_root: Path, receipt: Mapping[str, Any]) -> bytes:
    """Decompress one raw-root retrieval object addressed by its receipt."""
    object_path = str(receipt.get("object_path") or "")
    digest = str(receipt.get("sha256") or "")
    length = receipt.get("bytes")
    if (
        not object_path
        or not digest
        or isinstance(length, bool)
        or not isinstance(length, int)
        or length < 0
    ):
        raise ValueError("retrieval receipt is malformed")
    source = Path(raw_root) / object_path
    try:
        with gzip.open(source, "rb") as handle:
            content = handle.read(length + 1)
    except (OSError, EOFError) as exc:
        raise ValueError(f"retrieval object is unreadable: {object_path}") from exc
    if len(content) != length or hashlib.sha256(content).hexdigest() != digest:
        raise ValueError(f"retrieval object fails its receipt digest: {object_path}")
    return content


def _decoded_page_object(content: bytes) -> Mapping[str, Any] | None:
    """The page bytes as a JSON object, or None (verified but unusable)."""
    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _page_candidate_qualifies(
    content: bytes,
    *,
    accession: str | None,
    page_entry: Mapping[str, Any] | None,
) -> bool:
    """MAJOR-1: does one VERIFIED retained page still serve this need?

    With no filters given the incumbent behaviour holds (every verified
    candidate qualifies — back-compat only; no production caller may rely on
    it). Otherwise a candidate qualifies iff (a) its bytes decode to a JSON
    object whose ``accessionNumber`` list contains ``accession``, or (b)
    ``page_entry`` carries non-empty string filingFrom/filingTo AND the
    candidate's DERIVED range [min, max] over its own non-empty string
    ``filingDate`` cells equals [filingFrom, filingTo] exactly. Undecodable or
    non-object bytes verified; they are simply unusable — never an integrity
    refusal.
    """
    if accession is None and page_entry is None:
        return True
    payload: Mapping[str, Any] | None = None
    if accession:
        payload = _decoded_page_object(content)
        if payload is not None:
            accessions = payload.get("accessionNumber")
            if isinstance(accessions, list) and accession in accessions:
                return True
    if page_entry is not None:
        start = page_entry.get("filingFrom")
        end = page_entry.get("filingTo")
        if (
            isinstance(start, str)
            and start.strip()
            and isinstance(end, str)
            and end.strip()
        ):
            if payload is None:
                payload = _decoded_page_object(content)
            if payload is not None:
                dates = payload.get("filingDate")
                cells = [
                    value
                    for value in (dates if isinstance(dates, list) else [])
                    if isinstance(value, str) and value.strip()
                ]
                if cells and (min(cells), max(cells)) == (start.strip(), end.strip()):
                    return True
    return False


def find_verified_submissions_page(
    raw_root: Path,
    *,
    cik: str,
    page_name: str,
    accession: str | None = None,
    page_entry: Mapping[str, Any] | None = None,
) -> tuple[bytes, dict[str, Any]] | None:
    """ERRATA-5 E5-b + MAJOR-1: the newest VERIFIED retained page for this
    shard that still QUALIFIES, or None.

    Scans ``<raw_root>/<cik10>/submissions/*.receipt.json`` for receipts whose
    ``url`` equals ``historical_submissions_url(cik, page_name)``; EVERY such
    receipt's object must verify (sha256 + bytes, decompressed) — any failing
    one raises the run-level integrity refusal
    ``submissions_page_receipt_mismatch`` BEFORE any qualification and before
    any fetch, never a silent refetch-over (the incumbent ``persist_response``
    would repair the object on refetch, which is exactly why this check must
    run first). Among verified receipts that QUALIFY for ``accession`` and/or
    ``page_entry`` (containment or derived-range equality — see
    ``_page_candidate_qualifies``; SEC re-pages these shards newest-first, so a
    URL-matching retained page may be stale and unusable without being
    corrupt), the NEWEST by ``retrieved_at`` wins; ties break by lexically
    smallest ``sha256``. No qualifier -> None (the caller fetches through the
    incumbent path; the stale receipt and its object are never deleted, moved
    or rewritten — ``persist_response`` is content-addressed). With neither
    filter given the incumbent behaviour holds (newest verified, period) —
    kept only for back-compat; no production caller may use it.
    """
    from collectors.edgar_forensics import historical_submissions_url

    cik10 = canonical_cik(cik)
    url = historical_submissions_url(cik10, page_name)
    directory = Path(raw_root) / cik10 / "submissions"
    try:
        receipt_paths = sorted(directory.glob("*.receipt.json"))
    except OSError:
        return None
    verified: list[tuple[str, str, bytes, dict[str, Any]]] = []
    for receipt_path in receipt_paths:
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(receipt, Mapping) or receipt.get("url") != url:
            continue
        try:
            content = _read_retrieval_object(Path(raw_root), receipt)
        except ValueError:
            raise FifMemberCaptureError(
                f"a retained submissions page fails its receipt verification "
                f"(url={url}, object={receipt.get('object_path')!r}); refusing "
                "rather than refetching over retained bytes",
                code="submissions_page_receipt_mismatch",
            ) from None
        verified.append(
            (str(receipt.get("retrieved_at") or ""), str(receipt.get("sha256") or ""), content, dict(receipt))
        )
    if not verified:
        return None
    qualifying = [
        item
        for item in verified
        if _page_candidate_qualifies(
            item[2], accession=accession, page_entry=page_entry
        )
    ]
    if not qualifying:
        return None
    newest_at = max(item[0] for item in qualifying)
    _retrieved_at, _sha, content, receipt = min(
        (item for item in qualifying if item[0] == newest_at), key=lambda item: item[1]
    )
    return content, receipt


def retain_submissions_page(
    *,
    raw_root: Path,
    cik: str,
    page_name: str,
    submissions_collector: Any,
    retrieved_at: str,
    budget_remaining: int,
    page_ceiling_bytes: int,
    accession: str,
    page_entry: Mapping[str, Any],
) -> tuple[bytes, int, bool]:
    """ERRATA-5 rule 3 + E5-a + MAJOR-1: reuse-or-fetch ONE page under the run
    budget, with qualification-aware reuse.

    Returns ``(page_bytes, charged_bytes, reused)``. A verified retained page
    that still QUALIFIES for ``accession``/``page_entry`` (containment or
    derived-range equality — see ``find_verified_submissions_page``) is reused
    with zero requests and zero budget; a verified but STALE page (SEC re-paged
    the shard under the same URL) no longer pins the issuer forever — it simply
    does not qualify. Otherwise the page is fetched ONLY through the unchanged
    incumbent ``SecForensicsCollector.fetch_historical_submissions_file``
    (``publish_latest=False``: the shard object + receipt land in the CIK
    submissions namespace and ``latest.json`` never moves) and the FRESHLY
    fetched bytes are returned and used; the stale receipt and its object are
    never deleted, moved or rewritten (``persist_response`` is
    content-addressed: new bytes -> new object + receipt). E5-a: pre-fetch the
    remaining budget must cover the page ceiling, else a typed budget refusal;
    post-fetch a verified page above the ceiling is
    ``submissions_page_oversize`` and is never used (the incumbent object is
    left in place — no deletion in an incumbent namespace). The ceiling applies
    to the same quantity the incumbent applies it to: the decoded page body
    (``DEFAULT_MAX_SUBMISSIONS_BYTES`` as ``max_response_bytes``,
    collectors/fundamental_forensics_acquisition.py:84,655).
    """
    verified = find_verified_submissions_page(
        Path(raw_root),
        cik=cik,
        page_name=page_name,
        accession=accession,
        page_entry=page_entry,
    )
    if verified is not None:
        content, _receipt = verified
        if len(content) > page_ceiling_bytes:
            raise FifMemberCaptureError(
                f"retained submissions page exceeds the page byte ceiling: "
                f"{page_name} ({len(content)} > {page_ceiling_bytes})",
                code="submissions_page_oversize",
            )
        return content, 0, True
    if budget_remaining < page_ceiling_bytes:
        raise FifMemberCaptureError(
            "remaining run budget is below the submissions page ceiling, so a "
            f"page fetch cannot be admitted: {page_name} "
            f"({budget_remaining} < {page_ceiling_bytes})",
            code="run_budget_exceeded",
        )
    try:
        receipt = submissions_collector.fetch_historical_submissions_file(
            cik,
            page_name,
            retrieved_at=retrieved_at,
            max_response_bytes=page_ceiling_bytes,
        )
    except Exception as exc:  # noqa: BLE001 - the network leg is typed, never fatal-silent
        raise FifMemberCaptureError(
            f"submissions page fetch failed: {page_name} ({exc})",
            code="submissions_page_not_found",
        ) from exc
    if isinstance(receipt, Mapping):
        receipt = dict(receipt)
    elif hasattr(receipt, "to_dict"):
        receipt = dict(receipt.to_dict())
    else:
        from dataclasses import asdict, is_dataclass

        if is_dataclass(receipt):
            receipt = dict(asdict(receipt))
    try:
        content = _read_retrieval_object(Path(raw_root), receipt)
    except ValueError as exc:
        raise FifMemberCaptureError(
            f"fetched submissions page object failed readback: {page_name} ({exc})",
            code="submissions_page_not_found",
        ) from exc
    if len(content) > page_ceiling_bytes:
        # E5-a amendment: refused and never used as a witness; the incumbent
        # object stays exactly where the incumbent fetch put it.
        raise FifMemberCaptureError(
            f"submissions page exceeds the page byte ceiling: {page_name} "
            f"({len(content)} > {page_ceiling_bytes})",
            code="submissions_page_oversize",
        )
    return content, len(content), False


# ---------------------------------------------------------------------------
# Statement-role mint (issuer-generic, from the fetched schema member)
# ---------------------------------------------------------------------------


def _normalized_title(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip()).upper()


def _collapsed_definition(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _title_from_definition(text: str) -> str:
    text = _collapsed_definition(text)
    if _STATEMENT_DEFINITION_SEPARATOR in text:
        text = text.split(_STATEMENT_DEFINITION_SEPARATOR, 1)[1]
    return text.strip()


def _statement_role_candidates(schema_bytes: bytes) -> list[tuple[str, str, bool]]:
    """(role_uri, title, is_statement) triples in schema order, from ``roleType``.

    ``is_statement`` is true when the definition carries the XBRL "Statement"
    category (``"<sort> - Statement - <title>"``); disclosures, policies and
    details are the other categories.
    """
    if not schema_bytes or b"\x00" in schema_bytes:
        return []
    if b"<!DOCTYPE" in schema_bytes.upper() or b"<!ENTITY" in schema_bytes.upper():
        return []
    try:
        root = ET.fromstring(schema_bytes)
    except ET.ParseError:
        return []
    pairs: list[tuple[str, str, bool]] = []
    for element in root.iter():
        if not element.tag.endswith("roleType"):
            continue
        role_uri = element.get("roleURI")
        if not isinstance(role_uri, str) or not role_uri:
            continue
        definition = next(
            (child.text for child in element if child.tag.endswith("definition")),
            None,
        )
        if not isinstance(definition, str) or not definition.strip():
            continue
        title = _title_from_definition(definition)
        if title:
            pairs.append(
                (
                    role_uri,
                    title,
                    _STATEMENT_DEFINITION_SEPARATOR in _collapsed_definition(definition),
                )
            )
    return pairs


# Per-kind title needles, most specific first; the global exclusions keep
# parenthetical/comprehensive/supplemental roles from stealing a match.
_STATEMENT_NEEDLES: dict[str, tuple[str, ...]] = {
    "income_statement": (
        "STATEMENTS OF OPERATIONS",
        "STATEMENT OF OPERATIONS",
        "STATEMENTS OF INCOME",
        "INCOME STATEMENT",
        "INCOME",
    ),
    "balance_sheet": ("BALANCE SHEET",),
    "cash_flow": (
        "STATEMENTS OF CASH FLOWS",
        "STATEMENT OF CASH FLOWS",
        "CASH FLOW STATEMENT",
        "CASH FLOWS",
        "CASH FLOW",
    ),
}
# Titles some issuers give their primary statements ("Consolidated Results of
# Operations", "Statement of Financial Position/Condition"). Disclosures reuse
# the same words ("... in Statement of Financial Position (Details)"), so these
# are searched over Statement-category roles only, after every needle above.
_STATEMENT_ONLY_NEEDLES: dict[str, tuple[str, ...]] = {
    "income_statement": ("RESULTS OF OPERATIONS",),
    "balance_sheet": ("FINANCIAL POSITION", "FINANCIAL CONDITION"),
    "cash_flow": (),
}
_STATEMENT_TITLE_EXCLUSIONS = ("PARENTHETICAL", "COMPREHENSIVE", "SHAREHOLDERS", "SUPPLEMENTAL")


def _pick_statement_role(
    pairs: list[tuple[str, str, bool]], kind: str
) -> dict[str, str] | None:
    """First schema-ordered role whose title names one primary statement kind.

    When the schema categorizes any role as a Statement, the search covers
    Statement-category roles only — a disclosure such as "Income taxes" can
    never be picked, and a kind no Statement role names is a typed mint
    failure rather than a guessed disclosure. A pick that was already a
    Statement role is unchanged: no earlier needle matched any role, so none
    matched a Statement role either. Only a schema with no Statement category
    at all falls back to the original needles over every role.
    """
    has_statement_category = any(is_statement for _, _, is_statement in pairs)
    if has_statement_category:
        needles = _STATEMENT_NEEDLES[kind] + _STATEMENT_ONLY_NEEDLES[kind]
    else:
        needles = _STATEMENT_NEEDLES[kind]
    for needle in needles:
        for role_uri, title, is_statement in pairs:
            if has_statement_category and not is_statement:
                continue
            normalized = _normalized_title(title)
            if needle not in normalized:
                continue
            if any(bad in normalized for bad in _STATEMENT_TITLE_EXCLUSIONS):
                continue
            search = _TRAILING_PARENTHETICAL.sub("", title).strip()
            return {
                "role_uri": role_uri,
                "title": re.sub(r"\s+", " ", title),
                "title_search": re.sub(r"\s+", " ", search),
            }
    return None


def mint_statement_roles(schema_bytes: bytes) -> dict[str, dict[str, str]]:
    """Declare the three primary-statement identities from the filing's own schema.

    ``reconstruct_primary_statements`` refuses any package without a declared
    ``statement_roles`` entry, so a schema that does not name all three kinds
    is a typed mint failure — never a silently unsearchable package.
    """
    pairs = _statement_role_candidates(schema_bytes)
    minted: dict[str, dict[str, str]] = {}
    for kind in ("income_statement", "balance_sheet", "cash_flow"):
        spec = _pick_statement_role(pairs, kind)
        if spec is None:
            raise FifMemberCaptureError(
                f"schema roleTypes do not name a primary {kind}",
                code="statement_roles_mint_failed",
            )
        minted[kind] = spec
    return minted


# ---------------------------------------------------------------------------
# Capture pass
# ---------------------------------------------------------------------------


def _fetch_member_bytes(
    collector: Any,
    *,
    archive_root: Path,
    cik: str,
    accession: str,
    name: str,
    retrieved_at: str,
    budget_remaining: int,
) -> bytes:
    document = {
        "document_id": f"{cik}:{accession}:{name}",
        "archive_url": archive_document_url(cik, accession, name),
    }
    try:
        receipt = collector.fetch_document(document, retrieved_at=retrieved_at)
    except Exception as exc:  # noqa: BLE001 - the network leg is typed, never fatal-silent
        raise FifMemberCaptureError(
            f"member fetch failed for {name}: {exc}", code="member_fetch_failed"
        ) from exc
    if not isinstance(receipt, Mapping) and not hasattr(receipt, "get"):
        receipt = receipt.to_dict()
    if dict(receipt).get("status") == "missing":
        raise FifMemberCaptureError(
            f"member is missing from the SEC archive: {name}", code="member_fetch_failed"
        )
    try:
        payload = read_archive_document(Path(archive_root), receipt)
    except Exception as exc:  # noqa: BLE001
        raise FifMemberCaptureError(
            f"member bytes could not be read back from the archive cache: {name} ({exc})",
            code="member_fetch_failed",
        ) from exc
    if not payload:
        raise FifMemberCaptureError(
            f"member fetched with empty bytes: {name}", code="malformed_member"
        )
    if b"\x00" in payload:
        raise FifMemberCaptureError(
            f"member fetched with NUL bytes: {name}", code="malformed_member"
        )
    if len(payload) > MAX_MEMBER_BYTES:
        raise FifMemberCaptureError(
            f"member exceeds the per-member byte ceiling: {name}", code="member_oversize"
        )
    if len(payload) > budget_remaining:
        raise FifMemberCaptureError(
            "member capture exceeded the per-run byte budget", code="run_budget_exceeded"
        )
    return bytes(payload)


def _verify_retained_package(package_dir: Path) -> RetainedFifPackage:
    """Read + digest-verify one package subtree; any drift is a typed refusal."""
    manifest_path = package_dir / MANIFEST_NAME
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FifMemberCaptureError(
            f"retained package manifest is unreadable: {package_dir}",
            code="package_manifest_malformed",
        ) from exc
    if not isinstance(manifest, Mapping):
        raise FifMemberCaptureError(
            f"retained package manifest is not an object: {package_dir}",
            code="package_manifest_malformed",
        )
    # D9: ALLOW-list, not a one-schema deny-list — a manifest with no schema
    # or any schema other than FIF_MEMBER_CAPTURE_PACKAGE_SCHEMA is refused
    # with the same typed golden-refusal code (a foreign corpus is never read
    # back as a lane package, whatever its schema claims to be).
    if manifest.get("schema") != FIF_MEMBER_CAPTURE_PACKAGE_SCHEMA:
        raise FifMemberCaptureError(
            f"retained package manifest schema is not the member-capture "
            f"schema ({FIF_MEMBER_CAPTURE_PACKAGE_SCHEMA}): {package_dir} "
            f"(found {manifest.get('schema')!r})",
            code="golden_input_refused",
        )
    try:
        index_bytes = (package_dir / INDEX_NAME).read_bytes()
        witness_bytes = (package_dir / WITNESS_NAME).read_bytes()
    except OSError as exc:
        raise FifMemberCaptureError(
            f"retained package is missing its index or witness: {package_dir}",
            code="package_bytes_mismatch",
        ) from exc
    index_meta = (
        hashlib.sha256(index_bytes).hexdigest(),
        len(index_bytes),
    )
    if index_meta[0] != manifest.get("index_sha256") or index_meta[1] != manifest.get(
        "index_byte_length"
    ):
        raise FifMemberCaptureError(
            f"retained package index bytes disagree with its manifest: {package_dir}",
            code="package_bytes_mismatch",
        )
    witness_meta = manifest.get("acceptance_witness")
    if not isinstance(witness_meta, Mapping):
        raise FifMemberCaptureError(
            f"retained package manifest has no acceptance witness: {package_dir}",
            code="package_manifest_malformed",
        )
    if (
        hashlib.sha256(witness_bytes).hexdigest() != witness_meta.get("content_sha256")
        or len(witness_bytes) != witness_meta.get("byte_length")
    ):
        raise FifMemberCaptureError(
            f"retained package witness bytes disagree with its manifest: {package_dir}",
            code="package_bytes_mismatch",
        )
    members_meta = manifest.get("members")
    if not isinstance(members_meta, list) or not members_meta:
        raise FifMemberCaptureError(
            f"retained package manifest has no member inventory: {package_dir}",
            code="package_manifest_malformed",
        )
    members: dict[str, bytes] = {}
    for item in members_meta:
        if not isinstance(item, Mapping):
            raise FifMemberCaptureError(
                f"retained package member row is malformed: {package_dir}",
                code="package_manifest_malformed",
            )
        state = item.get("state")
        if state not in _MEMBER_STATES:
            raise FifMemberCaptureError(
                f"retained package member state is not in the incumbent vocabulary: {package_dir}",
                code="inventory_mismatch",
            )
        if state != "stored":
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name:
            raise FifMemberCaptureError(
                f"retained package stored member is unnamed: {package_dir}",
                code="package_manifest_malformed",
            )
        try:
            payload = (package_dir / MEMBERS_DIR / name).read_bytes()
        except OSError as exc:
            raise FifMemberCaptureError(
                f"retained package stored member is absent: {name}",
                code="package_bytes_mismatch",
            ) from exc
        if (
            hashlib.sha256(payload).hexdigest() != item.get("content_sha256")
            or len(payload) != item.get("byte_length")
        ):
            raise FifMemberCaptureError(
                f"retained package member bytes disagree with its manifest: {name}",
                code="package_bytes_mismatch",
            )
        members[name] = payload
    cik = manifest.get("cik")
    accession = manifest.get("accession")
    if not isinstance(cik, str) or not isinstance(accession, str):
        raise FifMemberCaptureError(
            f"retained package identity is malformed: {package_dir}",
            code="package_manifest_malformed",
        )
    return RetainedFifPackage(
        cik=cik,
        accession=accession,
        manifest=manifest,
        index_bytes=index_bytes,
        members=members,
        witness_bytes=witness_bytes,
        package_dir=package_dir,
    )


def read_retained_fif_packages(
    archive_root: Path, *, cik: str, accessions: Sequence[str]
) -> tuple[RetainedFifPackage, ...]:
    """Every digest-verified retained package for one CIK, over the CONTRACT
    accessions only — never a directory listing (D4).

    Iterating the listing trusted the warm cache: an accession dropped by a
    later contract edit, or a foreign partially-restored directory, was read
    back and handed to admission. Now only the contract's accession paths are
    visited, so a stray directory is invisible by construction. A package
    directory that exists and is non-empty but carries no
    ``package_manifest.json`` is the typed refusal
    ``package_manifest_malformed`` (ERRATA E1-A: no silent skip); an absent or
    EMPTY directory is authoritative absence (the accession was never
    captured). The verified manifest's ``cik``/``accession`` must equal the
    path's — a cross-claimed package is the same typed refusal. Staging lives
    under ``fif-packages/.staging/`` and is never an accession path.
    """
    out: list[RetainedFifPackage] = []
    for accession in sorted({str(entry) for entry in accessions}):
        package_dir = package_dir_for(Path(archive_root), cik, accession)
        if not package_dir.exists():
            continue
        if not package_dir.is_dir():
            raise FifMemberCaptureError(
                f"retained package path is not a directory: {package_dir}",
                code="package_manifest_malformed",
            )
        if not any(package_dir.iterdir()):
            continue  # empty placeholder: authoritative absence
        if not (package_dir / MANIFEST_NAME).is_file():
            raise FifMemberCaptureError(
                f"retained package directory exists without {MANIFEST_NAME} "
                f"(partial restore?): {package_dir}",
                code="package_manifest_malformed",
            )
        retained = _verify_retained_package(package_dir)
        if retained.cik != cik or retained.accession != accession:
            raise FifMemberCaptureError(
                "retained package manifest identity disagrees with its path: "
                f"{package_dir} (manifest cik={retained.cik} "
                f"accession={retained.accession})",
                code="package_manifest_malformed",
            )
        out.append(retained)
    return tuple(out)


def _retained_package_state(package_dir: Path) -> str:
    """``absent`` | ``empty`` | ``partial`` | ``manifest`` for one package dir.

    ERRATA E1: ``partial`` — the directory EXISTS and is non-empty but carries
    no ``package_manifest.json`` — is the typed refusal
    ``package_manifest_malformed`` in the capture loop. A restore that lost the
    manifest must never fall through to the capture branch, which would
    re-capture the accession with tonight's clock and silently re-mint the
    capture clock every downstream id derives from. An absent or empty package
    dir still captures normally (nothing is half-restored there).
    """
    if not package_dir.exists():
        return "absent"
    if not package_dir.is_dir():
        return "partial"
    if not any(package_dir.iterdir()):
        return "empty"
    if not (package_dir / MANIFEST_NAME).is_file():
        return "partial"
    return "manifest"


def _parse_archive_index(index_bytes: bytes) -> list[dict[str, Any]]:
    """Parse the fetched archive ``index.json`` into its ``directory.item`` rows.

    D3: a status-200 throttle page, truncated JSON, or a wrong-shape payload is
    the typed refusal ``malformed_member`` — never a ``JSONDecodeError`` /
    ``KeyError`` escaping the capture loop (only ``FifMemberCaptureError`` is
    caught there, so an untyped parse crash would abort the whole run).
    """
    try:
        payload = json.loads(index_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FifMemberCaptureError(
            f"archive index is not UTF-8 JSON: {exc}", code="malformed_member"
        ) from exc
    if not isinstance(payload, dict):
        raise FifMemberCaptureError(
            "archive index is not a JSON object", code="malformed_member"
        )
    directory = payload.get("directory")
    if not isinstance(directory, dict):
        raise FifMemberCaptureError(
            "archive index carries no directory object", code="malformed_member"
        )
    items = directory.get("item")
    if not isinstance(items, list) or not items:
        raise FifMemberCaptureError(
            "archive index directory.item is missing or empty", code="malformed_member"
        )
    if not all(isinstance(item, dict) for item in items):
        raise FifMemberCaptureError(
            "archive index directory.item rows are malformed", code="malformed_member"
        )
    return items


def _index_member_sizes(items: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """Index-listed byte sizes by member name, where the index states one.

    The SEC index carries ``size`` as a string (sometimes blank); a member
    with no usable listed size is simply absent here — its ceilings stay with
    the post-fetch checks in ``_fetch_member_bytes``.
    """
    sizes: dict[str, int] = {}
    for item in items:
        name = item.get("name")
        size = item.get("size")
        if not isinstance(name, str):
            continue
        if isinstance(size, bool):
            continue
        if isinstance(size, int):
            sizes[name] = int(size)
        elif isinstance(size, str) and size.strip().isdigit():
            sizes[name] = int(size.strip())
    return sizes


def _prefetch_member_ceilings(
    items: Sequence[Mapping[str, Any]],
    *,
    stem: str,
    budget_remaining: int,
    policy: Mapping[str, tuple[tuple[str, str], ...]] | None = None,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """D12 + ERRATA-4 R1/R2/R3: refuse on the INDEX listing, before any fetch.

    The member-count ceiling, a planned member whose index-listed size breaks
    the per-member ceiling, a REQUIRED member absent from the index
    (``member_missing_from_index``, R3), and a planned member sum above the
    remaining run budget are all knowable up front — a budget already spent
    must not still download one member at a time to discover it. An OPTIONAL
    member the index does not name is decided ABSENT here (R2): it costs zero
    requests and zero budget. Returns ``(present, absent)`` (suffix, role)
    pairs in MEMBER_SUFFIX_ROLES order.
    """
    if len(items) > MAX_INDEX_MEMBERS:
        raise FifMemberCaptureError(
            "archive index exceeds the member-count ceiling", code="member_count_exceeded"
        )
    plan = dict(policy or {"required": MEMBER_SUFFIX_ROLES, "optional": ()})
    ordered = [pair for pair in MEMBER_SUFFIX_ROLES if pair in plan["required"] or pair in plan["optional"]]
    sizes = _index_member_sizes(items)
    present: list[tuple[str, str]] = []
    absent: list[tuple[str, str]] = []
    planned = 0
    for suffix, role in ordered:
        name = f"{stem}{suffix}"
        if name not in sizes:
            if pair_is_required(plan, suffix):
                raise FifMemberCaptureError(
                    f"planned member is absent from the archive index: {name}",
                    code="member_missing_from_index",
                )
            absent.append((suffix, role))
            continue
        listed = sizes[name]
        if listed > MAX_MEMBER_BYTES:
            raise FifMemberCaptureError(
                "member's index-listed size exceeds the per-member byte "
                f"ceiling: {name} ({listed} bytes)",
                code="member_oversize",
            )
        present.append((suffix, role))
        planned += listed
    if planned > budget_remaining:
        raise FifMemberCaptureError(
            "planned member fetches exceed the remaining run byte budget "
            f"({planned} > {budget_remaining})",
            code="run_budget_exceeded",
        )
    return present, absent


def pair_is_required(
    plan: Mapping[str, tuple[tuple[str, str], ...]], suffix: str
) -> bool:
    return any(pair[0] == suffix for pair in plan["required"])


def _write_package(
    package_dir: Path,
    *,
    cik: str,
    accession: str,
    identity: Mapping[str, Any] | None,
    bound_fields: Mapping[str, str],
    witness_bytes: bytes,
    witness_source_url: str,
    index_bytes: bytes,
    stored_members: Mapping[str, bytes],
    statement_roles: Mapping[str, dict[str, str]] | None,
    capture_recorded_at: str,
    absent_members: Sequence[Mapping[str, str]] = (),
) -> tuple[dict[str, Any], int, int]:
    """Assemble the package in staging and rename it into place atomically.

    ERRATA E1: the whole package directory becomes visible to readers in ONE
    ``os.rename`` — never file-by-file into the reader path. The staging dir is
    a sibling OUTSIDE every ``<cik>/<accession>`` reader path
    (``<archive_root>/fif-packages/.staging/<cik>-<accession>-<random>``), and
    the rename is asserted to stay on one filesystem (``st_dev``) first: a
    cross-device rename would not be atomic, and the typed refusal never falls
    back to a copy. Returns ``(manifest, files_written, bytes_written)`` so the
    run report can state the real per-night snapshot delta.
    """
    items = _parse_archive_index(index_bytes)
    if len(items) > MAX_INDEX_MEMBERS:
        raise FifMemberCaptureError(
            "archive index exceeds the member-count ceiling", code="member_count_exceeded"
        )
    inventory = [str(item.get("name") or "") for item in items]
    if any(not name for name in inventory) or len(inventory) != len(set(inventory)):
        raise FifMemberCaptureError(
            "archive index has unnamed or duplicate members", code="inventory_mismatch"
        )
    stored_names = set(stored_members)
    unknown = stored_names - set(inventory)
    if unknown:
        raise FifMemberCaptureError(
            f"fetched members are absent from the archive index: {sorted(unknown)}",
            code="member_missing_from_index",
        )
    primary_document = bound_fields["primaryDocument"]
    stem = primary_document.rsplit(".", 1)[0]
    role_by_name = {f"{stem}{suffix}": role for suffix, role in MEMBER_SUFFIX_ROLES}
    rows: list[dict[str, Any]] = []
    stored_count = 0
    for name in inventory:
        if name in stored_names:
            payload = stored_members[name]
            if name == primary_document:
                role = "primary"
            else:
                role = role_by_name.get(name)
            if role is None:
                raise FifMemberCaptureError(
                    f"stored member carries no recognizable role: {name}",
                    code="inventory_mismatch",
                )
            rows.append(
                {
                    "name": name,
                    "state": "stored",
                    "role": role,
                    "content_sha256": hashlib.sha256(payload).hexdigest(),
                    "byte_length": len(payload),
                    "path": f"{MEMBERS_DIR}/{name}",
                    "archive_url": archive_document_url(cik, accession, name),
                }
            )
            stored_count += 1
        else:
            rows.append(
                {
                    "name": name,
                    "state": "not_requested",
                    "role": "archive",
                    "declared_reason": "not required for XBRL statement reconstruction",
                    "archive_url": archive_document_url(cik, accession, name),
                }
            )
    manifest: dict[str, Any] = {
        "schema": FIF_MEMBER_CAPTURE_PACKAGE_SCHEMA,
        "cik": cik,
        "accession": accession,
        "form": bound_fields["form"],
        "primary_document": primary_document,
        "period_of_report": bound_fields["reportDate"],
        "filing_date": bound_fields["filingDate"],
        "source_accepted_at": bound_fields["acceptanceDateTime"],
        "capture_recorded_at": capture_recorded_at,
        "capture_basis": "reconstruction",
        "acceptance_witness": {
            "path": WITNESS_NAME,
            "source_url": witness_source_url,
            "content_sha256": hashlib.sha256(witness_bytes).hexdigest(),
            "byte_length": len(witness_bytes),
        },
        "archive_index_url": archive_index_url(cik, accession),
        "index_sha256": hashlib.sha256(index_bytes).hexdigest(),
        "index_byte_length": len(index_bytes),
        "member_count": len(inventory),
        "retained_count": stored_count,
        "members": rows,
    }
    # R6: an 8-K carries NO statement_roles key at all — the dei-only schema
    # names none of the three primary statements, and D1 already tolerates a
    # missing key. 10-K/10-Q keep the required mint unchanged.
    if statement_roles is not None:
        manifest["statement_roles"] = dict(statement_roles)
    # R2/R4: each absent OPTIONAL member is recorded under absent_members,
    # sorted by name; the key is OMITTED when empty and never written as [].
    if absent_members:
        manifest["absent_members"] = [
            {"role": str(entry["role"]), "name": str(entry["name"]), "reason": str(entry["reason"])}
            for entry in sorted(absent_members, key=lambda entry: str(entry["name"]))
        ]
    if identity is not None:
        for field in ("entity_id", "security_id", "listing_key"):
            value = identity.get(field)
            if isinstance(value, str) and value:
                manifest[field] = value
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )

    final_parent = package_dir.parent
    final_parent.mkdir(parents=True, exist_ok=True)
    staging_parent = final_parent.parent / STAGING_DIR_NAME
    staging_parent.mkdir(parents=True, exist_ok=True)
    # The rename is only atomic within one filesystem; a cross-device staging
    # root is a typed refusal, never a copy-based fallback.
    if os.stat(staging_parent).st_dev != os.stat(final_parent).st_dev:
        raise FifMemberCaptureError(
            f"package staging root is on a different filesystem than the package "
            f"parent, so the directory rename would not be atomic: {staging_parent}",
            code="staging_device_mismatch",
        )
    staging_dir = staging_parent / (
        f"{final_parent.name}-{package_dir.name}-{secrets.token_hex(8)}"
    )
    try:
        for name, payload in sorted(stored_members.items()):
            _atomic_write(staging_dir / MEMBERS_DIR / name, payload)
        _atomic_write(staging_dir / INDEX_NAME, index_bytes)
        _atomic_write(staging_dir / WITNESS_NAME, witness_bytes)
        _atomic_write(staging_dir / MANIFEST_NAME, manifest_bytes)
        if package_dir.exists():
            # Only reachable as an EMPTY dir (a partial dir was refused before
            # capture); an occupied target would make the rename clobber bytes.
            os.rmdir(package_dir)
        os.rename(staging_dir, package_dir)
    except Exception:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise
    files_written = len(stored_members) + 3
    bytes_written = (
        sum(len(payload) for payload in stored_members.values())
        + len(index_bytes)
        + len(witness_bytes)
        + len(manifest_bytes)
    )
    return manifest, files_written, bytes_written


def capture_fif_filing_packages(
    *,
    raw_root: Path,
    archive_root: Path,
    issuers: list[Mapping[str, Any]],
    collector: Any,
    pacer: Any,
    recorded_at: str,
    run_budget_bytes: int = DEFAULT_RUN_BUDGET_BYTES,
    submissions_collector: Any = None,
) -> dict[str, Any]:
    """Capture contract accessions whose primaries the lane retained this run.

    ``collector`` must be the archive collector constructed on the SAME shared
    ``pacer`` (A20); a privately paced collector is a typed refusal. Every
    fetch goes through ``collector.fetch_document`` so pacing, retry, and byte
    ceilings are the incumbent collector's, with the run budget enforced here.
    An already-retained accession is skipped and its ``capture_recorded_at``
    reused verbatim, so an unchanged night re-derives the same clocks.

    ``submissions_collector`` (C0-c ERRATA-5) is the SecForensicsCollector on
    the SAME shared pacer that fetches a covering ``filings.files[]`` page
    when an accession sits outside ``filings.recent``; it too must ride the
    shared pacer (A20). Page bytes are charged to the same run budget.
    """
    if getattr(collector, "_pacer", pacer) is not pacer:
        raise FifMemberCaptureError(
            "member capture requires the collector to ride the shared SecRequestPacer",
            code="private_pacer",
        )
    if submissions_collector is not None and (
        getattr(submissions_collector, "_pacer", pacer) is not pacer
    ):
        raise FifMemberCaptureError(
            "member capture requires the submissions collector to ride the "
            "shared SecRequestPacer",
            code="private_pacer",
        )
    normalized_clock = _utc_text(recorded_at, field="recorded_at")
    budget = int(run_budget_bytes)
    report: dict[str, Any] = {
        "schema": "fundamental_forensics.fif_member_capture_run/v1",
        "recorded_at": normalized_clock,
        # ERRATA E1 instrumentation: the per-night snapshot delta this run added
        # under the (snapshotted) fif-packages/ prefix. Reused packages
        # contribute nothing, so an unchanged night reports 0/0 and the first
        # schedule-born run reports the real one-time footprint.
        "package_files_written": 0,
        "package_bytes_written": 0,
        "issuers": [],
    }
    for issuer in issuers:
        cik = canonical_cik(issuer["cik"])
        identity = issuer.get("security_master_binding")
        issuer_row: dict[str, Any] = {"cik": cik, "accessions": []}
        for accession_entry in issuer.get("accessions") or []:
            accession = str(accession_entry["accession"])
            row: dict[str, Any] = {
                "accession": accession,
                "outcome": None,
                "capture_recorded_at": None,
                "reused": False,
            }
            package_dir = package_dir_for(Path(archive_root), cik, accession)
            try:
                state = _retained_package_state(package_dir)
                if state == "partial":
                    # ERRATA E1: a restored-but-manifest-less package dir is a
                    # typed refusal — NEVER a fall-through to the capture
                    # branch, which would re-capture with tonight's clock.
                    raise FifMemberCaptureError(
                        f"retained package directory exists without "
                        f"{MANIFEST_NAME} (partial restore?): {package_dir}",
                        code="package_manifest_malformed",
                    )
                if state == "manifest":
                    retained = _verify_retained_package(package_dir)
                    row.update(
                        outcome="retained_reused",
                        capture_recorded_at=retained.capture_recorded_at,
                        reused=True,
                    )
                    issuer_row["accessions"].append(row)
                    continue
                retained_manifest = find_retained_primary_manifest(
                    Path(archive_root), cik=cik, accession=accession
                )
                if retained_manifest is None:
                    row["outcome"] = "no_retained_primary"
                    issuer_row["accessions"].append(row)
                    continue
                primary_name = _primary_name_of(retained_manifest)
                # R1: the member set is keyed by the CONTRACT form — never
                # inferred from file content — and is resolved BEFORE any
                # fetch (an unknown form is the typed refusal).
                contract_form = str(accession_entry.get("form") or "")
                policy = member_policy_for(contract_form)
                witness_bytes, bound_fields, page_info = mint_acceptance_witness(
                    raw_root=Path(raw_root),
                    cik=cik,
                    accession=accession,
                    primary_document=primary_name,
                    filing_date=str(accession_entry.get("filing_date") or ""),
                    submissions_collector=submissions_collector,
                    retrieved_at=normalized_clock,
                    budget_remaining=budget,
                )
                if page_info is not None and page_info["charged_bytes"]:
                    # ERRATA-5 rule 3: page bytes count toward the same run
                    # budget (a reused page costs nothing).
                    budget -= int(page_info["charged_bytes"])
                # R8: the contract row must agree with the witness-bound row —
                # BEFORE the index fetch, on BOTH witness paths (the recent
                # path's witness BYTES stay byte-identical; this is a check).
                if (
                    contract_form.strip().upper() != bound_fields["form"].strip().upper()
                    or str(accession_entry.get("filing_date") or "").strip()
                    != bound_fields["filingDate"].strip()
                ):
                    raise FifMemberCaptureError(
                        f"contract row disagrees with the witness-bound row for "
                        f"{accession}: form {contract_form!r} vs "
                        f"{bound_fields['form']!r}, filing_date "
                        f"{accession_entry.get('filing_date')!r} vs "
                        f"{bound_fields['filingDate']!r}",
                        code="submissions_row_mismatch",
                    )
                # Fetch the archive index, then the policy's role members by
                # stem. The primary itself is NOT re-fetched: retained.
                index_bytes = _fetch_member_bytes(
                    collector,
                    archive_root=Path(archive_root),
                    cik=cik,
                    accession=accession,
                    name=INDEX_NAME,
                    retrieved_at=normalized_clock,
                    budget_remaining=budget,
                )
                budget -= len(index_bytes)
                stem = primary_name.rsplit(".", 1)[0]
                # D12 + R2/R3: every ceiling knowable from the index listing
                # fires here, BEFORE any member fetch (the index is the only
                # fetch a refused accession makes); an optional member the
                # index does not name is decided ABSENT at zero cost.
                present, absent = _prefetch_member_ceilings(
                    _parse_archive_index(index_bytes),
                    stem=stem,
                    budget_remaining=budget,
                    policy=policy,
                )
                stored: dict[str, bytes] = {}
                for suffix, _role in present:
                    name = f"{stem}{suffix}"
                    payload = _fetch_member_bytes(
                        collector,
                        archive_root=Path(archive_root),
                        cik=cik,
                        accession=accession,
                        name=name,
                        retrieved_at=normalized_clock,
                        budget_remaining=budget,
                    )
                    budget -= len(payload)
                    stored[name] = payload
                stored[primary_name] = _read_retained_primary(
                    Path(archive_root), retained_manifest
                )
                # R6: 10-K/10-Q mint the three primary-statement identities
                # from the filing's own schema (unchanged, required); an 8-K
                # mints NONE and OMITS the manifest key.
                statement_roles = (
                    mint_statement_roles(stored[f"{stem}.xsd"])
                    if contract_form.strip().upper() in ("10-K", "10-Q")
                    else None
                )
                absent_entries = [
                    {
                        "role": role,
                        "name": f"{stem}{suffix}",
                        "reason": ABSENT_MEMBER_REASON,
                    }
                    for suffix, role in absent
                ]
                _manifest, files_written, bytes_written = _write_package(
                    package_dir,
                    cik=cik,
                    accession=accession,
                    identity=identity,
                    bound_fields=bound_fields,
                    witness_bytes=witness_bytes,
                    witness_source_url=json.loads(witness_bytes.decode("utf-8"))[
                        "source_url"
                    ],
                    index_bytes=index_bytes,
                    stored_members=stored,
                    statement_roles=statement_roles,
                    capture_recorded_at=normalized_clock,
                    absent_members=absent_entries,
                )
                report["package_files_written"] += files_written
                report["package_bytes_written"] += bytes_written
                row.update(
                    outcome="captured",
                    capture_recorded_at=normalized_clock,
                )
            except FifMemberCaptureError as exc:
                row.update(outcome=f"member_capture_failed:{exc.code}", error=str(exc))
            issuer_row["accessions"].append(row)
        report["issuers"].append(issuer_row)
    return report


def _read_retained_primary(archive_root: Path, manifest: Mapping[str, Any]) -> bytes:
    from collectors.sec_document_spine import read_primary_document

    try:
        return read_primary_document(Path(archive_root), manifest)
    except Exception as exc:  # noqa: BLE001
        raise FifMemberCaptureError(
            f"retained primary bytes are unreadable: {exc}",
            code="package_bytes_mismatch",
        ) from exc


__all__ = [
    "DEFAULT_RUN_BUDGET_BYTES",
    "FIF_MEMBER_CAPTURE_PACKAGE_SCHEMA",
    "FifMemberCaptureError",
    "GOLDEN_PACKAGE_SCHEMAS",
    "MANIFEST_NAME",
    "MAX_INDEX_MEMBERS",
    "MAX_MEMBER_BYTES",
    "MEMBER_SUFFIX_ROLES",
    "PACKAGE_PREFIX",
    "RETAINED_PACKAGE_INTEGRITY_CODES",
    "RetainedFifPackage",
    "STAGING_DIR_NAME",
    "capture_fif_filing_packages",
    "find_retained_primary_manifest",
    "mint_acceptance_witness",
    "mint_statement_roles",
    "package_dir_for",
    "retain_submissions_page",
    "select_submissions_page",
    "submissions_page_entry",
    "read_retained_fif_packages",
    "find_verified_submissions_page",
    "refuse_repository_fixture_inputs",
]
