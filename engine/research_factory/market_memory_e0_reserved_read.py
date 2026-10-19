"""Internal sequencing for an already authorized installed E0 study owner.

This is not an authorization entry point. All callables are trusted code in the
same owner process, never request-supplied functions, imports or permission flags.
The installed owner must authenticate its fixed study selection, fully resolve
domain records, bind the operation to its registered task/action and select the
source reader before calling here. Current E0 metadata validators grant none of
that authority. No public endpoint, actual study or provider is activated here.

The policy callback raises on denial and returns None on success. It must check
current owner time, selected installation, access history, source rights and
contamination on every call. Result qualification must authenticate the original
operation's output; receiving bytes is insufficient. Callback failure leaves
durable reservations/completions intact. No retry, recovery or refund is inferred.
"""
from __future__ import annotations

import json
from collections.abc import Callable

from .market_memory_e0_reservations import MAX_RESULT_BYTES, ReservationStore, _canonical


class E0ReservedReadError(ValueError):
    pass


def _run_reserved_read(
    store: ReservationStore,
    operation_id: str,
    intent: dict,
    *,
    authorize: Callable[[str, str, dict], None],
    load: Callable[[], bytes],
    qualify: Callable[[bytes, str, dict], None],
) -> bytes:
    """Consume one new reservation or disclose its original completed result.

    EXISTING_PENDING is an unresolved operation, including a crash between
    reservation and read. It never invokes load. COMPLETE also never invokes
    load, consumes no second look and requires current policy and qualification.
    This helper does not initialize a store or accept an externally supplied
    completion as recovery. Such reconciliation belongs to the original owner.
    """
    frozen = _canonical(intent)

    def clean_intent() -> dict:
        return json.loads(frozen)

    def check(phase: str) -> None:
        if authorize(phase, operation_id, clean_intent()) is not None:
            raise E0ReservedReadError("authorization_callback_contract")

    def qualified(body: bytes) -> None:
        if type(body) is not bytes or not 1 <= len(body) <= MAX_RESULT_BYTES:
            raise E0ReservedReadError("bounded_result_bytes_required")
        if qualify(body, operation_id, clean_intent()) is not None:
            raise E0ReservedReadError("qualification_callback_contract")

    # Even reservation metadata/result digests can reveal labels. Check policy
    # before touching accounting, then again after the durable reservation.
    check("reserve")
    reservation = store.reserve(operation_id, clean_intent())
    if reservation["status"] == "EXISTING_PENDING":
        raise E0ReservedReadError("original_operation_pending_no_replay")
    if reservation["status"] == "NEW":
        check("read")
        body = load()
        check("persist")
        qualified(body)
        # Qualification can take time; a revoke during it must prevent writing.
        check("persist")
        store.finish(operation_id, clean_intent(), body)
    elif reservation["status"] != "COMPLETE":
        raise E0ReservedReadError("reservation_status_unqualified")
    # Always disclose retained, integrity-checked bytes, including the new case.
    check("read_completed")
    body = store.read_completed(operation_id, clean_intent())
    qualified(body)
    check("disclose")
    return body
