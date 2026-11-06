"""Internal, read-only recovery over the original E0 reservation owner.

This is storage sequencing, not an authenticated issuer or an admission API.
Only the fixed trusted executor may supply these same-process policy and packet
qualification functions. Never expose them, the store, or its path as request
arguments. Source/service/recipient authorization belongs to that executor.

An absent or pending original is an observation, never permission to prepare it
again. No branch initializes, reserves, finishes, refunds, or reconstructs input.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from .market_memory_e0_reservations import (
    MAX_RESULT_BYTES, ReservationError, ReservationStore, _canonical, _identifier,
)


class E0OriginalCaseError(ValueError):
    """Stable internal refusal, without persisted content or caller data."""


def _read_original_case(store, operation_id, intent, *, authorize, qualify):
    """Return ``(ABSENT|PENDING|COMPLETE, original_bytes_or_None)``.

    The caller owns current source, installation, recipient and original-operation
    permission at every policy boundary. ``qualify`` checks the original packet,
    not its scientific value or the identity of the source owner. Neither a
    callback returning None nor these returned bytes establish native authority.
    """
    if type(store) is not ReservationStore:
        raise E0OriginalCaseError("original_reservation_owner_required")
    operation_id = _identifier(operation_id)
    if type(intent) is not dict:
        raise E0OriginalCaseError("original_intent_object_required")
    frozen_intent = _canonical(intent)
    intent_digest = sha256(frozen_intent).hexdigest()
    directory, binding = store.directory, store._binding_bytes
    if type(directory) is not type(Path()) or type(binding) is not bytes:
        raise E0OriginalCaseError("original_reservation_owner_required")

    def owner_unchanged():
        if store.directory is not directory or store._binding_bytes != binding:
            raise E0OriginalCaseError("original_reservation_owner_changed")

    def check(phase):
        owner_unchanged()
        if authorize(phase, operation_id, json.loads(frozen_intent)) is not None:
            raise E0OriginalCaseError("authorization_callback_contract")
        owner_unchanged()

    # Even the existence of an original operation is protected information.
    check("inspect_original")
    # Use the incumbent native lock/journal validator, including its orphan,
    # binding, owner/mode, event-chain and immutable publication checks. The
    # public aggregate snapshot cannot distinguish this exact operation.
    with ReservationStore._locked(store) as descriptor:
        state = ReservationStore._load(store, descriptor)
        if state is None:
            raise ReservationError("uninitialized_store")
        original = ReservationStore._operation(state, operation_id, intent_digest)
        status = "ABSENT" if original is None else (
            "PENDING" if original["result"] is None else "COMPLETE")
    owner_unchanged()
    if status != "COMPLETE":
        check("disclose_original_state")
        return status, None

    check("read_original_completed")
    body = ReservationStore.read_completed(store, operation_id, json.loads(frozen_intent))
    owner_unchanged()
    if type(body) is not bytes or not 1 <= len(body) <= MAX_RESULT_BYTES:
        raise E0OriginalCaseError("bounded_original_bytes_required")
    if qualify(body, operation_id, json.loads(frozen_intent)) is not None:
        raise E0OriginalCaseError("qualification_callback_contract")
    owner_unchanged()
    check("recheck_original_completed")
    # Actual bytes, SHA, size and intent are re-read after qualification. A
    # metadata-only success or a same-size replacement cannot disclose input.
    final = ReservationStore.read_completed(store, operation_id, json.loads(frozen_intent))
    if final != body:
        raise E0OriginalCaseError("original_completed_bytes_changed")
    check("disclose_original_completed")
    return status, body
