"""XG identity registry v1: lifecycle as a document, validated fail-closed.

Persona rows (``persona.py``) are voice; this file adds the second plane —
provisioning, binding, state. The registry is a separate YAML document so a new
key on a persona row cannot smuggle identity in (``Persona(**yaml.safe_load)``
is a kwargs splat and would refuse it anyway).

Design decisions (final, card t_da720ee4):

- **Fail-closed.** An unknown ``schema_version`` is exactly ONE refusal and no
  field validation runs — an unparseable registry must never half-validate.
  Strict keys everywhere: unknown top-level/entry/binding keys refuse.
- **List-of-strings refusals**, house style (``validators.py``): every failure
  is a human-readable string; empty list means pass. No exceptions except the
  one TypeError guard for wrong argument types.
- **Lock as the mutation check.** ``check_lock`` requires an exact complete
  snapshot. ``check_relock`` checks the prior snapshot before replacement,
  including revisions, immutable attribution and legal transitions.
  ``write_lock`` is the only formatter; the existing CLI writes its result.
- **Launch is a read.** ``launchable`` never mutates the document; a refused
  launch writes nothing.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit

import yaml

SCHEMA_VERSION = 1
STATES = ("proposed", "admitted", "suspended", "retired")
BIO_LINK_POLICIES = ("none", "single_canonical")
CHILD_ID_RE = re.compile(r"^[a-z0-9]{4,32}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
# "host:alias" — host must be a declared mail domain, alias is free.
MAILBOX_RE = re.compile(r"^[^:\s]+:[^:\s]+$")

TOP_KEYS = frozenset({
    "schema_version", "registry_revision", "mail_domains", "domains", "entries",
})
ENTRY_KEYS = frozenset({
    "handle", "child_id", "state", "revision", "domain", "recovery_owner",
    "bio_link_policy", "binding", "admission_receipt", "drift_observed_at",
    "drift_evidence_ref", "suspended_by", "retired_from",
})
BINDING_KEYS = frozenset({
    "email_mailbox", "proxy_slot", "cdp_port", "totp_custodian",
})
RECEIPT_KEYS = frozenset({"path", "sha256"})

CREDENTIAL_KEY_RE = re.compile(r"password|secret|token|seed", re.IGNORECASE)
BASE64ISH_RE = re.compile(r"^[A-Za-z0-9+/]{32,}={0,2}$")

COSTED_STATES = frozenset({"admitted", "suspended"})


def _refuse_type(name: str, value: Any, expected: str) -> list[str]:
    raise TypeError(f"{name} must be {expected}, got {type(value).__name__}")


def canonical_sha(mapping: Mapping, drop: tuple[str, ...] = ()) -> str:
    """sha256 of the mapping minus ``drop`` keys, canonical JSON, sorted keys."""
    payload = {k: v for k, v in mapping.items() if k not in drop}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


# ---------------------------------------------------------------- loading


def _load_yaml(path: str, kind: str) -> tuple[Any, list[str]]:
    try:
        with open(path) as fh:
            doc = yaml.safe_load(fh)
    except FileNotFoundError:
        return None, [f"{kind} file not found: {path}"]
    except yaml.YAMLError as exc:
        return None, [f"{kind} file is not parseable YAML: {path}: {exc}"]
    except OSError as exc:
        return None, [f"{kind} file is unreadable: {path}: {exc}"]
    if not isinstance(doc, dict):
        return None, [f"{kind} file must be a mapping of keys, got "
                      f"{type(doc).__name__}: {path}"]
    return doc, []


def load_registry(path: str) -> tuple[dict | None, list[str]]:
    """Load a registry document; ``(doc, [])`` or ``(None, refusals)``."""
    return _load_yaml(path, "registry")


def load_lock(path: str) -> tuple[dict | None, list[str]]:
    """Load a lock document; ``(lock, [])`` or ``(None, refusals)``."""
    return _load_yaml(path, "lock")


# ------------------------------------------------------------ validation


def _validate_receipt(where: str, value: Any, errors: list[str]) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        errors.append(f"{where} must be a mapping {{path, sha256}} or null")
        return
    extra = sorted(set(value) - RECEIPT_KEYS, key=repr)
    missing = sorted(RECEIPT_KEYS - set(value))
    for key in extra:
        errors.append(f"{where} has unknown key: {key!r}")
    for key in missing:
        errors.append(f"{where} is missing required key: {key!r}")
    path = value.get("path")
    if not (isinstance(path, str) and path.strip()):
        errors.append(f"{where}.path must be a non-empty string")
    sha = value.get("sha256")
    if not (isinstance(sha, str) and SHA256_RE.fullmatch(sha)):
        errors.append(f"{where}.sha256 must be 64 lowercase hex characters")


def _validate_credentials(doc: Any, where: str, errors: list[str]) -> None:
    """No credentials anywhere — the repo carries keys and paths, never material.

    The exception is a receipt ``sha256`` digest: it is the required evidence
    itself (and pure hex is a subset of the base64 alphabet), so it is not
    treated as credential material.
    """
    if isinstance(doc, dict):
        for key, value in doc.items():
            if isinstance(key, str):
                sub = f"{where}.{key}"
                if CREDENTIAL_KEY_RE.search(key):
                    errors.append(
                        f"credential-like key name at {where}: {key!r} "
                        "— the registry carries keys, never material")
                if key == "sha256":
                    continue
            else:
                sub = where
            _validate_credentials(value, sub, errors)
    elif isinstance(doc, list):
        for i, value in enumerate(doc):
            _validate_credentials(value, f"{where}[{i}]", errors)
    elif isinstance(doc, str):
        if "://" in doc:
            try:
                parsed = urlsplit(doc)
            except ValueError:
                errors.append(f"malformed URL at {where}")
                return
            if parsed.username is not None or parsed.password is not None:
                errors.append(f"credential-like URL with userinfo at {where} "
                              "— the registry carries keys, never material")
        elif BASE64ISH_RE.match(doc):
            errors.append(f"credential-like base64-looking value at {where} "
                          "(32+ base64 chars) — the registry carries keys, "
                          "never material")


def validate_document(doc: dict) -> list[str]:
    """Schema plus intra-document rules; ``[]`` means the document parses and holds."""
    if not isinstance(doc, dict):
        _refuse_type("doc", doc, "dict")
    version = doc.get("schema_version")
    if type(version) is not int or version != SCHEMA_VERSION:
        return [f"unknown schema_version {version!r}: this validator only knows "
                f"{SCHEMA_VERSION!r}; refusing to parse the rest of the document"]

    errors: list[str] = []
    for key in sorted(set(doc) - TOP_KEYS, key=repr):
        errors.append(f"unknown top-level key: {key!r}")

    revision = doc.get("registry_revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        errors.append(f"registry_revision must be an int >= 1, got {revision!r}")

    mail_domains = doc.get("mail_domains")
    if not isinstance(mail_domains, list):
        errors.append(f"mail_domains must be a list, got {type(mail_domains).__name__}")
        mail_domains = []
    else:
        for host in mail_domains:
            if not (isinstance(host, str) and host.strip()):
                errors.append(f"mail_domains entry must be a non-empty string, got {host!r}")

    domains = doc.get("domains")
    if not isinstance(domains, list):
        errors.append(f"domains must be a list, got {type(domains).__name__}")
        domains = []
    domain_records: dict[str, dict] = {}
    for rec in domains:
        if not isinstance(rec, dict):
            errors.append(f"domain record must be a mapping, got {type(rec).__name__}")
            continue
        extra = sorted(set(rec) - {"domain", "state", "recovery_owner",
                                   "bio_link_policy", "admission_receipt"}, key=repr)
        for key in extra:
            errors.append(f"unknown key in domain record: {key!r}")
        host = rec.get("domain")
        if not (isinstance(host, str) and host == host.lower() and
                "/" not in host and host.strip()):
            errors.append(f"domain record must carry a lowercase exact host, got {host!r}")
            continue
        if host in domain_records:
            errors.append(f"duplicate domain record: {host!r}")
        domain_records[host] = rec
        state = rec.get("state")
        if state not in STATES:
            errors.append(f"domain {host!r} state {state!r} is not one of "
                          f"{', '.join(STATES)}")
        owner = rec.get("recovery_owner")
        if not (isinstance(owner, str) and owner.strip()):
            errors.append(f"domain {host!r} recovery_owner must be a non-empty "
                          "string (who recovers DNS; never a credential)")
        policy = rec.get("bio_link_policy")
        if policy not in BIO_LINK_POLICIES:
            errors.append(f"domain {host!r} bio_link_policy {policy!r} is not "
                          f"one of {', '.join(BIO_LINK_POLICIES)}")
        if state == "admitted" and rec.get("admission_receipt") is None:
            errors.append(f"domain {host!r} is admitted without an admission_receipt")
        _validate_receipt(f"domain {host!r} admission_receipt",
                          rec.get("admission_receipt"), errors)

    allowed_mail = [h for h in mail_domains if isinstance(h, str)]

    entries = doc.get("entries")
    if not isinstance(entries, list):
        errors.append(f"entries must be a list, got {type(entries).__name__}")
        cred = []
        _validate_credentials(doc, "registry", cred)
        return errors + cred
    if not entries:
        errors.append("entries is empty — the registry needs at least one entry")

    seen_handles: set[str] = set()
    seen_child_ids: set[str] = set()
    seen_ports: dict[int, str] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append(f"entry must be a mapping, got {type(entry).__name__}")
            continue
        _validate_entry(entry, domain_records, allowed_mail,
                        seen_handles, seen_child_ids, seen_ports, errors)
    _check_cdp_uniqueness(entries, errors)
    _check_retired_from(entries, errors)
    cred: list[str] = []
    _validate_credentials(doc, "registry", cred)
    return errors + cred


def _validate_entry(entry: dict, domain_records: dict, allowed_mail: list,
                    seen_handles: set, seen_child_ids: set,
                    seen_ports: dict, errors: list[str]) -> None:
    handle = entry.get("handle")
    if not (isinstance(handle, str) and handle.strip()):
        errors.append(f"entry {entry!r} has no usable handle (join key to a "
                      "persona file); refusing to process it further")
        return
    where = f"entry {handle!r}"
    for key in sorted(set(entry) - ENTRY_KEYS, key=repr):
        errors.append(f"{where} has unknown key: {key!r}")

    state = entry.get("state")
    if state not in STATES:
        errors.append(f"{where} state {state!r} is not one of {', '.join(STATES)}")

    revision = entry.get("revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        errors.append(f"{where} revision must be an int >= 1, got {revision!r}")

    child_id = entry.get("child_id")
    if not (isinstance(child_id, str) and CHILD_ID_RE.fullmatch(child_id)):
        errors.append(f"{where} child_id {child_id!r} must match "
                      f"{CHILD_ID_RE.pattern} (immutable attribution key)")
    elif child_id in seen_child_ids:
        errors.append(f"{where} child_id {child_id!r} is already used by another entry")
    else:
        seen_child_ids.add(child_id)

    if handle in seen_handles:
        errors.append(f"duplicate entry for handle {handle!r}")
    else:
        seen_handles.add(handle)

    domain = entry.get("domain")
    domain_known = isinstance(domain, str) and domain in domain_records
    if not domain_known:
        errors.append(f"{where} names domain {domain!r}, which is not declared in "
                      "`domains` — a binding may only point at a declared record")

    owner = entry.get("recovery_owner")
    if not (isinstance(owner, str) and owner.strip()):
        errors.append(f"{where} recovery_owner must be a non-empty string "
                      "(who recovers the identity; never a credential)")

    policy = entry.get("bio_link_policy")
    if policy not in BIO_LINK_POLICIES:
        errors.append(f"{where} bio_link_policy {policy!r} is not one of "
                      f"{', '.join(BIO_LINK_POLICIES)}")
    if policy == "single_canonical" and domain_known:
        if domain_records[domain].get("bio_link_policy") != "single_canonical":
            errors.append(f"{where} bio_link_policy is single_canonical but domain "
                          f"{domain!r} does not allow one")

    binding = entry.get("binding")
    if not isinstance(binding, dict):
        errors.append(f"{where} binding must be a mapping of {{email_mailbox, "
                      f"proxy_slot, cdp_port, totp_custodian}}, got "
                      f"{type(binding).__name__}")
        binding = {}
    for key in sorted(set(binding) - BINDING_KEYS, key=repr):
        errors.append(f"{where} binding has unknown key: {key!r}")
    for key in sorted(BINDING_KEYS - set(binding)):
        errors.append(f"{where} binding is missing required key: {key!r}")

    costed = isinstance(state, str) and state in COSTED_STATES
    # proposed: nothing is provisioned yet; retired: the historic binding may
    # remain as the audit trail (it also leaves cdp uniqueness at retirement).
    unprovisioned = (state == "proposed")
    mailbox = binding.get("email_mailbox")
    if costed:
        if not (isinstance(mailbox, str) and MAILBOX_RE.match(mailbox)):
            errors.append(f"{where} state {state!r} requires a provisioned mailbox "
                          f'"host:alias", got {mailbox!r}')
        elif isinstance(allowed_mail, list) and mailbox and mailbox.split(":", 1)[0] not in allowed_mail:
            if isinstance(mailbox, str) and MAILBOX_RE.match(mailbox):
                host = mailbox.split(":", 1)[0]
                errors.append(f"{where} mailbox host {host!r} is outside the declared "
                              f"mail_domains allowlist {allowed_mail}")
    elif unprovisioned and mailbox is not None:
        errors.append(f"{where} is {state!r} but carries a mailbox {mailbox!r} — "
                      "a binding is provisioned on admission, not before")

    proxy_slot = binding.get("proxy_slot")
    if costed:
        if not (isinstance(proxy_slot, str) and proxy_slot.strip()):
            errors.append(f"{where} state {state!r} requires a credential-store "
                          f"proxy_slot (a key, never a credential), got {proxy_slot!r}")
    elif unprovisioned and proxy_slot is not None:
        errors.append(f"{where} is {state!r} but carries a proxy_slot — "
                      "a slot is bound on admission, not before")

    port = binding.get("cdp_port")
    if costed:
        if not (isinstance(port, int) and not isinstance(port, bool)
                and 1024 <= port <= 65535):
            errors.append(f"{where} state {state!r} requires a cdp_port int in "
                          f"1024..65535 (part of identity), got {port!r}")
    elif unprovisioned and port is not None:
        errors.append(f"{where} is {state!r} but carries a cdp_port — "
                      "a port is bound on admission, not before")

    custodian = binding.get("totp_custodian")
    if costed:
        if not (isinstance(custodian, str) and custodian.strip()):
            errors.append(f"{where} state {state!r} requires a totp_custodian seat id "
                          "(who holds the seed, not the seed), got {custodian!r}")
    elif unprovisioned and custodian is not None:
        errors.append(f"{where} is {state!r} but carries a totp_custodian — "
                      "custody is assigned on admission, not before")

    receipt = entry.get("admission_receipt")
    if state in ("admitted", "suspended"):
        if receipt is None:
            errors.append(f"{where} is {state!r} without an admission_receipt — "
                          "admission is a receipt, not a bare boolean")
        else:
            _validate_receipt(f"{where} admission_receipt", receipt, errors)
    elif receipt is not None:
        errors.append(f"{where} is {state!r} but carries an admission_receipt — "
                      "a receipt exists only once the identity has been admitted")

    drift_keys = ("drift_observed_at", "drift_evidence_ref", "suspended_by")
    if state == "suspended":
        for key in drift_keys:
            if entry.get(key) is None:
                errors.append(f"{where} is suspended but {key} is null — drift "
                              "is the only writer of `suspended` and it leaves evidence")
        iso = entry.get("drift_observed_at")
        if iso is not None:
            try:
                if not isinstance(iso, str) or not re.match(
                        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", iso):
                    raise ValueError("timestamp must be an ISO-8601 string")
                datetime.fromisoformat(iso)
            except ValueError:
                errors.append(f"{where} drift_observed_at {iso!r} is not an ISO-8601 "
                              "timestamp")
        for key in ("drift_evidence_ref", "suspended_by"):
            value = entry.get(key)
            if value is not None and not (isinstance(value, str) and value.strip()):
                errors.append(f"{where} {key} must be a non-empty string")
    else:
        for key in drift_keys:
            if entry.get(key) is not None:
                errors.append(f"{where} is {state!r} but {key} is set — drift "
                              "fields exist only on a suspended entry")

    predecessor = entry.get("retired_from")
    if predecessor is not None:
        if not (isinstance(predecessor, str) and predecessor.strip()):
            errors.append(f"{where} retired_from must be the handle of the "
                          f"predecessor identity or null, got {predecessor!r}")


def _check_retired_from(entries: list, errors: list[str]) -> None:
    by_handle: dict[str, list[dict]] = {}
    for entry in entries:
        if isinstance(entry, dict) and isinstance(entry.get("handle"), str):
            by_handle.setdefault(entry["handle"], []).append(entry)
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("handle"), str):
            # _validate_entry already refused this entry; keep returning refusals.
            continue
        predecessor = entry.get("retired_from")
        if predecessor is None or not isinstance(predecessor, str):
            continue
        others = [e for h in [predecessor] for e in by_handle.get(h, []) if e is not entry]
        if not others:
            errors.append(f"entry {entry['handle']!r} names retired_from "
                          f"{predecessor!r}, which is not another entry in the registry")
        elif not any(e.get("state") == "retired" for e in others):
            errors.append(f"entry {entry['handle']!r} names retired_from "
                          f"{predecessor!r}, which is not itself retired — "
                          "replacement is visible, not silent")


def _check_cdp_uniqueness(entries: list, errors: list[str]) -> None:
    ports: dict[int, list[str]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("state") == "retired":
            continue
        binding = entry.get("binding")
        if not isinstance(binding, dict):
            continue
        port = binding.get("cdp_port")
        if isinstance(port, int) and not isinstance(port, bool):
            ports.setdefault(port, []).append(str(entry.get("handle")))
    for port, handles in sorted(ports.items()):
        if len(handles) > 1:
            errors.append(f"cdp_port {port} is shared by {len(handles)} entries "
                          f"({', '.join(sorted(handles))}) — a port is part of "
                          "identity, two identities on one port is a collision")


def validate_bindings(doc: dict, personas: Mapping[str, Any],
                      credential_slots: Iterable[str]) -> list[str]:
    """Persona↔entry symmetry (both ways) plus resolvable proxy slots.

    Retired entries are exempt from the persona-present requirement (the voice
    is gone, the identity stays auditable), but a persona file for a retired
    handle IS a refusal: behaviour without a registry entry.
    """
    if not isinstance(doc, dict):
        _refuse_type("doc", doc, "dict")
    if not isinstance(personas, Mapping):
        _refuse_type("personas", personas, "a mapping of handle -> persona")
    slots = {str(s) for s in credential_slots}
    errors: list[str] = []

    entries = doc.get("entries")
    if not isinstance(entries, list):
        return [f"entries must be a list, got {type(entries).__name__}"]
    entry_handles: dict[str, str] = {}
    for entry in entries:
        if isinstance(entry, dict) and isinstance(entry.get("handle"), str):
            entry_handles[entry["handle"]] = entry.get("state", "")

    for handle, state in sorted(entry_handles.items()):
        if handle not in personas and state != "retired":
            errors.append(f"registry entry {handle!r} has no persona file — "
                          "identity without voice")
    for handle in sorted(set(personas) - set(entry_handles)):
        errors.append(f"persona file {handle!r} has no registry entry — "
                      "behaviour without identity")
    for handle, state in sorted(entry_handles.items()):
        if state == "retired" and handle in personas:
            errors.append(f"persona file {handle!r} still exists for a retired "
                          "entry — retire the voice with the identity")

    for entry in entries:
        if (not isinstance(entry, dict) or not isinstance(entry.get("state"), str)
                or entry["state"] not in COSTED_STATES):
            continue
        binding = entry.get("binding")
        slot = binding.get("proxy_slot") if isinstance(binding, dict) else None
        if isinstance(slot, str) and slot.strip() and slot not in slots:
            errors.append(f"entry {entry.get('handle')!r} proxy_slot {slot!r} is "
                          "not resolvable in the credential store — the store is "
                          "referenced by key, never inlined")

    return errors


# ------------------------------------------------------------ the lock check


_LEGAL_TRANSITIONS = {
    ("proposed", "admitted"),
    ("admitted", "suspended"),
    ("suspended", "admitted"),
    # any -> retired (retirement is terminal, reached from any state)
    ("proposed", "retired"),
    ("admitted", "retired"),
    ("suspended", "retired"),
}


def _lock_shape_errors(lock: dict) -> list[str]:
    """A malformed prior snapshot is a refusal, never a bootstrap request."""
    version = lock.get("schema_version")
    if type(version) is not int or version != SCHEMA_VERSION:
        return [f"unknown lock schema_version {version!r}; refusing to parse the lock"]
    errors: list[str] = []
    allowed = {"schema_version", "registry_revision", "document_sha256", "entries", "domains"}
    for key in sorted(set(lock) - allowed, key=repr):
        errors.append(f"lock has unknown key: {key!r}")
    revision = lock.get("registry_revision")
    if type(revision) is not int or revision < 1:
        errors.append("lock registry_revision must be an int >= 1")
    digest = lock.get("document_sha256")
    if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
        errors.append("lock document_sha256 must be exactly 64 lowercase hex characters")

    child_ids: set[str] = set()
    for collection in ("entries", "domains"):
        records = lock.get(collection)
        if not isinstance(records, dict):
            errors.append(f"lock {collection} must be a keyed mapping")
            continue
        for key, record in records.items():
            where = f"lock {collection} {key!r}"
            if not isinstance(key, str) or not key.strip() or not isinstance(record, dict):
                errors.append(f"{where} must be a non-empty key and mapping")
                continue
            fields = ({"revision", "state", "sha256", "receipt_sha256", "child_id"}
                      if collection == "entries" else {"state", "sha256"})
            if set(record) != fields:
                errors.append(f"{where} must contain exactly {sorted(fields)!r}")
            if record.get("state") not in STATES:
                errors.append(f"{where} has an invalid state")
            sha = record.get("sha256")
            if not isinstance(sha, str) or not SHA256_RE.fullmatch(sha):
                errors.append(f"{where}.sha256 must be exactly 64 lowercase hex characters")
            if collection == "entries":
                entry_revision = record.get("revision")
                if type(entry_revision) is not int or entry_revision < 1:
                    errors.append(f"{where}.revision must be an int >= 1")
                child = record.get("child_id")
                if not isinstance(child, str) or not CHILD_ID_RE.fullmatch(child):
                    errors.append(f"{where}.child_id must be a valid immutable attribution key")
                elif child in child_ids:
                    errors.append(f"{where}.child_id duplicates another locked identity")
                else:
                    child_ids.add(child)
                receipt = record.get("receipt_sha256")
                if isinstance(record.get("state"), str) and record["state"] in COSTED_STATES:
                    if not isinstance(receipt, str) or not SHA256_RE.fullmatch(receipt):
                        errors.append(f"{where}.receipt_sha256 must pin the admission evidence")
                elif receipt is not None:
                    errors.append(f"{where}.receipt_sha256 must be null outside costed states")
    return errors


def _check_lock(doc: dict, lock: dict, *, prospective: bool) -> list[str]:
    """Shared exact-snapshot and pre-overwrite revision/transition evaluator."""
    if not isinstance(doc, dict):
        _refuse_type("doc", doc, "dict")
    if not isinstance(lock, dict):
        _refuse_type("lock", lock, "dict")
    errors = validate_document(doc)
    if errors:
        return errors
    errors = _lock_shape_errors(lock)
    if errors:
        return errors

    revision = doc["registry_revision"]
    previous_revision = lock["registry_revision"]
    document_sha = canonical_sha(doc)
    # Exact snapshots and reconstructible prior snapshots must agree with every
    # row pin. A no-op or global-only checkpoint cannot launder a corrupt lock.
    prior_document = {**doc, "registry_revision": previous_revision}
    exact_rows = not prospective or canonical_sha(prior_document) == lock["document_sha256"]
    if prospective:
        if revision < previous_revision:
            errors.append("registry_revision went backwards; revisions are monotonic")
        if revision == previous_revision and document_sha != lock["document_sha256"]:
            errors.append("registry_revision drift: document mutated without a global revision bump")
    else:
        if revision != previous_revision:
            errors.append("registry_revision drift: document and lock revisions must agree")
        if document_sha != lock["document_sha256"]:
            errors.append("registry_revision drift: document digest does not match its exact lock snapshot")

    lock_entries = lock.get("entries")
    doc_entries = doc.get("entries")
    if not isinstance(lock_entries, dict) or not isinstance(doc_entries, list):
        if not isinstance(lock_entries, dict):
            errors.append(f"lock entries must be a keyed mapping, got "
                          f"{type(lock_entries).__name__}")
        if not isinstance(doc_entries, list):
            errors.append(f"document entries must be a list, got "
                          f"{type(doc_entries).__name__}")
        return errors

    doc_states: dict[str, dict] = {}
    for entry in doc_entries:
        if isinstance(entry, dict) and isinstance(entry.get("handle"), str):
            doc_states[entry["handle"]] = entry
        else:
            errors.append(f"document entry is not a mapping with a handle: {entry!r}")

    if exact_rows:
        for handle in sorted(set(doc_states) - set(lock_entries)):
            errors.append(f"entry {handle!r} is not in the lock — new identities "
                          "need the re-lock ceremony, not a silent addition")
        for handle in sorted(set(lock_entries) - set(doc_states)):
            errors.append(f"lock entry {handle!r} is not in the document — identities "
                          "are removed by a re-lock, never from the lock alone")

    for handle in sorted(set(doc_states) & set(lock_entries)):
        entry = doc_states[handle]
        locked = lock_entries[handle]
        if not isinstance(locked, dict):
            errors.append(f"lock entry {handle!r} must be a mapping with "
                          f"revision/state/sha256, got {type(locked).__name__}")
            continue
        state = entry.get("state")
        revision = entry.get("revision")
        if not isinstance(revision, int) or isinstance(revision, bool):
            errors.append(f"entry {handle!r} revision {revision!r} is not an int; "
                          "the lock check refuses it")
            continue
        doc_sha = canonical_sha(entry, drop=("revision",))
        lock_sha = locked.get("sha256")
        lock_rev = locked.get("revision")

        if exact_rows and (doc_sha != lock_sha or revision != lock_rev):
            errors.append(f"entry {handle!r} revision/digest does not match its exact lock snapshot")
        if entry["child_id"] != locked["child_id"]:
            errors.append(f"entry {handle!r} child_id is immutable across re-locks")
        if doc_sha == lock_sha:
            receipt = entry.get("admission_receipt")
            receipt_sha = receipt.get("sha256") if isinstance(receipt, dict) else None
            if state != locked["state"] or receipt_sha != locked["receipt_sha256"]:
                errors.append(f"lock entry {handle!r} state/receipt pin contradicts its unchanged digest")


        if doc_sha != lock_sha and revision == lock_rev:
            errors.append(f"entry {handle!r} mutated without a revision bump "
                          "(sha changed, revision stayed) — mutations bump the "
                          "revision and rerun the re-lock ceremony")
        if revision < lock_rev:
            errors.append(f"entry {handle!r} revision went backwards: {revision} "
                          f"< lock revision {lock_rev} — revisions are monotonic")
        if doc_sha == lock_sha and revision != lock_rev:
            errors.append(f"entry {handle!r} bump without mutation (revision "
                          f"{revision} vs lock {lock_rev}, sha unchanged) — a "
                          "forged ceremony")

        lock_state = locked.get("state")
        if (lock_state, state) not in _LEGAL_TRANSITIONS and lock_state != state:
            if ("retired", state) == (lock_state, state) or lock_state == "retired":
                errors.append(f"entry {handle!r} retired is terminal: the lock "
                              f"holds retired and the document claims {state!r}")
            elif state == "proposed" and lock_state == "suspended":
                errors.append(f"entry {handle!r} suspension is sticky: the lock "
                              f"holds suspended and the document went back to "
                              "proposed; re-admission is the only exit")
            else:
                errors.append(f"entry {handle!r} illegal state transition "
                              f"{lock_state!r} -> {state!r}")

        elif (lock_state, state) == ("proposed", "admitted"):
            if entry.get("admission_receipt") is None:
                errors.append(f"entry {handle!r} proposed->admitted without an "
                              "admission_receipt — admission is a receipt, not "
                              "a bare boolean")
        elif (lock_state, state) == ("admitted", "suspended"):
            missing = [k for k in ("drift_observed_at", "drift_evidence_ref",
                                   "suspended_by") if entry.get(k) is None]
            if missing:
                errors.append(f"entry {handle!r} admitted->suspended without "
                              f"{', '.join(missing)} — drift leaves evidence")
        elif (lock_state, state) == ("suspended", "admitted"):
            receipt = entry.get("admission_receipt")
            if receipt is None:
                errors.append(f"entry {handle!r} suspended->admitted (re-admission) "
                              "without an admission_receipt")
            else:
                sha = receipt.get("sha256") if isinstance(receipt, dict) else None
                if sha == locked.get("receipt_sha256"):
                    errors.append(f"entry {handle!r} re-admission reuses the old "
                                  "receipt — re-admission is a NEW event with its "
                                  "own receipt")
    doc_domains = {record["domain"]: record for record in doc["domains"]}
    lock_domains = lock["domains"]
    if exact_rows:
        for host in sorted(set(doc_domains) - set(lock_domains)):
            errors.append(f"domain {host!r} is not in the lock — re-lock required")
        for host in sorted(set(lock_domains) - set(doc_domains)):
            errors.append(f"lock domain {host!r} is not in the document — re-lock required")
    for host in sorted(set(doc_domains) & set(lock_domains)):
        record, locked = doc_domains[host], lock_domains[host]
        unchanged = canonical_sha(record) == locked["sha256"]
        if exact_rows and not unchanged:
            errors.append(f"domain {host!r} digest does not match its exact lock snapshot")
        if (unchanged or exact_rows) and record["state"] != locked["state"]:
            errors.append(f"domain {host!r} state does not match its lock snapshot")
    return errors



def check_lock(doc: dict, lock: dict) -> list[str]:
    """Read-only gate: require the exact complete snapshot, never a prospective edit."""
    return _check_lock(doc, lock, prospective=False)


def check_relock(doc: dict, previous_lock: dict) -> list[str]:
    """Validate an explicit update before the existing CLI writer replaces its lock.

    Membership changes require a global revision advance. No-op re-locks and
    global-only checkpoints remain valid; retained identities keep their own
    revision, attribution and transition laws. This compares the prior snapshot,
    not a permanent identity-history ledger.
    """
    return _check_lock(doc, previous_lock, prospective=True)


def check_revision(doc: dict, expected_revision: int) -> list[str]:
    """Rule 3: the revision the run validated against differs from disk."""
    if not isinstance(doc, dict):
        _refuse_type("doc", doc, "dict")
    if not (isinstance(expected_revision, int) and not isinstance(expected_revision, bool)):
        _refuse_type("expected_revision", expected_revision, "int")
    on_disk = doc.get("registry_revision")
    if on_disk != expected_revision:
        return [f"registry_revision is {on_disk!r} on disk but the last validated "
                f"revision was {expected_revision!r} — a registry edited mid-run "
                "is drift"]
    return []


# ------------------------------------------------------------------ launch


def launchable(doc: dict, handle: str) -> list[str]:
    """``[]`` iff the entry exists and is ``admitted``. A read: never mutates."""
    if not isinstance(doc, dict):
        _refuse_type("doc", doc, "dict")
    if not isinstance(handle, str):
        _refuse_type("handle", handle, "str")
    entries = doc.get("entries")
    entry = None
    for row in entries or []:
        if isinstance(row, dict) and row.get("handle") == handle:
            entry = row
    if entry is None:
        return [f"no registry entry for {handle!r} — an unregistered identity "
                "is not launchable; register it first"]
    state = entry.get("state")
    if state != "admitted":
        return [f"entry {handle!r} is {state!r}, not admitted — launch is gated "
                "on state alone and a refused launch writes nothing"]
    return []


# ----------------------------------------------------------------- content


def links_outside_domain(text: str, entry: dict) -> list[str]:
    """Report, per URL in ``text``, that its host ≠ the entry's declared domain."""
    from . import validators  # local import: registry must not import at module use time

    domain = entry.get("domain")
    errors: list[str] = []
    for link in validators.links_in_text(text or ""):
        host = _link_host(link)
        if host is not None and domain is not None and host != domain:
            errors.append(f"link {link!r} points at {host!r}, outside the declared "
                          f"domain {domain!r}")
    return errors


def _link_host(link: str) -> str | None:
    """Host of a link token, scheme or not.

    ``validators.links_in_text`` also emits scheme-less tokens (``www.*`` and
    bare dotted hosts); those parse as a netloc with ``urlsplit("//" + token)``
    — the same parse the bio gate uses — so leaving the scheme off can no
    longer move a link outside the declared domain without a refusal.
    """
    token = (link or "").strip()
    if not token:
        return None
    parsed = urlsplit(token) if "://" in token else urlsplit("//" + token)
    host = (parsed.hostname or "").lower()
    return host or None


def validate_bio_against_registry(text: str, doc: dict, handle: str, *,
                                  display_name: str = "") -> list[str]:
    """Bio gate for one registry entry: policy, admitted domain, then the bio law."""
    from . import validators

    errors: list[str] = []
    entry = None
    for row in (doc.get("entries") or []):
        if isinstance(row, dict) and row.get("handle") == handle:
            entry = row
    if entry is None:
        return [f"no registry entry for {handle!r} — the bio gate needs the entry "
                "to bind policy and child id"]

    if entry.get("bio_link_policy") == "none":
        for token in validators.links_in_text(text or ""):
            errors.append(f"entry {handle!r} bio_link_policy is none — the bio may "
                          f"carry NO link, but it carries {token!r}")
        child = entry.get("child_id")
        known = {e.get("child_id") for e in doc.get("entries") or []
                 if isinstance(e, dict)}
        return errors + validators.validate_bio(
            text, child_id=child, known_ids=known or None, display_name=display_name)

    domain_record = None
    for rec in doc.get("domains") or []:
        if isinstance(rec, dict) and rec.get("domain") == entry.get("domain"):
            domain_record = rec
    if domain_record is None:
        errors.append(f"entry {handle!r} names domain {entry.get('domain')!r}, "
                      "which is not declared in `domains`")
    elif domain_record.get("state") != "admitted":
        errors.append(f"bio link may not exist unless the domain record is "
                      f"admitted: {entry.get('domain')!r} is "
                      f"{domain_record.get('state')!r}")

    errors.extend(links_outside_domain(text, entry))

    child = entry.get("child_id")
    known_ids = {e.get("child_id") for e in doc.get("entries") or []
                 if isinstance(e, dict)}
    return errors + validators.validate_bio(
        text, child_id=child, known_ids=known_ids or None, display_name=display_name)


# ------------------------------------------------------------------- glue


def validate_all(doc, lock, personas, credential_slots,
                 expected_revision=None) -> list[str]:
    """Everything, in order; a schema_version refusal short-circuits the rest."""
    errors: list[str] = []
    if doc is None:
        errors.append("registry did not load — fix the load refusal first")
    else:
        errors.extend(validate_document(doc))
        if any("refusing to parse" in e for e in errors):
            return errors
    if lock is None:
        # Fail closed: without the lock the mutation-without-bump check cannot
        # run, and "could not check" is never "passed".
        errors.append("no registry lock supplied — the mutation-without-bump "
                      "check cannot run; refusing (fail-closed). Run the "
                      "re-lock ceremony (registry-lock) and pass --lock")
    else:
        errors.extend(error for error in check_lock(doc, lock) if error not in errors)
    if personas is not None:
        errors.extend(validate_bindings(doc, personas, credential_slots))
    if expected_revision is not None:
        errors.extend(check_revision(doc, expected_revision))
    return errors


def write_lock(doc: dict) -> dict:
    """The lock mapping for ``doc`` (pure). The CLI writes it; nothing else does."""
    if not isinstance(doc, dict):
        _refuse_type("doc", doc, "dict")
    lock: dict[str, Any] = {
        "schema_version": doc.get("schema_version"),
        "registry_revision": doc.get("registry_revision"),
        "document_sha256": canonical_sha(doc),
        "entries": {},
        "domains": {},
    }
    for entry in doc.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        handle = entry.get("handle")
        if not isinstance(handle, str):
            continue
        receipt = entry.get("admission_receipt")
        lock["entries"][handle] = {
            "child_id": entry.get("child_id"),
            "revision": entry.get("revision"),
            "state": entry.get("state"),
            "sha256": canonical_sha(entry, drop=("revision",)),
            "receipt_sha256": receipt.get("sha256")
            if isinstance(receipt, dict) else None,
        }
    for rec in doc.get("domains") or []:
        if isinstance(rec, dict) and isinstance(rec.get("domain"), str):
            lock["domains"][rec["domain"]] = {
                "state": rec.get("state"),
                "sha256": canonical_sha(rec),
            }
    return lock
