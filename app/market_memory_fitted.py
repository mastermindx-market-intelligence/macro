"""Authenticated COMPLETE-only fitted evidence for the existing Brain owner.

No query/fit creation, new storage, registration, or lifecycle is performed.
The original installed native owner still owns all current control, source and
COMPLETE-custody qualification; absent enrollment remains a refusal.
"""
from pathlib import Path

from fastapi import HTTPException

from app import market_memory as incumbent
from engine.neuralweb import brain_analogues as brain
from engine.neuralweb import market_memory_fitted_brain_citations as wire
from engine.neuralweb import market_memory_fitted_evidence as evidence
from engine.neuralweb import market_memory_fitted_retrieval as retrieval
from engine.neuralweb import market_memory_pit as pit
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.neuralweb import market_memory_retained_use as house
from engine.research_factory import market_memory_fitted_persistence as persistence
from engine.research_factory import market_memory_fitted_use as use
from engine.research_factory.market_memory_e0_reservations import ReservationError


def tool_available(root):
    """Public unchanged purpose guard only; no private control or owner read."""
    try:
        if Path(root).resolve() != persistence.owner.INSTALLED_ROOT.resolve():
            return False
        use._purpose(Path(root))
        return True
    except (ValueError, OSError, KeyError, TypeError):
        return False


def retained_fitted_context_for_user(root, user_id, request_spec):
    house._enforce_current_site_user(user_id)
    try:
        request = wire.validate_request(request_spec)
    except (ValueError, TypeError, OverflowError) as exc:
        raise HTTPException(400, detail={"state": "INVALID_FITTED_REFERENCE"}) from exc
    if Path(root).resolve() != persistence.owner.INSTALLED_ROOT.resolve():
        raise HTTPException(403, detail={"state": "INSTALLED_FITTED_OWNER_REQUIRED"})
    with incumbent._symbol_rate_lock:
        allowed = incumbent._book_symbol_rate(
            f"playback-user:{user_id}", limit=incumbent._PLAYBACK_USER_LIMIT,
            now=incumbent.time.monotonic())
    if not allowed:
        raise HTTPException(429, detail={"state": "RATE_LIMITED"}, headers={"Retry-After": "60"})
    if not incumbent._playback_slots.acquire(blocking=False):
        raise HTTPException(503, detail={"state": "BUSY"}, headers={"Retry-After": "2"})
    try:
        with incumbent._observe_admitted_read("retained_macro"):
            with pit.bounded_owner_reads(maximum_bytes=64 * 1024 * 1024):
                registered, _digest = house.load_registration(Path(root))
                if len(registered["allowed_subject_ids"]) != 1:
                    raise HTTPException(403, detail={"state": "SINGLE_FITTED_SUBJECT_REQUIRED"})
                reference, mode = request["reference"], request["mode"]
                intent = reference["intent"]
                policy = house.RetainedHouseUsePolicy(Path(root), user_id=user_id,
                    store_id=registered["store_id"], subject_id=registered["allowed_subject_ids"][0],
                    generation_id=intent["generation_id"], generation_sha256=intent["generation_sha256"],
                    query_cutoff=intent["query_cutoff"], mode=mode)
                policy.check("read_retained_generation_metadata", policy.expected)
                # value is required by the unchanged native transport shape but
                # is never consumed. Native reads actual COMPLETE bytes only
                # after current rights; this locator is never a capability.
                selection, current = persistence.reproduce_registered_fitted_query(
                    {**reference, "value": None}, policy=policy)
                native = retrieval.disclose_fitted_retrieval(selection, policy=current)
                if native["method"]["eligibility_method_spec"]["mode"] != mode:
                    raise HTTPException(400, detail={"state": "FITTED_MODE_MISMATCH"})
                owner = native["query_owner"]
                current.check("read_retained_generation_metadata", owner)
                reader = persistence._reader()
                generation = reader.read_pinned_generation(
                    generation_id=owner["generation_id"], maximum_capture_count=cohort.MAX_CAPTURES)
                packet = evidence.build_fitted_evidence_packet(
                    selection, reader, generation, policy=current)
                value = brain.get_fitted_retained_market_context(selection, packet, policy=current)
                value["reopen_reference"] = reference
                if len(cohort.canonical(value)) > brain.RETAINED_CONTEXT_MAX_BYTES:
                    raise HTTPException(503, detail={"state": "FITTED_RESPONSE_BYTE_BOUND"})
                retrieval.disclose_fitted_retrieval(selection, policy=current)
                evidence.disclose_fitted_evidence_packet(packet, policy=current)
                house._enforce_current_site_user(user_id)
                return value
    except HTTPException:
        raise
    except ReservationError as exc:
        # Native custody intentionally does not distinguish missing from pending
        # query results. Neither can trigger creation, replay or another read.
        if str(exc) in {"completed_result_unavailable", "uninitialized_store"}:
            raise HTTPException(409, detail={"state": "COMPLETE_FITTED_QUERY_REQUIRED"}) from exc
        raise HTTPException(503, detail={"state": "FITTED_CUSTODY_UNAVAILABLE"}) from exc
    except pit.OwnerReadBudgetError as exc:
        raise HTTPException(503, detail={"state": "OWNER_READ_BUDGET_EXCEEDED"}) from exc
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise HTTPException(403, detail={"state": "FITTED_SOURCE_USE_NOT_ADMITTED"}) from exc
    finally:
        incumbent._playback_slots.release()
