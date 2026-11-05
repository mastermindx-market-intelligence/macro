"""Dormant comparisons of incumbent accounting references, with no I/O.

The trusted assigning caller supplies an expected full generation set and exact
owner readback references. Agreement cannot authenticate either caller or owner,
prove complete unseen history, establish singleton custody, or prove durability.
No result from this module enables generation, execution, evaluation or authority.
"""
from __future__ import annotations

import json
import math
import re

MAX_DEPTH = 16
MAX_NODES = 8192
MAX_CONTAINER_ITEMS = 1024
MAX_STRING_CHARS = 4096
MAX_BYTES = 262144
MAX_VARIANTS = 256
MAX_COUNT = 1_000_000
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SHORT_HASH = re.compile(r"[0-9a-f]{16}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_FAMILY = re.compile(r"rf\.[a-z_]+\.[a-z0-9_]+\Z")
_EXPECTED_KEYS = frozenset({
    "schema", "original_root_id", "family", "protocol_sha256",
    "history_anchor_sha256", "variants", "inherited_variants",
    "trial_ceiling", "vault_required", "vault_request",
})
_VARIANT_KEYS = frozenset({
    "variant_id", "source_sha256", "config_sha256", "incumbent_config_hash",
})
_TRIAL_KEYS = frozenset({
    "schema", "original_root_id", "family", "protocol_sha256",
    "history_anchor_sha256", "snapshot_sha256", "snapshot_bytes",
    "writer_receipt_sha256", "durable_readback_receipt_sha256", "history_state",
    "load_error", "corrupt_lines", "recorded_variants", "declared_floor",
    "literal_n", "effective_n",
})
_VAULT_REQUEST_KEYS = frozenset({
    "window_id", "hypothesis_id", "request_id", "consumption_id",
    "seal_sha256", "history_anchor_sha256", "consumption_record_sha256",
    "minimum_peek_count",
})
_VAULT_KEYS = _VAULT_REQUEST_KEYS | frozenset({
    "schema", "original_root_id", "protocol_sha256", "seals_snapshot_sha256",
    "seals_snapshot_bytes", "peek_snapshot_sha256", "peek_snapshot_bytes",
    "writer_receipt_sha256", "durable_consumption_receipt_sha256",
    "label_mediator_receipt_sha256", "history_state", "consumption_state",
    "load_error", "corrupt_lines", "retired", "chain_state", "peek_count",
})


def _exact_json(value: object) -> bool:
    """Bound the plain tree before canonical encoding; invoke no custom hooks."""
    pending = [(value, 0)]
    seen: set[int] = set()
    nodes = 0
    string_chars = 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        if nodes > MAX_NODES or depth > MAX_DEPTH:
            return False
        kind = type(item)
        if kind is dict or kind is list:
            if id(item) in seen or len(item) > MAX_CONTAINER_ITEMS:
                return False
            seen.add(id(item))
            if kind is dict:
                for key, child in item.items():
                    if type(key) is not str or len(key) > MAX_STRING_CHARS:
                        return False
                    string_chars += len(key)
                    pending.append((child, depth + 1))
            else:
                for child in item:
                    pending.append((child, depth + 1))
            if len(pending) + nodes > MAX_NODES:
                return False
        elif kind is str:
            string_chars += len(item)
            if len(item) > MAX_STRING_CHARS:
                return False
        elif kind is int:
            if abs(item) > 2**63 - 1:
                return False
        elif kind is float:
            if not math.isfinite(item):
                return False
        elif item is not None and kind is not bool:
            return False
        if string_chars > MAX_BYTES:
            return False
    try:
        body = json.dumps(value, allow_nan=False, ensure_ascii=False,
                          sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError):
        return False
    return len(body) <= MAX_BYTES


def _closed(value: object, keys: frozenset[str], label: str,
            errors: list[str]) -> bool:
    if type(value) is not dict or set(value) != keys:
        errors.append(label + ": closed object required")
        return False
    return True


def _id(value: object) -> bool:
    return type(value) is str and _ID.fullmatch(value) is not None


def _sha(value: object) -> bool:
    return type(value) is str and _SHA256.fullmatch(value) is not None


def _count(value: object, minimum: int = 0, maximum: int = MAX_COUNT) -> bool:
    return type(value) is int and minimum <= value <= maximum


def _variants(value: object, label: str, errors: list[str]) -> dict[str, tuple]:
    result: dict[str, tuple] = {}
    strong_seen: set[str] = set()
    short_seen: dict[str, tuple] = {}
    if type(value) is not list or len(value) > MAX_VARIANTS:
        errors.append(label + ": bounded list required")
        return result
    for row in value:
        if not _closed(row, _VARIANT_KEYS, label + ".variant", errors):
            continue
        if (not _id(row["variant_id"]) or not _sha(row["source_sha256"])
                or not _sha(row["config_sha256"])
                or type(row["incumbent_config_hash"]) is not str
                or _SHORT_HASH.fullmatch(row["incumbent_config_hash"]) is None):
            errors.append(label + ": malformed variant identity")
            continue
        key = row["variant_id"]
        identity = (row["source_sha256"], row["config_sha256"],
                    row["incumbent_config_hash"])
        if key in result:
            errors.append(label + ": duplicate variant ID")
        if row["config_sha256"] in strong_seen:
            errors.append(label + ": duplicate scientific configuration")
        short = row["incumbent_config_hash"]
        if short in short_seen and short_seen[short] != identity:
            errors.append(label + ": incumbent hash collision or swapped bytes")
        result[key] = identity
        strong_seen.add(row["config_sha256"])
        short_seen[short] = identity
    return result


def _snapshot(row: dict, fields: tuple[str, ...], label: str,
              errors: list[str]) -> None:
    for field in fields:
        if not _sha(row[field]):
            errors.append(label + ": malformed digest reference")


def _vault_request(value: object, errors: list[str]) -> bool:
    if not _closed(value, _VAULT_REQUEST_KEYS, "expected.vault_request", errors):
        return False
    for field in ("window_id", "hypothesis_id", "request_id", "consumption_id"):
        if not _id(value[field]):
            errors.append("expected.vault_request: malformed original identity")
    _snapshot(value, ("seal_sha256", "history_anchor_sha256",
                      "consumption_record_sha256"), "expected.vault_request", errors)
    if not _count(value["minimum_peek_count"], 1):
        errors.append("expected.vault_request: invalid minimum peek count")
    return True


def assess_accounting_references(expected_generation: object, *,
                                 trial_readback: object,
                                 vault_readback: object = None) -> dict:
    """Compare inert references. Even complete agreement is permanently dormant.

    The caller must bind an expected full original family, including inherited
    emitted configurations, separately from readback. This function does not
    observe generation, inspect a ledger, reconstruct accounting, release labels,
    or authenticate receipts. A supplied digest is only a comparison value.
    """
    errors: list[str] = []
    inputs = ((expected_generation, "expected"),
              (trial_readback, "trial_readback"), (vault_readback, "vault_readback"))
    for value, label in inputs:
        if not _exact_json(value):
            errors.append(label + ": bounded finite exact JSON required")
    if errors:
        return _result(errors)
    if not _closed(expected_generation, _EXPECTED_KEYS, "expected", errors):
        return _result(errors)
    expected = expected_generation
    if expected["schema"] != "research_codegen.expected_generation.v1":
        errors.append("expected: wrong schema")
    if not _id(expected["original_root_id"]):
        errors.append("expected: malformed original root")
    family = expected["family"]
    if type(family) is not str or len(family) >= 40 or _FAMILY.fullmatch(family) is None:
        errors.append("expected: invalid original family")
    _snapshot(expected, ("protocol_sha256", "history_anchor_sha256"), "expected", errors)
    emitted = _variants(expected["variants"], "expected.emitted", errors)
    inherited = _variants(expected["inherited_variants"], "expected.inherited", errors)
    # Check collisions across the new and inherited portions as well.
    if type(expected["variants"]) is list and type(expected["inherited_variants"]) is list:
        full = _variants(expected["inherited_variants"] + expected["variants"],
                         "expected.original_family", errors)
    else:
        full = {}
    width = len(full)
    if not emitted or width != len(emitted) + len(inherited):
        errors.append("expected: nonempty distinct full generation set required")
    if not _count(expected["trial_ceiling"], 1, MAX_VARIANTS) or width > expected["trial_ceiling"]:
        errors.append("expected: original trial ceiling exceeded or invalid")
    if type(expected["vault_required"]) is not bool:
        errors.append("expected: explicit vault requirement required")
    if expected["vault_required"] is True:
        _vault_request(expected["vault_request"], errors)
    elif expected["vault_request"] is not None:
        errors.append("expected: dormant optional vault request must be null")
    if errors:
        return _result(errors)

    if _closed(trial_readback, _TRIAL_KEYS, "trial", errors):
        trial = trial_readback
        if trial["schema"] != "research_codegen.trial_readback_reference.v1":
            errors.append("trial: wrong schema")
        for field in ("original_root_id", "family", "protocol_sha256", "history_anchor_sha256"):
            if trial[field] != expected[field]:
                errors.append("trial: original generation or history identity mismatch")
        _snapshot(trial, ("snapshot_sha256", "writer_receipt_sha256",
                          "durable_readback_receipt_sha256"), "trial", errors)
        if not _count(trial["snapshot_bytes"], 1, 2**63 - 1):
            errors.append("trial: invalid snapshot size")
        if (trial["history_state"] != "complete" or trial["load_error"] is not None
                or type(trial["corrupt_lines"]) is not int or trial["corrupt_lines"] != 0):
            errors.append("trial: incomplete, corrupt or uncertain history")
        recorded = _variants(trial["recorded_variants"], "trial.recorded", errors)
        if recorded != full:
            errors.append("trial: full explicit original generation set mismatch")
        for field in ("declared_floor", "literal_n", "effective_n"):
            if not _count(trial[field]):
                errors.append("trial: invalid accounting count")
        if all(_count(trial[field]) for field in ("declared_floor", "literal_n", "effective_n")):
            if trial["literal_n"] != width:
                errors.append("trial: literal count does not match full itemized width")
            if trial["declared_floor"] < width or trial["declared_floor"] > expected["trial_ceiling"]:
                errors.append("trial: declaration does not cover the bounded original search")
            if trial["effective_n"] != max(width, trial["declared_floor"], 1):
                errors.append("trial: lowball, correlation credit or unexplained count")

    if expected["vault_required"] is True:
        if _closed(vault_readback, _VAULT_KEYS, "vault", errors):
            vault = vault_readback
            valid_minimum = _count(vault["minimum_peek_count"], 1)
            if not valid_minimum:
                errors.append("vault: invalid readback minimum peek count")
            if vault["schema"] != "research_codegen.vault_readback_reference.v1":
                errors.append("vault: wrong schema")
            request = expected["vault_request"]
            if type(request) is dict and set(request) == _VAULT_REQUEST_KEYS:
                for field in _VAULT_REQUEST_KEYS:
                    if vault[field] != request[field]:
                        errors.append("vault: original request, consumption or anchor mismatch")
            for field in ("original_root_id", "protocol_sha256"):
                if vault[field] != expected[field]:
                    errors.append("vault: original generation identity mismatch")
            _snapshot(vault, ("seals_snapshot_sha256", "peek_snapshot_sha256",
                              "writer_receipt_sha256", "durable_consumption_receipt_sha256",
                              "label_mediator_receipt_sha256"), "vault", errors)
            if not all(_count(vault[f], 1, 2**63 - 1) for f in
                       ("seals_snapshot_bytes", "peek_snapshot_bytes")):
                errors.append("vault: invalid history snapshot sizes")
            if (vault["history_state"] != "complete" or vault["chain_state"] != "consistent"
                    or vault["consumption_state"] != "recorded"
                    or vault["load_error"] is not None or type(vault["corrupt_lines"]) is not int
                    or vault["corrupt_lines"] != 0 or vault["retired"] is not False):
                errors.append("vault: uncertain, retired or unqualified history reference")
            if not _count(vault["peek_count"], 1) or (
                    valid_minimum and vault["peek_count"] < vault["minimum_peek_count"]):
                errors.append("vault: consumed access count mismatch")
    elif vault_readback is not None:
        errors.append("vault: unexpected optional readback")
    return _result(errors)


def _result(errors: list[str]) -> dict:
    # Fixed diagnostics do not echo source content, secrets or caller paths.
    return {
        "schema": "research_codegen.accounting_reference_assessment.v1",
        "status": "PREREQUISITES_INVALID" if errors else "STRUCTURALLY_COMPLETE_DISABLED",
        "violations": list(dict.fromkeys(errors)),
        "generation_enabled": False,
        "execution_enabled": False,
        "evaluation_enabled": False,
        "authority_granted": False,
        "owner_origin_and_durability": "UNQUALIFIED",
        "note": "Reference agreement cannot authenticate caller-authored receipts, prove unseen "
                "history completeness, singleton custody, durable consumption or label mediation.",
    }
