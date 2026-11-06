"""Exclusive synthetic staging accounting; inert receipts, zero production authority.

The trusted assigning root supplies the test commission, the frozen expected
generation set and the emitted scientific configurations. This module stages
the FULL good/control-refusal set into one fixed preexisting per-commission staging file
BEFORE any driver or transport call, using the existing ``TrialLedger`` as the
only accounting engine. ``run_id`` is receipt/request identity only: it never
selects a path, and a candidate or run rename cannot reset the commissioned
original family history.

Guarantees are deliberately bounded. Agreement of hashes, descriptors and
counts is a comparison against caller-supplied trusted inputs; it never
authenticates a caller, proves unseen history completeness, establishes
singleton custody, or proves durability beyond the observed fsync ordering
recorded in the two observation bindings. All activation flags stay false and
``assess_accounting_references`` stays ``STRUCTURALLY_COMPLETE_DISABLED`` /
``UNQUALIFIED`` for production. The incumbent shared owner transaction coordinates participating source
callers; it cannot fence uncooperative external writers or authenticate history.

Refusals raise ``StagingAccountingRefused`` with one bounded fixed code. An
uncertain append (fsync/readback failure) preserves already-confirmed rows on
disk, refuses any usable readback, and is reconciled by a retry of the SAME
original identity -- never by deletion, reset or a fresh pathname.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat

from engine.trial_ledger import TrialLedger, _hash as _incumbent_hash
from . import accounting_contract, contracts
from .bridge import BoundBytes, SyntheticTestCommission
from .input_contract import parse_timestamp

__all__ = [
    "StagingAccountingRefused",
    "ScientificConfigBinding",
    "StagedAccountingReadback",
    "stage_synthetic_generation",
    "LEDGER_BASENAME",
]

LEDGER_BASENAME = "trial_ledger.jsonl"
MAX_SNAPSHOT_BYTES = contracts.MAX_BYTES
_MAX_RUN_ID_CHARS = 128
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SHORT_HASH = re.compile(r"[0-9a-f]{16}\Z")
_OPAQUE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_ROW_SOURCE = "staging_synthetic_generation"
_DECLARED_REASON = "staging_accounting:declared_original_ceiling"
_GENERATED_ROW_KEYS = frozenset({
    "ts", "family", "config_hash", "config", "source", "info_cutoff", "note",
})
_DECLARED_ROW_KEYS = frozenset({
    "ts", "family", "kind", "n", "reason", "config_hash",
})
_CONFIG_KEYS = frozenset({
    "source_sha256", "parameters", "information_set_sha256", "horizon_id",
    "objective_id",
})
_EXPECTED_KEYS = frozenset({
    "schema", "original_root_id", "family", "protocol_sha256",
    "history_anchor_sha256", "variants", "inherited_variants",
    "trial_ceiling", "vault_required", "vault_request",
})
_WRITER_KEYS = frozenset({
    "schema", "original_root_id", "family", "run_id", "ledger_basename",
    "authority", "scope", "staging_dev", "staging_ino", "ledger_dev",
    "ledger_ino", "ledger_mode", "ledger_hardlinks", "bytes_before",
    "bytes_after", "sha256_before", "sha256_after", "appended_bytes",
    "config_rows_appended", "declared_rows_appended", "observed_order",
    "uncertainty",
})
_DURABLE_KEYS = frozenset({
    "schema", "original_root_id", "family", "run_id", "ledger_basename",
    "authority", "scope", "ledger_dev", "ledger_ino", "file_fsync_observed",
    "directory_fsync_observed", "cold_readback_observed", "snapshot_sha256",
    "snapshot_bytes", "history_state", "load_error", "corrupt_lines",
    "literal_n", "declared_floor", "effective_n", "uncertainty",
    "durability_state", "original_prefix_bytes", "original_prefix_head_sha256",
})
_TRIAL_SCHEMA = "research_codegen.trial_readback_reference.v1"
_WRITER_SCHEMA = "research_codegen.staging_writer_observation.v1"
_DURABLE_SCHEMA = "research_codegen.staging_durable_readback_observation.v1"



class StagingAccountingRefused(ValueError):
    """Closed staging refusal; confirmed rows persist, no usable readback."""


@dataclass(frozen=True)
class ScientificConfigBinding:
    """One emitted scientific choice: exact bounded config bound to bytes."""
    variant_id: str
    source_sha256: str
    config: BoundBytes


@dataclass(frozen=True)
class StagedAccountingReadback:
    """Exact frozen staging receipt; observation hashes fill receipt fields."""
    expected_generation: BoundBytes
    trial_readback: BoundBytes
    raw_snapshot: BoundBytes
    writer_observation: BoundBytes
    durable_readback_observation: BoundBytes
    newly_recorded_count: int


def _require(condition, code):
    if not condition:
        raise StagingAccountingRefused(code)


def _pairs(rows):
    result = {}
    for key, value in rows:
        _require(type(key) is str and key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _canonical(value):
    return json.dumps(value, allow_nan=False, ensure_ascii=True,
                      sort_keys=True, separators=(",", ":"))


def _bound(value, label):
    _require(type(value) is BoundBytes, label + "_BYTES_REQUIRED")
    _require(type(value.raw) is bytes and 0 < len(value.raw) <= MAX_SNAPSHOT_BYTES
             and type(value.size) is int and value.size == len(value.raw)
             and type(value.sha256) is str
             and _SHA256.fullmatch(value.sha256) is not None,
             label + "_BYTE_BINDING_INVALID")
    _require(hashlib.sha256(value.raw).hexdigest() == value.sha256,
             label + "_DIGEST_MISMATCH")
    return value


def _load_bound_json(value, label):
    raw = _bound(value, label).raw
    try:
        doc = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                         parse_constant=lambda _: (_ for _ in ()).throw(
                             StagingAccountingRefused(label + "_NONFINITE_JSON")))
    except StagingAccountingRefused:
        raise
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise StagingAccountingRefused(label + "_INVALID_JSON") from exc
    _require(contracts.is_exact_json(doc), label + "_UNBOUNDED_JSON")
    return doc


def _exact_int(value, minimum=0, maximum=accounting_contract.MAX_COUNT):
    return type(value) is int and minimum <= value <= maximum


def _descriptors(rows, label):
    errors: list[str] = []
    mapping = accounting_contract._variants(rows, label, errors)
    _require(not errors, label + "_DESCRIPTOR_INVALID")
    return mapping


def _validate_expected(doc, commission):
    """Closed frozen-spec validation before any write; returns bounded parts."""
    _require(type(doc) is dict and set(doc) == set(_EXPECTED_KEYS),
             "EXPECTED_SCHEMA_INVALID")
    _require(doc["schema"] == "research_codegen.expected_generation.v1",
             "EXPECTED_SCHEMA_INVALID")
    _require(contracts._opaque_id(doc["original_root_id"])
             and doc["original_root_id"] == commission.original_root_id,
             "COMMISSION_IDENTITY_MISMATCH")
    family = doc["family"]
    _require(contracts._family(family), "EXPECTED_FAMILY_INVALID")
    _require(contracts._sha(doc["protocol_sha256"])
             and contracts._sha(doc["history_anchor_sha256"]),
             "EXPECTED_ANCHOR_INVALID")
    _require(_exact_int(doc["trial_ceiling"], 1, accounting_contract.MAX_VARIANTS),
             "EXPECTED_CEILING_INVALID")
    _require(doc["vault_required"] is False and doc["vault_request"] is None,
             "VAULT_MUST_BE_DORMANT")
    emitted = _descriptors(doc["variants"], "EXPECTED_EMITTED")
    inherited = _descriptors(doc["inherited_variants"], "EXPECTED_INHERITED")
    full = _descriptors(doc["inherited_variants"] + doc["variants"],
                        "EXPECTED_FULL")
    _require(bool(emitted), "EXPECTED_EMITTED_EMPTY")
    _require(len(full) == len(emitted) + len(inherited), "EXPECTED_SET_OVERLAP")
    _require(len(full) <= doc["trial_ceiling"], "EXPECTED_CEILING_EXCEEDED")
    anchor = doc["history_anchor_sha256"]
    return family, doc["protocol_sha256"], doc["trial_ceiling"], anchor, \
        emitted, inherited, full


def _original_prefix(value, expected_sha256):
    """Compare independently supplied original bytes; never manufacture origin."""
    _require(type(value) is BoundBytes and type(value.raw) is bytes
             and len(value.raw) <= MAX_SNAPSHOT_BYTES
             and type(value.size) is int and value.size == len(value.raw)
             and contracts._sha(value.sha256)
             and hashlib.sha256(value.raw).hexdigest() == value.sha256
             and value.sha256 == expected_sha256, "ORIGINAL_ANCHOR_INVALID")
    _require(not value.raw or value.raw.endswith(b"\n"), "ORIGINAL_ANCHOR_TORN")
    return value.raw


def _utc_timestamp(value):
    _require(type(value) is str and len(value) <= 64, "HISTORY_TIMESTAMP_INVALID")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        _require(parsed.tzinfo is not None and parsed.utcoffset() == timezone.utc.utcoffset(parsed),
                 "HISTORY_TIMESTAMP_INVALID")
    except (ValueError, OverflowError) as exc:
        raise StagingAccountingRefused("HISTORY_TIMESTAMP_INVALID") from exc


def _scientific_doc(binding, family, emitted):
    """Recompute the strong and incumbent hashes through the accepted contracts."""
    _require(type(binding) is ScientificConfigBinding, "CONFIG_BINDING_INVALID")
    _require(type(binding.variant_id) is str
             and _OPAQUE_ID.fullmatch(binding.variant_id) is not None
             and type(binding.source_sha256) is str
             and _SHA256.fullmatch(binding.source_sha256) is not None,
             "CONFIG_BINDING_INVALID")
    doc = _load_bound_json(binding.config, "CONFIG")
    _require(type(doc) is dict and set(doc) == set(_CONFIG_KEYS),
             "SCIENTIFIC_CONFIG_INVALID")
    _require(contracts.is_exact_json(doc["parameters"])
             and contracts._sha(doc["source_sha256"])
             and contracts._sha(doc["information_set_sha256"])
             and contracts._opaque_id(doc["horizon_id"])
             and contracts._opaque_id(doc["objective_id"]),
             "SCIENTIFIC_CONFIG_INVALID")
    identity = emitted.get(binding.variant_id) if emitted else None
    _require(identity is not None
             and binding.source_sha256 == identity[0]
             and binding.source_sha256 == doc["source_sha256"],
             "CONFIG_DESCRIPTOR_MISMATCH")
    _require(identity[1] == contracts.canonical_json_sha256(doc)
             and identity[2] == _incumbent_hash(family, doc),
             "CONFIG_DESCRIPTOR_MISMATCH")
    return doc


def _resolve_staging(commission):
    """Bind the commission to one existing exclusive non-canonical directory."""
    _require(type(commission) is SyntheticTestCommission,
             "EXACT_COMMISSION_REQUIRED")
    _require(contracts._opaque_id(commission.original_root_id)
             and type(commission.staging_root) is str
             and commission.staging_root and os.path.isabs(commission.staging_root),
             "INVALID_STAGING_ROOT")
    try:
        st = os.lstat(commission.staging_root)
    except OSError as exc:
        raise StagingAccountingRefused("INVALID_STAGING_ROOT") from exc
    _require(stat.S_ISDIR(st.st_mode) and not stat.S_ISLNK(st.st_mode),
             "INVALID_STAGING_ROOT")
    resolved = Path(os.path.abspath(commission.staging_root))
    _require(resolved.resolve(strict=True) == resolved, "SYMLINKED_STAGING_ROOT")
    _require(resolved != resolved.parent, "CANONICAL_PATH_ALIAS")
    module_pkg = Path(__file__).resolve().parent
    protected = [module_pkg, module_pkg.parent, module_pkg.parent.parent,
                 Path(os.path.abspath("data"))]
    for guarded in protected:
        if resolved == guarded or resolved in guarded.parents \
                or guarded in resolved.parents:
            raise StagingAccountingRefused("CANONICAL_PATH_ALIAS")
    return resolved


def _dir_fsync(directory):
    try:
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError as exc:
        raise StagingAccountingRefused("DIRECTORY_FSYNC_UNSETTLED") from exc


def _read_snapshot(path):
    try:
        return _read_snapshot_checked(path)
    except OSError as exc:
        raise StagingAccountingRefused("SNAPSHOT_UNREADABLE") from exc


def _read_snapshot_checked(path):
    """Bounded no-follow read with descriptor identity rechecked around it."""
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        return None, None
    except OSError as exc:
        raise StagingAccountingRefused("SNAPSHOT_UNREADABLE") from exc
    _require(stat.S_ISREG(st.st_mode) and not stat.S_ISLNK(st.st_mode),
             "SNAPSHOT_NOT_REGULAR")
    _require(st.st_nlink == 1, "SNAPSHOT_HARDLINKED")
    _require(st.st_size <= MAX_SNAPSHOT_BYTES, "SNAPSHOT_UNBOUNDED")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        opened = os.fstat(fd)
        _require((opened.st_dev, opened.st_ino, opened.st_mode, opened.st_nlink,
                  opened.st_size) == (st.st_dev, st.st_ino, st.st_mode,
                                      st.st_nlink, st.st_size),
                 "PATH_SWAPPED_DURING_READ")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(MAX_SNAPSHOT_BYTES + 1)
        after = os.fstat(fd)
    finally:
        os.close(fd)
    _require(len(raw) == opened.st_size, "SNAPSHOT_UNBOUNDED")
    _require((opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns,
              opened.st_ctime_ns) == (after.st_dev, after.st_ino, after.st_size,
                                      after.st_mtime_ns, after.st_ctime_ns),
             "SNAPSHOT_CHANGED_DURING_READ")
    current = os.lstat(path)
    _require(stat.S_ISREG(current.st_mode) and current.st_nlink == 1
             and (current.st_dev, current.st_ino) == (opened.st_dev, opened.st_ino),
             "PATH_SWAPPED_DURING_READ")
    return raw, opened


def _parse_line(line, family):
    try:
        row = json.loads(line, object_pairs_hook=_pairs,
                         parse_constant=lambda _: (_ for _ in ()).throw(
                             StagingAccountingRefused("HISTORY_NONFINITE_JSON")))
    except StagingAccountingRefused:
        raise
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise StagingAccountingRefused("HISTORY_PARSE_REFUSED") from exc
    if type(row) is not dict:
        raise StagingAccountingRefused("HISTORY_ROW_INVALID")
    _utc_timestamp(row.get("ts"))
    if row.get("kind") is not None:
        _require(set(row) == set(_DECLARED_ROW_KEYS)
                 and row["kind"] == "declared_budget", "HISTORY_ROW_INVALID")
        _require(row["family"] == family, "WRONG_FAMILY_HISTORY")
        _require(_exact_int(row["n"], 1), "HISTORY_ROW_INVALID")
        _require(type(row["reason"]) is str and 0 < len(row["reason"]) <= 256,
                 "HISTORY_ROW_INVALID")
        _require(type(row["config_hash"]) is str
                 and _SHORT_HASH.fullmatch(row["config_hash"]) is not None,
                 "HISTORY_ROW_INVALID")
        _require(row["config_hash"] == _incumbent_hash(
            family, {"__declared_budget__": row["n"], "reason": row["reason"]}),
            "CONFIG_DIGEST_MISMATCH")
        return row["n"], None
    _require(set(row) == set(_GENERATED_ROW_KEYS), "HISTORY_ROW_INVALID")
    _require(row["family"] == family, "WRONG_FAMILY_HISTORY")
    try:
        parse_timestamp(row["ts"])
    except ValueError as exc:
        raise StagingAccountingRefused("HISTORY_TIMESTAMP_INVALID") from exc
    _require(type(row["config_hash"]) is str
             and _SHORT_HASH.fullmatch(row["config_hash"]) is not None,
             "HISTORY_ROW_INVALID")
    _require(contracts.is_exact_json(row["config"]), "HISTORY_ROW_INVALID")
    _require(row["source"] == _ROW_SOURCE and row["info_cutoff"] is None
             and row["note"] is None, "HISTORY_ROW_INVALID")
    _require(row["config_hash"] == _incumbent_hash(family, row["config"]),
             "CONFIG_DIGEST_MISMATCH")
    return None, row


def _strict_replay(raw, family, full):
    """Parse the FULL bounded snapshot; never trust cached or declared counts."""
    _require(type(raw) is bytes and len(raw) <= MAX_SNAPSHOT_BYTES, "SNAPSHOT_UNBOUNDED")
    _require(not raw or raw.endswith(b"\n"), "HISTORY_TORN")
    identities = {identity[2]: identity for identity in full.values()}
    present: dict[str, str] = {}
    declared_max = 0
    if raw:
        try:
            text = raw.decode("utf-8")
        except UnicodeError as exc:
            raise StagingAccountingRefused("HISTORY_PARSE_REFUSED") from exc
        for line in text.split("\n"):
            if not line.strip():
                continue
            declared_n, generated = _parse_line(line, family)
            if generated is None:
                declared_max = max(declared_max, declared_n)
                continue
            config_hash = generated["config_hash"]
            encoded = _canonical(generated["config"])
            _require(config_hash not in present, "DUPLICATE_HISTORY_ROW")
            _require(config_hash in identities, "UNKNOWN_HISTORY_ROW")
            identity = identities[config_hash]
            doc = generated["config"]
            _require(type(doc) is dict and set(doc) == set(_CONFIG_KEYS)
                     and doc["source_sha256"] == identity[0]
                     and contracts.canonical_json_sha256(doc) == identity[1],
                     "STRONG_HISTORY_IDENTITY_MISMATCH")
            present[config_hash] = encoded
    return present, declared_max


def _variant_for_hash(full, config_hash):
    for variant_id, identity in full.items():
        if identity[2] == config_hash:
            return variant_id
    raise StagingAccountingRefused("UNKNOWN_HISTORY_ROW")


def _bound_bytes(doc):
    raw = _canonical(doc).encode("utf-8")
    return BoundBytes(raw=raw, sha256=hashlib.sha256(raw).hexdigest(),
                      size=len(raw))


def stage_synthetic_generation(*, commission, run_id, expected_generation,
                               configurations, history_anchor) -> StagedAccountingReadback:
    """Stage the full emitted set under one exclusive lock, then read back cold.

    The commission binds the root to an existing exclusive staging directory
    outside canonical data. The caller exclusively initializes and durably
    records its new invented original history before supplying the independent
    raw-prefix anchor. This mutation API never creates or resets history.
    Exactly one fixed ``trial_ledger.jsonl`` basename
    carries this commissioned original history; ``run_id`` never selects a
    path. Refusals are closed; an unsettled append keeps confirmed rows and
    returns nothing usable, and the SAME original identity reconciles it.
    """
    _require(type(run_id) is str and len(run_id) <= _MAX_RUN_ID_CHARS
             and _RUN_ID.fullmatch(run_id) is not None, "INVALID_RUN_ID")
    _require(type(configurations) is tuple
             and len(configurations) <= accounting_contract.MAX_VARIANTS,
             "CONFIG_COLLECTION_INVALID")
    staging = _resolve_staging(commission)
    expected_doc = _load_bound_json(expected_generation, "EXPECTED")
    family, protocol_sha256, ceiling, anchor, emitted, inherited, full = \
        _validate_expected(expected_doc, commission)
    provided: dict[str, object] = {}
    for binding in configurations:
        _require(type(binding) is ScientificConfigBinding,
                 "CONFIG_BINDING_INVALID")
        doc = _scientific_doc(binding, family, emitted)
        _require(binding.variant_id not in provided, "DUPLICATE_CONFIG_BINDING")
        provided[binding.variant_id] = doc
    _require(set(provided) == set(emitted), "CONFIG_MAP_INCOMPLETE")
    emitted_hashes = {identity[2] for identity in emitted.values()}
    inherited_hashes = {identity[2] for identity in inherited.values()}

    prefix = _original_prefix(history_anchor, anchor)
    ledger_path = staging / LEDGER_BASENAME
    staging_stat = os.lstat(staging)
    # Initial creation belongs to the explicit fixture owner before this API.
    # Missing files never become a new original history, including empty anchor.
    # A full stat/open/read here races a legitimate participating writer before
    # this caller has the incumbent ledger flock. Observe absence only; strict
    # owner_transaction below obtains and validates the real history under lock.
    try:
        os.lstat(ledger_path)
    except FileNotFoundError as exc:
        raise StagingAccountingRefused("ORIGINAL_HISTORY_MISSING") from exc
    except OSError as exc:
        raise StagingAccountingRefused("SNAPSHOT_UNREADABLE") from exc
    _require(hasattr(TrialLedger, "owner_transaction") and hasattr(TrialLedger, "raw_readback"),
             "CORE_OWNER_TRANSACTION_UNAVAILABLE")
    fresh = TrialLedger(path=ledger_path, family=family)
    try:
        with fresh.owner_transaction(strict=True) as owner:
            _require(owner is fresh, "EXACT_INCUMBENT_OWNER_REQUIRED")
            raw_before = owner.raw_readback()
            _require(type(raw_before) is bytes and raw_before.startswith(prefix), "ORIGINAL_ANCHOR_MISMATCH")
            _strict_replay(prefix, family, full)
            raw_check, st_before = _read_snapshot(ledger_path)
            _require(raw_before == raw_check, "SNAPSHOT_CHANGED_DURING_READ")
            present, declared_max = _strict_replay(raw_before, family, full)
            _require(declared_max <= ceiling, "INCONSISTENT_CEILING")
            _require(inherited_hashes <= set(present), "INCOMPLETE_INHERITED_ANCHOR")
            _require(owner.load_error is None and owner.corrupt_lines == 0
                     and owner.literal_n(family) == len(present)
                     and owner.declared_budget(family) == declared_max,
                     "COLD_RECONCILIATION_MISMATCH")
            missing = sorted(emitted_hashes - set(present))
            docs = [provided[_variant_for_hash(full, config_hash)] for config_hash in missing]
            newly_recorded = owner.log_grid(docs, family=family, info_cutoff=None,
                source=_ROW_SOURCE, note=None) if docs else 0
            _require(type(newly_recorded) is int and newly_recorded == len(docs), "READBACK_INCONSISTENT")
            declaration_result = owner.log_declared_budget(ceiling, family=family, reason=_DECLARED_REASON)
            _require(type(declaration_result) is bool, "READBACK_INCONSISTENT")
            declared_appended = int(declaration_result)
            # Explicit same-file recovery/sync is performed even on exact replay.
            # A read-only view or old row never substitutes for observed fsync.
            fd = os.open(ledger_path, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
            try:
                current = os.fstat(fd)
                _require(stat.S_ISREG(current.st_mode) and current.st_nlink == 1
                         and (current.st_dev, current.st_ino) == (st_before.st_dev, st_before.st_ino),
                         "LEDGER_SWAP_DETECTED")
                os.fsync(fd)
            finally:
                os.close(fd)
            _dir_fsync(staging)
            raw_after = owner.raw_readback()
            checked_after, st_after = _read_snapshot(ledger_path)
            _require(raw_after == checked_after, "READBACK_INCONSISTENT")
            present_after, declared_after = _strict_replay(raw_after, family, full)
            width = len(full)
            _require(set(present_after) == emitted_hashes | inherited_hashes
                     and declared_after == ceiling and owner.load_error is None
                     and owner.corrupt_lines == 0 and owner.literal_n(family) == width
                     and owner.declared_budget(family) == ceiling
                     and owner.effective_n(family) == max(width, ceiling, 1), "COLD_RECONCILIATION_MISMATCH")
            _require((st_after.st_dev, st_after.st_ino, st_after.st_nlink)
                     == (st_before.st_dev, st_before.st_ino, 1), "LEDGER_SWAP_DETECTED")
            # Complete the independent on-disk readback under the SAME
            # original sidecar flock. Once we unlock, a second legitimate
            # owner may append; that later append must not retroactively
            # invalidate our already-verified durable snapshot receipt.
            final_staging = os.lstat(staging)
            final_raw, final_stat = _read_snapshot(ledger_path)
            _require((final_staging.st_dev, final_staging.st_ino) == (staging_stat.st_dev, staging_stat.st_ino)
                     and final_raw == raw_after and (final_stat.st_dev, final_stat.st_ino) == (st_after.st_dev, st_after.st_ino),
                     "STAGING_IDENTITY_CHANGED")
    except StagingAccountingRefused:
        raise
    except (OSError, ValueError, RuntimeError) as exc:
        raise StagingAccountingRefused("OWNER_TRANSACTION_UNSETTLED") from exc

    recorded = [dict(variant_id=variant_id, source_sha256=identity[0],
                     config_sha256=identity[1],
                     incumbent_config_hash=identity[2])
                for variant_id, identity in sorted(full.items())]
    trial_doc = {
        "schema": _TRIAL_SCHEMA,
        "original_root_id": commission.original_root_id,
        "family": family,
        "protocol_sha256": protocol_sha256,
        "history_anchor_sha256": anchor,
        "snapshot_sha256": hashlib.sha256(raw_after).hexdigest(),
        "snapshot_bytes": len(raw_after),
        "writer_receipt_sha256": "",
        "durable_readback_receipt_sha256": "",
        "history_state": "complete",
        "load_error": None,
        "corrupt_lines": 0,
        "recorded_variants": recorded,
        "declared_floor": ceiling,
        "literal_n": width,
        "effective_n": max(width, ceiling, 1),
    }
    writer_doc = {
        "schema": _WRITER_SCHEMA,
        "original_root_id": commission.original_root_id,
        "family": family,
        "run_id": run_id,
        "ledger_basename": LEDGER_BASENAME,
        "authority": "display_only",
        "scope": "SYNTHETIC_ENGINEERING_ONLY",
        "staging_dev": staging_stat.st_dev,
        "staging_ino": staging_stat.st_ino,
        "ledger_dev": st_after.st_dev,
        "ledger_ino": st_after.st_ino,
        "ledger_mode": stat.S_IMODE(st_after.st_mode),
        "ledger_hardlinks": st_after.st_nlink,
        "bytes_before": len(raw_before),
        "bytes_after": len(raw_after),
        "sha256_before": hashlib.sha256(raw_before).hexdigest(),
        "sha256_after": hashlib.sha256(raw_after).hexdigest(),
        "appended_bytes": len(raw_after) - len(raw_before),
        "config_rows_appended": newly_recorded,
        "declared_rows_appended": declared_appended,
        "observed_order": ["core_owner_transaction_entered", "original_raw_prefix_verified",
                           "grid_appended" if newly_recorded else "existing_generation_reconciled",
                           "same_file_fsync_observed", "directory_fsync_observed",
                           "cold_readback_verified", "core_owner_transaction_exited"],
        "uncertainty": "none",
    }
    durable_doc = {
        "schema": _DURABLE_SCHEMA,
        "original_root_id": commission.original_root_id,
        "family": family,
        "run_id": run_id,
        "ledger_basename": LEDGER_BASENAME,
        "authority": "display_only",
        "scope": "SYNTHETIC_ENGINEERING_ONLY",
        "ledger_dev": st_after.st_dev,
        "ledger_ino": st_after.st_ino,
        "file_fsync_observed": True,
        "directory_fsync_observed": True,
        "cold_readback_observed": True,
        "snapshot_sha256": hashlib.sha256(raw_after).hexdigest(),
        "snapshot_bytes": len(raw_after),
        "history_state": "complete",
        "load_error": None,
        "corrupt_lines": 0,
        "literal_n": width,
        "declared_floor": ceiling,
        "effective_n": max(width, ceiling, 1),
        "uncertainty": "none",
        "durability_state": "DURABLE_GENERATION_RECORDED" if newly_recorded else "DURABLE_RECONCILED",
        "original_prefix_bytes": len(prefix),
        "original_prefix_head_sha256": hashlib.sha256(prefix.splitlines()[-1] if prefix else b"").hexdigest(),
    }
    _require(set(writer_doc) == set(_WRITER_KEYS)
             and set(durable_doc) == set(_DURABLE_KEYS)
             and contracts.is_exact_json(writer_doc)
             and contracts.is_exact_json(durable_doc)
             and contracts.is_exact_json(trial_doc), "OBSERVATION_INVALID")
    trial_doc["writer_receipt_sha256"] = hashlib.sha256(
        _canonical(writer_doc).encode("utf-8")).hexdigest()
    trial_doc["durable_readback_receipt_sha256"] = hashlib.sha256(
        _canonical(durable_doc).encode("utf-8")).hexdigest()
    # Descriptor agreement is judged only by the unchanged accounting contract.
    assessment = accounting_contract.assess_accounting_references(
        expected_doc, trial_readback=trial_doc)
    _require(assessment["status"] == "STRUCTURALLY_COMPLETE_DISABLED"
             and assessment["violations"] == [], "READBACK_INCONSISTENT")
    return StagedAccountingReadback(
        expected_generation=expected_generation,
        trial_readback=_bound_bytes(trial_doc),
        raw_snapshot=BoundBytes(raw=raw_after,
                                sha256=hashlib.sha256(raw_after).hexdigest(),
                                size=len(raw_after)),
        writer_observation=_bound_bytes(writer_doc),
        durable_readback_observation=_bound_bytes(durable_doc),
        newly_recorded_count=newly_recorded,
    )
