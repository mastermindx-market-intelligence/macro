"""Deterministic preregistered condition-order allocation for Market Memory E0.

Scope and authority
-------------------
This module is source preparation only. It allocates a display-only ordering of
the three preregistered E0 conditions across a caller-supplied list of metadata
task identifiers. It is generated source, never an actual study allocation.

* Metadata allocation is not installed authority, not reference resolution,
  not actual reviewer blinding, and not study admission.
* This utility cannot authenticate actual task bytes or actual task selection.
  The owning study executor must first resolve and freeze the registered task
  list, then join this metadata output to that exact task manifest. A caller
  that passes internally consistent objects is never registration and never
  authority.
* The condition-order map belongs to the trusted study executor. A public,
  frozen, deterministic seed does not make this output a blinded reviewer
  packet; the eventual owner is responsible for withholding the mapping from
  reviewers.
* ``seed_is_secret``, ``operational_admission``, ``blinding_established`` and
  ``actual_task_provenance_authenticated`` are fixed ``False`` by design. The
  output carries no purported actual identities, labels, source reads,
  P-values, confidence, or acceptance.
* There is deliberately no write, access, budget, or reservation API here.

Algorithm and its limits
------------------------
Per task, independently and with no cross-task state, the digest
``SHA-256(seed_bytes || canonical_json(payload))`` is interpreted as an
unsigned big-endian 256-bit integer. Only values below
``(2**256 // 6) * 6`` are accepted, so the modulo-6 selection carries no
truncation bias. Rejected values advance a counter and are tried again, up to
``MAX_HASH_ATTEMPTS_PER_TASK`` times, after which allocation is refused with
``allocation_entropy_bound``.

The counter-driven rejection loop exists for deterministic reproducibility and
modulo-bias avoidance. It is not a cryptographic secrecy claim, not a
commitment scheme, and not evidence of real-world random sampling: identical
inputs always yield identical output. No Python builtin digest of object
identity, no global or module-level pseudo-random generator, no clock, no
environment variable, and no study outcome is consulted anywhere in this
module.

Identifiers are restricted to the ASCII registry alphabet so that canonical
UTF-8 encoding is unambiguous; surrogates, control characters, non-ASCII text,
and boolean or subclassed values are refused rather than coerced.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import re

__all__ = [
    "AllocationError",
    "OUTPUT_SCHEMA",
    "ALGORITHM",
    "AUTHORITY",
    "FROZEN_SEED_HEX",
    "CONDITIONS",
    "PERMUTATIONS",
    "MAX_TASK_IDS",
    "MAX_HASH_ATTEMPTS_PER_TASK",
    "allocate_condition_order",
]

OUTPUT_SCHEMA = "research_factory.market_memory_e0_condition_order.v1"
ALGORITHM = "market_memory.e0_condition_order.sha256_rejection_v1"
AUTHORITY = "display_only"

# Preregistered before condition labels were known. Not configurable here.
FROZEN_SEED_HEX = "7c8013e1e8092bdf91d4598a73c01d9690199dfb6c08db632b81f564367a4b03"
CONDITIONS: tuple[str, ...] = ("no_memory", "recency", "fixed_l1")

MAX_TASK_IDS = 10000
MAX_HASH_ATTEMPTS_PER_TASK = 1024

# Python's documented itertools ordering over the frozen condition tuple.
PERMUTATIONS: tuple[tuple[str, ...], ...] = tuple(itertools.permutations(CONDITIONS))
_ORDERING_SPACE = len(PERMUTATIONS)
_ACCEPTANCE_BOUND = (2**256 // _ORDERING_SPACE) * _ORDERING_SPACE

_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")
_HEX64_PATTERN = re.compile(r"[0-9a-f]{64}")

# Stable machine-readable reason strings. They are the complete error message,
# so no caller-supplied value can ever be echoed back through an exception.
REASON_SEED_TYPE = "seed_hex_must_be_native_str"
REASON_SEED_FORMAT = "seed_hex_must_be_lowercase_hex64"
REASON_SEED_NOT_FROZEN = "seed_hex_not_the_preregistered_frozen_seed"
REASON_STUDY_TYPE = "study_id_must_be_native_str"
REASON_STUDY_FORMAT = "invalid_study_id"
REASON_DIGEST_TYPE = "tasks_sha256_must_be_native_str"
REASON_DIGEST_FORMAT = "tasks_sha256_must_be_lowercase_hex64"
REASON_POPULATION_TYPE = "task_ids_must_be_native_list"
REASON_POPULATION_EMPTY = "empty_task_population"
REASON_POPULATION_OVERSIZED = "oversized_task_population"
REASON_TASK_TYPE = "task_id_must_be_native_str"
REASON_TASK_FORMAT = "invalid_task_id"
REASON_TASK_DUPLICATE = "duplicate_task_id"
REASON_ENTROPY_BOUND = "allocation_entropy_bound"


class AllocationError(ValueError):
    """Refusal carrying one fixed reason string and nothing else.

    The reason is the entire message and ``str(error) == error.reason``. Inputs
    are never interpolated, so an exception cannot leak identifiers or copy an
    attacker-controlled string into logs.
    """

    __slots__ = ("reason",)

    def __init__(self, reason: str) -> None:
        if type(reason) is not str or _ID_PATTERN.fullmatch(reason) is None:
            raise ValueError("invalid_reason_label")
        super().__init__(reason)
        self.reason = reason


def _canonical_bytes(payload: dict) -> bytes:
    """Canonical UTF-8 JSON: sorted keys, tight separators, no NaN/Infinity."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _digest(seed_bytes: bytes, payload_bytes: bytes) -> bytes:
    """The single private digest step: SHA-256 over seed bytes then payload.

    Tests may replace this internal step to exercise the rejection loop and the
    bounded refusal. It is not a public knob and no call path accepts outside
    randomness.
    """
    return hashlib.sha256(seed_bytes + payload_bytes).digest()


def _require_native_str(value: object, *, type_reason: str, format_reason: str,
                        pattern: re.Pattern) -> str:
    # Exact native str: bool, int, bytes, and str subclasses are refused, never
    # coerced. Subclasses would otherwise smuggle caller-controlled equality.
    if type(value) is not str:
        raise AllocationError(type_reason)
    if pattern.fullmatch(value) is None:
        raise AllocationError(format_reason)
    return value


def _validate_request(*, seed_hex: object, study_id: object, tasks_sha256: object,
                      task_ids: object) -> tuple[bytes, str, str, list[str]]:
    seed = _require_native_str(seed_hex, type_reason=REASON_SEED_TYPE,
                               format_reason=REASON_SEED_FORMAT, pattern=_HEX64_PATTERN)
    if seed != FROZEN_SEED_HEX:
        raise AllocationError(REASON_SEED_NOT_FROZEN)
    study = _require_native_str(study_id, type_reason=REASON_STUDY_TYPE,
                                format_reason=REASON_STUDY_FORMAT, pattern=_ID_PATTERN)
    digest = _require_native_str(tasks_sha256, type_reason=REASON_DIGEST_TYPE,
                                 format_reason=REASON_DIGEST_FORMAT, pattern=_HEX64_PATTERN)
    if type(task_ids) is not list:
        raise AllocationError(REASON_POPULATION_TYPE)
    if not task_ids:
        raise AllocationError(REASON_POPULATION_EMPTY)
    if len(task_ids) > MAX_TASK_IDS:
        raise AllocationError(REASON_POPULATION_OVERSIZED)
    validated: list[str] = []
    seen: set[str] = set()
    for raw in task_ids:
        task_id = _require_native_str(raw, type_reason=REASON_TASK_TYPE,
                                      format_reason=REASON_TASK_FORMAT, pattern=_ID_PATTERN)
        if task_id in seen:
            raise AllocationError(REASON_TASK_DUPLICATE)
        seen.add(task_id)
        validated.append(task_id)
    return bytes.fromhex(FROZEN_SEED_HEX), study, digest, validated


def _select_order(*, seed_bytes: bytes, study_id: str, tasks_sha256: str,
                  task_id: str) -> tuple[str, ...]:
    """Deterministic permutation index for one task through the bounded counter loop.

    The counter starts at 0. A digest whose big-endian value is not below the
    acceptance bound is refused and the counter advances; after
    ``MAX_HASH_ATTEMPTS_PER_TASK`` attempts allocation is refused outright.
    Nothing here is drawn, seeded, or influenced from outside these inputs.
    """
    for counter in range(MAX_HASH_ATTEMPTS_PER_TASK):
        payload_bytes = _canonical_bytes({
            "algorithm": ALGORITHM,
            "study_id": study_id,
            "tasks_sha256": tasks_sha256,
            "task_id": task_id,
            "counter": counter,
        })
        value = int.from_bytes(_digest(seed_bytes, payload_bytes), "big")
        if value < _ACCEPTANCE_BOUND:
            return PERMUTATIONS[value % _ORDERING_SPACE]
    raise AllocationError(REASON_ENTROPY_BOUND)


def allocate_condition_order(*, seed_hex: str, study_id: str, tasks_sha256: str,
                             task_ids: list[str]) -> dict:
    """Return a detached JSON-native condition-order allocation record.

    Keyword-only and closed: there is no extra argument, no alternate-randomness
    or seed-substitution parameter, and no positional call form.

    Args:
        seed_hex: Must equal ``FROZEN_SEED_HEX`` exactly, lowercase hex64.
        study_id: Native str matching ``[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}``.
        tasks_sha256: Lowercase hex64 digest of the already-frozen registered
            task manifest. Supplying it here does not authenticate that
            manifest; this utility never reads task bytes.
        task_ids: Native list of 1..10000 unique native-str task identifiers.

    Returns:
        A freshly built dict with ``assignments`` sorted by ``task_id`` so that
        caller input order cannot affect output, plus ``allocation_sha256`` over
        the canonical encoding of every other field. The record is display-only
        metadata: it grants no admission, proves no blinding, and authenticates
        no provenance.

    Raises:
        AllocationError: A stable reason string; the offending input is never
            echoed. ``TypeError`` is raised by Python itself for extra or
            positional arguments, before this body runs.
    """
    seed_bytes, study, tasks_digest, population = _validate_request(
        seed_hex=seed_hex, study_id=study_id, tasks_sha256=tasks_sha256, task_ids=task_ids)

    # Build order in canonical sorted position: input order cannot affect output.
    assignments = [
        {
            "task_id": task_id,
            "order": list(_select_order(seed_bytes=seed_bytes, study_id=study,
                                       tasks_sha256=tasks_digest, task_id=task_id)),
        }
        for task_id in sorted(population)
    ]

    record: dict = {
        "schema": OUTPUT_SCHEMA,
        "authority": AUTHORITY,
        "algorithm": ALGORITHM,
        "study_id": study,
        "tasks_sha256": tasks_digest,
        "seed_hex": FROZEN_SEED_HEX,
        "seed_is_secret": False,
        "conditions": list(CONDITIONS),
        "assignments": assignments,
        "operational_admission": False,
        "blinding_established": False,
        "actual_task_provenance_authenticated": False,
    }
    # Self-binding digest over the canonical object excluding this key itself.
    record["allocation_sha256"] = hashlib.sha256(_canonical_bytes(record)).hexdigest()
    return record
