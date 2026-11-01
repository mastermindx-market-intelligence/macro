"""Internal mechanism for a still-present original producer parent.

This module authenticates neither a caller nor process settlement. It is not a
recovery command. Its only intended caller is the original pinned launcher,
after it has actually waited for its own child and retained that child's capture
in memory. Source qualification, all-writer admission, original-parent custody
and the single-attempt production write transport remain caller requirements.
No file or caller-supplied boolean grants any of those properties.

Only the closed analyzer's acknowledged publication cut is supported. Original
evidence remains immutable; an exclusive new journal records the unissued tail
and final CAS. A lost parent, uncertain original effect, or second continuation
cannot use this mechanism. It never republishes corpus/PDF/derivative bytes.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path

from engine.research_vault import catalog, fulltext_store
from engine.research_vault import producer_generation as contract
from engine.research_vault.generation_evidence import FileGenerationEvidence
from engine.research_vault.generation_recovery import inspect_live_settled_publication
from engine.research_vault.producer_generation_writer import ProducerGenerationSession

# The admitted corpus alone can consume the analyzer's ordinary 256 MiB
# budget. This bounded continuation also checks acknowledged PDFs, receipts
# and catalog fences, so use the analyzer's existing 1 GiB aggregate limit.
# Larger cuts still refuse before any continuation write.
LIVE_BYTE_BUDGET = 1024 * 1024 * 1024


class OriginalContinuationUnavailable(RuntimeError):
    """The retained original operation requires reconciliation; never retry."""


def _refuse():
    raise OriginalContinuationUnavailable("ORIGINAL_CONTINUATION_UNAVAILABLE")


def _checked_bytes(store, row):
    raw = store.get_bytes_strict_bounded(row["key"], row["bytes"])
    if (type(raw) is not bytes or len(raw) != row["bytes"]
            or hashlib.sha256(raw).hexdigest() != row["sha256"]):
        _refuse()
    return raw


def _continue_after_original_exit(store, original_journal, *, expected_identity,
                                  original_capture_sha256, clock=None):
    """Execute one supported original tail; caller owns actual exit/custody.

    The private return includes final catalog bytes for the public-safe mirror.
    Do not serialize that return to public logs. There is intentionally no
    original-process receipt parameter, resume flag, admission flag or CLI.
    A capture digest and a valid plan alone do not authorize calling this API.
    """
    evidence = None
    try:
        now = datetime.now(timezone.utc) if clock is None else clock()
        if not isinstance(now, datetime) or now.tzinfo is None:
            _refuse()
        # All original uncertain outcomes refuse here before creating a second
        # journal or emitting any remote write, even when postimages match.
        plan = inspect_live_settled_publication(
            store, original_journal, expected_identity=expected_identity,
            original_capture_sha256=original_capture_sha256,
            byte_budget=LIVE_BYTE_BUDGET)
        document = catalog.parse_strict(plan["catalog_bytes"], check_future_clock=False)
        record = document[contract.GENERATION_FIELD]
        if now.timestamp() < record["started_at"]:
            _refuse()
        store.validate_strict_conditional_write_capability()

        confirmed = {}
        for row in plan["required_live_checks"]:
            if (row["key"] == contract.CORPUS_KEY
                    or row["key"].startswith(fulltext_store.RECEIPT_PREFIX)):
                confirmed[row["key"]] = _checked_bytes(store, row)
        if contract.CORPUS_KEY not in confirmed:
            _refuse()

        # No BEGIN and no new epoch. Restore only an already observed original
        # BUILDING predecessor, then reuse the incumbent completion algorithm.
        session = ProducerGenerationSession()
        session.store = store
        session.catalog_version = plan["catalog_version"]
        session.catalog_bytes = plan["catalog_bytes"]
        session.record = record
        session.active, session.failure = True, ""
        session._confirmed_writes = confirmed
        session.evidence = None
        session.assert_current()

        # There is one fixed continuation slot per original private run folder.
        # Never unlink or adopt it, including after a pre-effect refusal.
        continuation = Path(original_journal).parent / "continuation.jsonl"
        evidence = FileGenerationEvidence.create(continuation, expected_identity)
        evidence.append("continuation_origin", {
            "original_capture_sha256": original_capture_sha256,
            "epoch": plan["epoch"],
            "catalog_sha256": plan["catalog_sha256"],
            "catalog_version": plan["catalog_version"],
        })
        session.evidence = evidence

        for key, body in plan["unissued_receipts"]:
            session.assert_current()
            operation = session._intent(key, body, "application/json",
                                        conditional=True, expected_version=None)
            try:
                ok = store.put_bytes_strict_conditional(
                    key, body, expected_version=None, content_type="application/json")
            except Exception:
                session._result(operation, "exception_effect_unknown")
                session._fail("continuation receipt effect uncertain")
            if ok is not True:
                session._result(operation, "conditional_conflict")
                session._fail("continuation receipt conditional conflict")
            session._result(operation, "returned_true")
            session._confirmed_writes[key] = body

        completed_at = datetime.now(timezone.utc) if clock is None else clock()
        final_catalog = session.complete(document, now=completed_at)
        evidence.close()
        return {
            "state": "ORIGINAL_CONTINUATION_COMPLETE",
            "identity": dict(expected_identity), "epoch": plan["epoch"],
            "original_capture_sha256": original_capture_sha256,
            "continuation_capture_sha256": evidence.capture_sha256,
            "receipt_count": len(plan["unissued_receipts"]),
            "catalog_bytes": final_catalog,
        }
    except Exception:
        # No raw Store exception, private catalog, configured path or receipt
        # body leaves this boundary. The retained journal preserves uncertainty.
        raise OriginalContinuationUnavailable("ORIGINAL_CONTINUATION_UNAVAILABLE") from None
    finally:
        if evidence is not None:
            try:
                evidence.close()
            except Exception:
                raise OriginalContinuationUnavailable("ORIGINAL_CONTINUATION_UNAVAILABLE") from None
