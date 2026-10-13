"""Issuer-generic admission of already-captured SEC archive bytes.

Turns in-memory index/manifest/member/witness bytes into a digest-verified,
role-complete package the incumbent D3 publication path and iXBRL ledger
converter consume unchanged. This module performs no I/O: no filesystem, no
network, no clock read, no second SEC request budget.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from xml.etree import ElementTree as ET

from collectors.sec_filing_parser import (
    SecFilingParseError,
    parse_sec_filing_document,
    validate_sec_filing_parse_result,
)

from .filing_attestation import TAXONOMY_NAMESPACE_POLICY, _qname_to_taxonomy
from .filing_package import _MEMBER_STATES
from .production_datasets import LAWFUL_CAPTURE_BASES
from .sec_document_spine import (
    HARD_MAX_ARCHIVE_DOCUMENT_BYTES,
    HARD_MAX_ARCHIVE_INDEX_MEMBERS,
    archive_document_url,
    archive_index_url,
    canonical_cik,
)

ADMITTED_FILING_PACKAGE_SCHEMA = "fundamental_forensics.admitted_filing_package/v1"
REQUIRED_STORED_ROLES = (
    "primary",
    "schema",
    "calculation",
    "definition",
    "label",
    "presentation",
)
# C0-c ERRATA-4 R7 (seat-ratified D1 edit, scoped to ERRATA-4 ONLY): the
# per-form map is ADDITIVE and relaxes EXACTLY the form string "8-K". Every
# other form string — including 8-K/A and 10-K/A — resolves to the unchanged
# strict REQUIRED_STORED_ROLES, and the 10-K/10-Q admission path is
# behaviour-identical. The form is the WITNESS-BOUND form (R8 makes it equal
# the contract form), and admission is no-I/O and holds no contract.
FORM_REQUIRED_STORED_ROLES: dict[str, tuple[str, ...]] = {
    "8-K": ("primary", "schema", "label", "presentation"),
}
_FORM_OPTIONAL_STORED_ROLES: dict[str, tuple[str, ...]] = {
    "8-K": ("calculation", "definition"),
}
_ABSENT_MEMBER_KEYS = frozenset({"role", "name", "reason"})
_ABSENT_MEMBER_REASON = "absent_in_archive_index"
_OPTIONAL_ROLE_SUFFIX = {"calculation": "_cal.xml", "definition": "_def.xml"}

_REFUSAL_CODES = frozenset(
    {
        "index_digest_mismatch",
        "index_malformed",
        "inventory_mismatch",
        "required_role_missing",
        "member_digest_mismatch",
        "member_oversize",
        "witness_mismatch",
        "clock_order_violation",
        "unlawful_capture_basis",
        "attestation_claim_refused",
        "primary_unparseable",
        "identity_mismatch",
    }
)
_RELATED_EVENT_REF_KEYS = frozenset(
    {"plane", "event_id", "relation", "source_filing_distinction"}
)
_WITNESS_BIND = (
    ("accession", "accessionNumber"),
    ("form", "form"),
    ("primary_document", "primaryDocument"),
    ("period_of_report", "reportDate"),
    ("filing_date", "filingDate"),
    ("source_accepted_at", "acceptanceDateTime"),
)
_CIK_IN_URL_RE = re.compile(r"CIK(\d{1,10})")
_ACCESSION_RE = re.compile(r"\A[0-9]{10}-[0-9]{2}-[0-9]{6}\Z")
_FORBIDDEN_DECL = (b"<!DOCTYPE", b"<!ENTITY")


class AdmittedFilingPackageError(ValueError):
    """The captured bytes cannot be admitted as a complete filing package."""

    def __init__(self, message: str, *, code: str) -> None:
        if code not in _REFUSAL_CODES:
            raise ValueError(f"unknown admission refusal code: {code}")
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class AdmittedFilingPackage:
    """Digest-verified, role-complete package. Duck-compatible with GoldenFilingPackage."""

    manifest: Mapping[str, Any]
    members: Mapping[str, bytes]
    parse_evidence: Mapping[str, Any]


def _refuse(message: str, *, code: str) -> None:
    raise AdmittedFilingPackageError(message, code=code)


def _aware_utc(value: Any, *, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        _refuse(f"{field} is not an aware ISO-8601 UTC clock", code="clock_order_violation")
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise AdmittedFilingPackageError(
            f"{field} is not an aware ISO-8601 UTC clock",
            code="clock_order_violation",
        ) from exc
    if parsed.tzinfo is None:
        _refuse(f"{field} is not an aware ISO-8601 UTC clock", code="clock_order_violation")
    return parsed.astimezone(timezone.utc)


def _decode_json_object(raw: bytes, *, code: str, name: str) -> dict[str, Any]:
    if _FORBIDDEN_DECL[0] in raw or b"\x00" in raw:
        _refuse(f"{name} is malformed", code=code)
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AdmittedFilingPackageError(f"{name} is malformed", code=code) from exc
    if not isinstance(parsed, dict):
        _refuse(f"{name} is malformed", code=code)
    return parsed


def _admit_statement_roles(manifest: Mapping[str, Any]) -> None:
    extras = manifest.get("statement_roles")
    if extras is None:
        return
    if not isinstance(extras, dict):
        _refuse("statement_roles are malformed", code="inventory_mismatch")
    for kind in ("income_statement", "balance_sheet", "cash_flow"):
        spec = extras.get(kind)
        if not isinstance(spec, dict):
            _refuse(f"statement role is missing: {kind}", code="inventory_mismatch")
        if not isinstance(spec.get("role_uri"), str) or not spec["role_uri"]:
            _refuse(f"statement role_uri is missing: {kind}", code="inventory_mismatch")
        if not isinstance(spec.get("title"), str) or not spec["title"]:
            _refuse(f"statement title is missing: {kind}", code="inventory_mismatch")


def _admit_related_event_ref(manifest: Mapping[str, Any]) -> None:
    raw = manifest.get("related_event_ref")
    if raw is None:
        return
    if not isinstance(raw, dict) or set(raw) != _RELATED_EVENT_REF_KEYS:
        _refuse("related_event_ref is not the stable reference", code="identity_mismatch")
    if "generation_id" in raw:
        _refuse("related_event_ref must not mint generation identity", code="identity_mismatch")
    if not all(isinstance(raw.get(key), str) and raw[key] for key in ("plane", "event_id", "relation")):
        _refuse("related_event_ref is not the stable reference", code="identity_mismatch")
    distinction = raw.get("source_filing_distinction")
    if not isinstance(distinction, dict):
        _refuse("related_event_ref is not the stable reference", code="identity_mismatch")
    eight_k = distinction.get("earnings_release_8k_accession")
    periodic = distinction.get("periodic_report_accession")
    if not isinstance(eight_k, str) or not isinstance(periodic, str) or not eight_k or not periodic:
        _refuse("related_event_ref is not the stable reference", code="identity_mismatch")
    if eight_k == periodic:
        _refuse("related_event_ref collapses distinct filings", code="identity_mismatch")
    if periodic != manifest.get("accession"):
        _refuse("related_event_ref is not bound to this filing", code="identity_mismatch")


def _schema_target_namespace(schema_bytes: bytes) -> str | None:
    """Read the stored schema member's targetNamespace. Never follows URLs."""
    if not schema_bytes or len(schema_bytes) > HARD_MAX_ARCHIVE_DOCUMENT_BYTES:
        return None
    if b"\x00" in schema_bytes:
        return None
    upper = schema_bytes.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        return None
    try:
        root = ET.fromstring(schema_bytes)
    except ET.ParseError:
        return None
    value = root.get("targetNamespace")
    if isinstance(value, str) and value:
        return value
    return None


def _unadmitted_namespaces(
    parsed: Mapping[str, Any],
    *,
    extension_namespace: str | None,
) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for fact in parsed.get("facts") or []:
        if not isinstance(fact, Mapping):
            continue
        qname = fact.get("concept_qname")
        if not isinstance(qname, str) or not qname.startswith("{") or "}" not in qname:
            continue
        uri = qname[1:].split("}", 1)[0]
        if not uri:
            continue
        if extension_namespace is not None and uri == extension_namespace:
            continue
        # Reuse the incumbent policy table; never invent a second mapping.
        if TAXONOMY_NAMESPACE_POLICY.get(uri) is not None or _qname_to_taxonomy(qname) is not None:
            continue
        counts[uri] = counts.get(uri, 0) + 1
    return [{"uri": uri, "fact_count": counts[uri]} for uri in sorted(counts)]


_DEI_BASE = "http://xbrl.sec.gov/dei"


def _dei_local_name(qname: Any) -> str | None:
    """Local name of a dei-taxonomy qname (any dei year), else None."""
    if not isinstance(qname, str) or not qname.startswith("{") or "}" not in qname:
        return None
    namespace, _, local = qname[1:].partition("}")
    if namespace != _DEI_BASE and not namespace.startswith(_DEI_BASE + "/"):
        return None
    return local or None


def _dei_identity(parsed: Mapping[str, Any]) -> dict[str, Any]:
    """As-filed issuer identity from the parsed primary document alone.

    Pure lookup over parser facts: every available dei EntityCentralIndexKey
    value and the first available dei EntityRegistrantName value. Never
    consults a current issuer, security, or statement master (D3-F5): the
    name recorded here is the one the filing itself carried, not a
    today-label.
    """
    cik_values: list[str] = []
    registrant_name: str | None = None
    for fact in parsed.get("facts") or []:
        if not isinstance(fact, Mapping):
            continue
        local = _dei_local_name(fact.get("concept_qname"))
        if local is None or fact.get("status") != "available":
            continue
        value = fact.get("transformed_value")
        if not isinstance(value, str):
            value = fact.get("raw_value")
        if not isinstance(value, str) or not value:
            continue
        if local == "EntityCentralIndexKey":
            cik_values.append(value)
        elif local == "EntityRegistrantName" and registrant_name is None:
            registrant_name = value
    return {
        "entity_cik_values": tuple(cik_values),
        "registrant_name_as_filed": registrant_name,
    }


def _parse_evidence(parsed: Mapping[str, Any], unadmitted: list[dict[str, Any]]) -> dict[str, Any]:
    parser_meta = parsed.get("parser") if isinstance(parsed.get("parser"), Mapping) else {}
    coverage = parsed.get("coverage") if isinstance(parsed.get("coverage"), Mapping) else {}
    evidence: dict[str, Any] = {
        "schema": parsed.get("schema"),
        "profile": parser_meta.get("profile"),
        "version": parser_meta.get("version"),
        "algorithm_fingerprint": parser_meta.get("algorithm_fingerprint"),
        "fact_count": coverage.get("fact_count", len(parsed.get("facts") or [])),
        "context_count": coverage.get("context_count", len(parsed.get("contexts") or [])),
        "unit_count": coverage.get("unit_count", len(parsed.get("units") or [])),
        "diagnostics": list(parsed.get("diagnostics") or []),
        "coverage": dict(coverage),
        "taxonomy_validation_complete": False,
        "unadmitted_namespaces": unadmitted,
    }
    for key, value in parsed.items():
        if "unsupported" in str(key).lower() and key not in evidence:
            evidence[key] = value
    return evidence


def admit_retained_filing_package(
    *,
    index_bytes: bytes,
    manifest: Mapping[str, Any],
    members: Mapping[str, bytes],
    witness_bytes: bytes,
    capture_recorded_at: str,
    capture_basis: str = "reconstruction",
) -> AdmittedFilingPackage:
    """Admit already-captured archive bytes. No filesystem, network, or now()."""
    if type(index_bytes) is not bytes:
        _refuse("archive index must be exact bytes", code="index_malformed")
    if type(witness_bytes) is not bytes:
        _refuse("acceptance witness must be exact bytes", code="witness_mismatch")
    if not isinstance(manifest, Mapping):
        _refuse("package inventory is malformed", code="inventory_mismatch")
    if not isinstance(members, Mapping):
        _refuse("package inventory is malformed", code="inventory_mismatch")

    # A19: refuse oversize members/index BEFORE hashing or parsing.
    if len(index_bytes) > HARD_MAX_ARCHIVE_DOCUMENT_BYTES:
        _refuse("archive index exceeds the document byte bound", code="member_oversize")
    for name, payload in members.items():
        if type(payload) is not bytes:
            _refuse(f"stored member is not exact bytes: {name}", code="member_digest_mismatch")
        if len(payload) > HARD_MAX_ARCHIVE_DOCUMENT_BYTES:
            _refuse(f"archive member exceeds the document byte bound: {name}", code="member_oversize")

    # A13: reconstruction label; never historical attestation.
    if capture_basis not in LAWFUL_CAPTURE_BASES:
        _refuse("capture_basis is not a lawful capture basis", code="unlawful_capture_basis")
    if manifest.get("attested") or capture_basis != "reconstruction":
        _refuse("attestation claim refused on a reconstruction capture", code="attestation_claim_refused")

    accepted_at = _aware_utc(manifest.get("source_accepted_at"), field="source_accepted_at")
    recorded_at = _aware_utc(capture_recorded_at, field="capture_recorded_at")
    if recorded_at < accepted_at:
        _refuse(
            "capture_recorded_at precedes source_accepted_at",
            code="clock_order_violation",
        )

    index_sha = hashlib.sha256(index_bytes).hexdigest()
    if index_sha != manifest.get("index_sha256"):
        _refuse("archive index digest mismatch", code="index_digest_mismatch")
    if len(index_bytes) != manifest.get("index_byte_length"):
        _refuse("archive index length mismatch", code="index_digest_mismatch")
    try:
        index_payload = json.loads(index_bytes.decode("utf-8"))
        items = index_payload["directory"]["item"]
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise AdmittedFilingPackageError(
            "archive index is malformed", code="index_malformed"
        ) from exc
    if not isinstance(items, list):
        _refuse("archive index is malformed", code="index_malformed")
    if len(items) > HARD_MAX_ARCHIVE_INDEX_MEMBERS:
        _refuse("archive index exceeds the member-count bound", code="member_oversize")
    index_names = [str(item.get("name") or "") for item in items]
    if any(not name for name in index_names):
        _refuse("archive index has an unnamed member", code="index_malformed")
    if len(index_names) != len(set(index_names)):
        _refuse("archive index has duplicate members", code="index_malformed")

    members_meta = manifest.get("members")
    if not isinstance(members_meta, list):
        _refuse("package inventory is malformed", code="inventory_mismatch")
    manifest_names = [str(item.get("name") or "") for item in members_meta]
    if any(not name for name in manifest_names):
        _refuse("package inventory has an unnamed member", code="inventory_mismatch")
    if len(manifest_names) != len(set(manifest_names)):
        _refuse("package inventory has duplicate members", code="inventory_mismatch")
    extra = set(manifest_names) - set(index_names)
    missing = set(index_names) - set(manifest_names)
    if extra or missing:
        _refuse("package inventory does not match the archive index", code="inventory_mismatch")
    committed = manifest.get("member_count")
    if not isinstance(committed, int) or committed < 1 or len(index_names) != committed:
        _refuse("package inventory count does not match the committed index", code="inventory_mismatch")
    _admit_statement_roles(manifest)
    _admit_related_event_ref(manifest)

    witness_meta = manifest.get("acceptance_witness")
    if not isinstance(witness_meta, dict):
        _refuse("acceptance witness is missing", code="witness_mismatch")
    if hashlib.sha256(witness_bytes).hexdigest() != witness_meta.get("content_sha256"):
        _refuse("acceptance witness digest mismatch", code="witness_mismatch")
    if len(witness_bytes) != witness_meta.get("byte_length"):
        _refuse("acceptance witness length mismatch", code="witness_mismatch")
    witness = _decode_json_object(witness_bytes, code="witness_mismatch", name="acceptance witness")
    for manifest_field, witness_field in _WITNESS_BIND:
        if manifest.get(manifest_field) != witness.get(witness_field):
            _refuse(
                f"{manifest_field} is not bound to the acceptance witness",
                code="witness_mismatch",
            )

    try:
        cik10 = canonical_cik(manifest.get("cik"))
    except Exception as exc:
        raise AdmittedFilingPackageError(
            "package CIK is not a canonical identity",
            code="identity_mismatch",
        ) from exc
    accession = manifest.get("accession")
    if not isinstance(accession, str) or not _ACCESSION_RE.fullmatch(accession):
        _refuse("package accession is not a canonical identity", code="identity_mismatch")
    # The accession prefix names the TRANSMITTING filer/agent CIK (Donnelley
    # 0000950170, Workiva 0001628280), not the issuer — incumbent law in
    # broad_sec_store edgar-index rows and companyfacts accessions. Bind the
    # issuer through the archive URLs, the witness, and the filing's own dei
    # facts instead, so an agent-filed issuer admits while a mis-claimed
    # package still refuses.
    try:
        expected_index_url = archive_index_url(cik10, accession)
    except Exception as exc:
        raise AdmittedFilingPackageError(
            "package archive_index_url is not canonical",
            code="identity_mismatch",
        ) from exc
    if manifest.get("archive_index_url") != expected_index_url:
        _refuse(
            "package archive_index_url is not bound to the package identity",
            code="identity_mismatch",
        )
    source_url = witness.get("source_url")
    if isinstance(source_url, str):
        found = _CIK_IN_URL_RE.search(source_url)
        if found is not None:
            try:
                witness_cik = canonical_cik(found.group(1))
            except Exception as exc:
                raise AdmittedFilingPackageError(
                    "acceptance witness CIK is not a canonical identity",
                    code="identity_mismatch",
                ) from exc
            if witness_cik != cik10:
                _refuse("package CIK is not bound to the acceptance witness", code="identity_mismatch")

    stored: dict[str, bytes] = {}
    stored_count = 0
    stored_roles: set[str] = set()
    index_name_set = set(index_names)
    for item in members_meta:
        if not isinstance(item, dict):
            _refuse("stored member is malformed", code="inventory_mismatch")
        name = item.get("name")
        if not isinstance(name, str):
            _refuse("stored member is malformed", code="inventory_mismatch")
        # A10/A17: the incumbent closed member-state vocabulary. A junk,
        # missing, or non-string state refuses here — it must never hide a
        # member from the inventory accounting.
        state = item.get("state")
        if not isinstance(state, str) or state not in _MEMBER_STATES:
            _refuse(
                f"member state is not in the incumbent vocabulary: {name}",
                code="inventory_mismatch",
            )
        # Issuer identity bind: a member that carries archive_url must point
        # inside this issuer's archive directory for this accession.
        if "archive_url" in item:
            try:
                expected_url = archive_document_url(cik10, accession, name)
            except Exception as exc:
                raise AdmittedFilingPackageError(
                    f"member archive_url is not canonical: {name}",
                    code="identity_mismatch",
                ) from exc
            if item.get("archive_url") != expected_url:
                _refuse(
                    f"member archive_url is not bound to the package identity: {name}",
                    code="identity_mismatch",
                )
        if state != "stored":
            continue
        stored_count += 1
        if name not in index_name_set:
            _refuse(f"stored member is not in the archive index: {name}", code="inventory_mismatch")
        payload = members.get(name)
        if type(payload) is not bytes:
            _refuse(f"stored member is missing: {name}", code="member_digest_mismatch")
        digest = hashlib.sha256(payload).hexdigest()
        if digest != item.get("content_sha256") or len(payload) != item.get("byte_length"):
            _refuse(f"member digest mismatch: {name}", code="member_digest_mismatch")
        stored[name] = payload
        role = item.get("role")
        if isinstance(role, str) and role:
            stored_roles.add(role)

    # A17 + R7: never return a partial package; every required role FOR THE
    # FORM must be stored with a verified digest and length. The per-form map
    # relaxes exactly "8-K" (schema/label/presentation + primary); every other
    # form string resolves to the unchanged strict REQUIRED_STORED_ROLES.
    form = str(manifest.get("form") or "")
    required_roles = FORM_REQUIRED_STORED_ROLES.get(form, REQUIRED_STORED_ROLES)
    # R7 bounds first: absent_members on any non-8-K form is inventory_
    # mismatch even when the strict role loop would also refuse (8-K/A).
    _admit_absent_members(
        manifest,
        index_names=index_names,
        form=form,
        stored_roles=stored_roles,
        primary_name=primary_of_manifest(manifest),
    )
    for role in required_roles:
        if role not in stored_roles:
            _refuse(f"required stored role is missing: {role}", code="required_role_missing")
    if stored_count != manifest.get("retained_count"):
        _refuse("retained count does not match stored members", code="inventory_mismatch")
    primary = manifest.get("primary_document")
    if not isinstance(primary, str) or primary not in stored:
        _refuse("primary document is not retained", code="required_role_missing")

    schema_bytes = None
    for item in members_meta:
        if isinstance(item, dict) and item.get("state") == "stored" and item.get("role") == "schema":
            schema_name = item.get("name")
            if isinstance(schema_name, str):
                schema_bytes = stored.get(schema_name)
            break
    extension_ns = _schema_target_namespace(schema_bytes) if schema_bytes is not None else None

    try:
        parsed = parse_sec_filing_document(stored[primary], document_name=primary)
        validate_sec_filing_parse_result(parsed)
    except SecFilingParseError as exc:
        raise AdmittedFilingPackageError(str(exc), code="primary_unparseable") from exc

    dei = _dei_identity(parsed)
    for filed_cik_value in dei["entity_cik_values"]:
        try:
            filed_cik = canonical_cik(filed_cik_value)
        except Exception as exc:
            raise AdmittedFilingPackageError(
                "dei EntityCentralIndexKey is not a canonical identity",
                code="identity_mismatch",
            ) from exc
        if filed_cik != cik10:
            _refuse(
                "dei EntityCentralIndexKey is not bound to the package CIK",
                code="identity_mismatch",
            )

    unadmitted = _unadmitted_namespaces(parsed, extension_namespace=extension_ns)
    evidence = _parse_evidence(parsed, unadmitted)

    admitted_manifest: dict[str, Any] = dict(manifest)
    admitted_manifest["schema"] = ADMITTED_FILING_PACKAGE_SCHEMA
    admitted_manifest["capture_basis"] = capture_basis
    admitted_manifest["capture_recorded_at"] = capture_recorded_at
    # convert_parsed_filing reads this incumbent field name; bind it to the
    # capture clock so the two clocks never collapse on the wire.
    admitted_manifest["fixture_recorded_at"] = capture_recorded_at
    admitted_manifest["attested"] = False
    admitted_manifest["source_accepted_at"] = manifest["source_accepted_at"]
    # D3-F5: as-filed identity, from the primary document's own dei facts on
    # the source_accepted_at clock. Never the caller's legal_name (a
    # current-master label that stays a separate passthrough) and never a
    # current issuer, security, or statement master.
    registrant_name = dei["registrant_name_as_filed"]
    admitted_manifest["issuer_identity_as_of"] = {
        "cik": cik10,
        "registrant_name_as_filed": registrant_name,
        "name_basis": "primary_document_dei" if registrant_name is not None else "absent_in_filing",
        "as_of_clock": "source_accepted_at",
        "as_of": manifest["source_accepted_at"],
    }

    return AdmittedFilingPackage(
        manifest=admitted_manifest,
        members=stored,
        parse_evidence=evidence,
    )


def primary_of_manifest(manifest: Mapping[str, Any]) -> Any:
    return manifest.get("primary_document")


def _admit_absent_members(
    manifest: Mapping[str, Any],
    *,
    index_names: Sequence[str],
    form: str,
    stored_roles: set[str],
    primary_name: Any,
) -> None:
    """R2/R7: verify ``absent_members`` against the digest-bound index.

    Refuses ``inventory_mismatch`` on any of: an optional role for the form
    that is neither stored nor recorded (silence); an entry for a stored role
    or a required role; ``absent_members`` present on any non-8-K form; an
    empty list; a duplicate entry; an unknown reason; an entry whose name IS
    among the index item names; an entry whose name is not
    ``<primary stem><suffix>`` for its role; or an entry whose role is not
    optional for the form.
    """
    absent = manifest.get("absent_members")
    optional_roles = _FORM_OPTIONAL_STORED_ROLES.get(form, ())
    if absent is None:
        # Silence: an optional role that is neither stored nor recorded.
        for role in optional_roles:
            if role not in stored_roles:
                _refuse(
                    f"optional role is neither stored nor recorded absent: {role}",
                    code="inventory_mismatch",
                )
        return
    if not optional_roles:
        # absent_members on any non-8-K form (including every amendment form).
        _refuse(
            f"absent_members are not lawful for form {form!r}",
            code="inventory_mismatch",
        )
    if not isinstance(absent, list) or not absent:
        _refuse("absent_members must be a non-empty list", code="inventory_mismatch")
    seen: set[tuple[str, str]] = set()
    index_set = set(index_names)
    stem = (
        str(primary_name).rsplit(".", 1)[0]
        if isinstance(primary_name, str) and primary_name
        else ""
    )
    for entry in absent:
        if not isinstance(entry, Mapping) or set(entry) != _ABSENT_MEMBER_KEYS:
            _refuse("absent member entry is malformed", code="inventory_mismatch")
        role = entry.get("role")
        name = entry.get("name")
        if (str(role), str(name)) in seen:
            _refuse(f"duplicate absent member entry: {name}", code="inventory_mismatch")
        seen.add((str(role), str(name)))
        if entry.get("reason") != _ABSENT_MEMBER_REASON:
            _refuse(f"absent member reason is unknown: {name}", code="inventory_mismatch")
        if role not in optional_roles:
            _refuse(
                f"absent member role is not optional for the form: {name}",
                code="inventory_mismatch",
            )
        suffix = _OPTIONAL_ROLE_SUFFIX.get(str(role))
        if not isinstance(name, str) or not suffix or name != f"{stem}{suffix}":
            _refuse(
                f"absent member name is not the primary stem's member: {name}",
                code="inventory_mismatch",
            )
        if name in index_set:
            _refuse(
                f"absent member is named by the archive index: {name}",
                code="inventory_mismatch",
            )
        if role in stored_roles:
            _refuse(
                f"absent member is recorded for a stored role: {name}",
                code="inventory_mismatch",
            )


__all__ = [
    "ADMITTED_FILING_PACKAGE_SCHEMA",
    "AdmittedFilingPackage",
    "AdmittedFilingPackageError",
    "FORM_REQUIRED_STORED_ROLES",
    "REQUIRED_STORED_ROLES",
    "admit_retained_filing_package",
]
