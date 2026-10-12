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

import hashlib
import json
import os
import re
import secrets
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from xml.etree import ElementTree as ET

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
# The committed golden fixture manifest schemas are a different corpus. A
# package claiming one of them is refused with a typed error: production
# generations are built from lane-retained bytes, never fixture trees.
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
    }
)

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
) -> tuple[bytes, dict[str, str]]:
    """Bind the Submissions-row slice for one accession to exact manifest fields.

    The slice is the incumbent 7-bound-field witness shape (accessionNumber,
    form, filingDate, reportDate, acceptanceDateTime, primaryDocument) plus its
    two source pointers (source_url, source_path). A row that disagrees with
    the retained manifest's primary document is a typed identity refusal.
    """
    try:
        submissions, receipt = read_verified_submissions(Path(raw_root), cik)
    except Exception as exc:  # noqa: BLE001 - AcquisitionError and friends are typed here
        raise FifMemberCaptureError(
            f"retained Submissions bytes are unavailable for CIK {cik}: {exc}",
            code="submissions_unavailable",
        ) from exc
    recent = (submissions.get("filings") or {}).get("recent") or {}
    accessions = recent.get("accessionNumber")
    if not isinstance(accessions, list) or accession not in accessions:
        raise FifMemberCaptureError(
            f"accession is absent from the retained Submissions rows: {accession}",
            code="accession_not_in_submissions",
        )
    row_index = accessions.index(accession)

    def _cell(field: str) -> Any:
        values = recent.get(field)
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
        "source_url": str(receipt.get("url") or ""),
        "source_path": f"filings.recent[accessionNumber={accession}]",
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
    return payload, bound


# ---------------------------------------------------------------------------
# Statement-role mint (issuer-generic, from the fetched schema member)
# ---------------------------------------------------------------------------


def _normalized_title(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip()).upper()


def _title_from_definition(text: str) -> str:
    if _STATEMENT_DEFINITION_SEPARATOR in text:
        text = text.split(_STATEMENT_DEFINITION_SEPARATOR, 1)[1]
    return re.sub(r"\s+", " ", text.strip())


def _statement_role_candidates(schema_bytes: bytes) -> list[tuple[str, str]]:
    """(role_uri, title) pairs in schema order, from ``roleType`` definitions."""
    if not schema_bytes or b"\x00" in schema_bytes:
        return []
    if b"<!DOCTYPE" in schema_bytes.upper() or b"<!ENTITY" in schema_bytes.upper():
        return []
    try:
        root = ET.fromstring(schema_bytes)
    except ET.ParseError:
        return []
    pairs: list[tuple[str, str]] = []
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
            pairs.append((role_uri, title))
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
_STATEMENT_TITLE_EXCLUSIONS = ("PARENTHETICAL", "COMPREHENSIVE", "SHAREHOLDERS", "SUPPLEMENTAL")


def _pick_statement_role(
    pairs: list[tuple[str, str]], kind: str
) -> dict[str, str] | None:
    """First schema-ordered role whose title names one primary statement kind."""
    for needle in _STATEMENT_NEEDLES[kind]:
        for role_uri, title in pairs:
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
    if manifest.get("schema") in GOLDEN_PACKAGE_SCHEMAS:
        raise FifMemberCaptureError(
            f"retained package claims a golden fixture schema: {package_dir}",
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
    archive_root: Path, *, cik: str
) -> tuple[RetainedFifPackage, ...]:
    """Every digest-verified retained package for one CIK, in accession order.

    A leftover staging directory (or any dot-prefixed sibling) is never read
    back as a package: staging lives under ``fif-packages/.staging/`` and is
    structurally outside every ``<cik>/`` path, and this listing skips
    dot-entries defensively as well.
    """
    root = Path(archive_root) / PACKAGE_PREFIX / cik
    if not root.is_dir():
        return ()
    out: list[RetainedFifPackage] = []
    for accession_dir in sorted(root.iterdir()):
        if accession_dir.name.startswith("."):
            continue
        if not accession_dir.is_dir():
            continue
        if not (accession_dir / MANIFEST_NAME).is_file():
            continue
        out.append(_verify_retained_package(accession_dir))
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
    statement_roles: Mapping[str, dict[str, str]],
    capture_recorded_at: str,
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
        "statement_roles": dict(statement_roles),
        "members": rows,
    }
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
) -> dict[str, Any]:
    """Capture contract accessions whose primaries the lane retained this run.

    ``collector`` must be the archive collector constructed on the SAME shared
    ``pacer`` (A20); a privately paced collector is a typed refusal. Every
    fetch goes through ``collector.fetch_document`` so pacing, retry, and byte
    ceilings are the incumbent collector's, with the run budget enforced here.
    An already-retained accession is skipped and its ``capture_recorded_at``
    reused verbatim, so an unchanged night re-derives the same clocks.
    """
    if getattr(collector, "_pacer", pacer) is not pacer:
        raise FifMemberCaptureError(
            "member capture requires the collector to ride the shared SecRequestPacer",
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
                witness_bytes, bound_fields = mint_acceptance_witness(
                    raw_root=Path(raw_root),
                    cik=cik,
                    accession=accession,
                    primary_document=primary_name,
                )
                # Fetch the archive index, then the five role members by stem.
                # The primary itself is NOT re-fetched: it is already retained.
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
                stored: dict[str, bytes] = {}
                for suffix, _role in MEMBER_SUFFIX_ROLES:
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
                statement_roles = mint_statement_roles(stored[f"{stem}.xsd"])
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
    "read_retained_fif_packages",
    "refuse_repository_fixture_inputs",
]
