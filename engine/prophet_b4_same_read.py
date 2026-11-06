"""The same-read join between the canonical B3 projection and B4 Availability.

This module is the single caller both existing owners have been waiting for: it
derives the B3 candidate projection ONCE through
``engine.prophet_candidate_state.build_native_factual_assessment_result`` (the
pair consumed only via ``NativeFactualAssessmentResult.verified_pair`` — never
a reprojected decision session, second read, or stamped receipt) and reads the
B4 owner inputs ONCE through
``engine.prophet_entry_availability_sources.read_native_b4_owner_inputs``
against the SAME snapshot object and the same candidate key/receipt.  It then
checks that the owner read's native binding is the very episode/generation/
session the verified pair carries, re-attests the two owner files byte-for-byte
against the reader's own digests, and delegates the Availability decision to
``evaluate_runtime_entry_availability`` alone — this module never constructs a
B4 ``facts`` mapping itself.

Fail-closed law (program unit B05): whenever a mandatory owner fact is absent
the result is ``state="UNAVAILABLE_DATA"`` with typed reasons, never a guess.
At BASE that is ALWAYS the outcome, because the native entry-geometry and
metric owners do not exist yet: those composer inputs are passed as the empty
mapping the composer documents for "no owner fact", and the composer's own
typed refusal (``RuntimeOwnerFactError``) is carried verbatim as the reason.
No NBBO/bid/ask key is added to the B4 fact or quote contract, no gate is
waived, and nothing is written, cached, or fetched.

``nbbo_quality`` is envelope EVIDENCE only: it classifies the owner read's
observed quote when (and only when) that row actually carries bid/ask/ts
fields — which no owner publishes at BASE, so the value is ``"MISSING"`` — and
it never enters B4 facts and never changes ``state``; liquidity fillability
stays the fillability owner's fact.  ``classify_nbbo`` states the rejection
rule a future NBBO owner must satisfy.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
from math import isfinite
from typing import Mapping

from engine.prophet_candidate_state import (
    CandidateStateContractError,
    build_native_factual_assessment_result,
)
from engine.prophet_entry_availability import EntryAvailabilityContractError
from engine.prophet_entry_availability_sources import (
    RuntimeOwnerFactError,
    evaluate_runtime_entry_availability,
    read_native_b4_owner_inputs,
)

#: The closed schema of one same-read join result.
SAME_READ_SCHEMA = "prophet.b4.same_read/v1"

#: The closed result key set (frozen contract).  Tested verbatim.
RESULT_KEYS = (
    "schema",
    "state",
    "availability",
    "b3_projection_id",
    "episode_id",
    "binding",
    "owner_read_schema",
    "nbbo_quality",
    "unavailable_reasons",
    "receipts",
)

_STATE_EVALUATED = "EVALUATED"
_STATE_UNAVAILABLE = "UNAVAILABLE_DATA"

#: The owner-read binding fields that must equal the bound B3 pair exactly.
#: The reader emits exactly these names (plus ``store_symbol``, which the B3
#: pair has no counterpart for and which is therefore echoed, not compared).
_BINDING_FIELDS = ("security_id", "episode_id", "candidate_generation_id", "market_session")

#: The observed-quote fields a future NBBO owner must publish before
#: ``nbbo_quality`` can be anything but ``MISSING``.
_NBBO_FIELDS = ("bid", "ask", "nbbo_ts")

#: The only exception classes the owner chain may raise for an absent or
#: contradictory mandatory fact; each is typed into ``unavailable_reasons`` as
#: ``"<ExceptionClass>: <message>"``.  Anything else propagates.
_CONTRACT_ERRORS = (
    RuntimeOwnerFactError,
    EntryAvailabilityContractError,
    CandidateStateContractError,
)


class _OwnerBytesChanged(Exception):
    """The attested owner bytes are no longer what the reader read.

    Deliberately NOT one of ``_CONTRACT_ERRORS``: the join's own typed reason
    ``SAME_READ_OWNER_BYTES_CHANGED:<name>`` must reach the envelope verbatim,
    not be re-wrapped as a generic contract refusal.
    """

    def __init__(self, name: str) -> None:
        super().__init__(f"owner file {name} changed since the attested read")
        self.name = name


def _typed_reason(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"


def _parse_instant(value: object, field: str) -> datetime:
    """Parse one required timezone-aware ISO-8601 instant to UTC."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be an ISO-8601 timestamp string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp string") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def classify_nbbo(
    bid: object,
    ask: object,
    nbbo_ts: object,
    *,
    decision_at: str,
    max_age_seconds: float,
) -> str:
    """Classify one NBBO observation as entry evidence — the rejection rule.

    A future NBBO owner must publish a real bid/ask pair and a parseable,
    pre-decision, timezone-aware quote timestamp whose age stays inside the
    disclosed ceiling; anything else is typed and refused, never repaired.
    Outcomes, in check order: ``MISSING`` (bid or ask absent), ``INVALID``
    (non-numeric, bool, non-finite, or <= 0 side), ``UNCLOCKED`` (timestamp
    missing, unparseable, or naive), ``STALE`` (timestamp after
    ``decision_at`` or older than ``max_age_seconds`` — age exactly AT the
    ceiling is still QUALIFIED), ``LOCKED`` (bid == ask), ``CROSSED``
    (bid > ask), ``QUALIFIED`` (a genuine two-sided market inside the window).

    ``decision_at`` and ``max_age_seconds`` are the caller's reference
    contract, not evidence: a malformed ``decision_at`` or a non-finite or
    negative ceiling raises ``ValueError`` instead of being classified.
    """
    decision_clock = _parse_instant(decision_at, "decision_at")
    if isinstance(max_age_seconds, bool) or not isinstance(max_age_seconds, (int, float)) \
            or not isfinite(float(max_age_seconds)) or float(max_age_seconds) < 0:
        raise ValueError("max_age_seconds must be a finite non-negative number")

    if bid is None or ask is None:
        return "MISSING"
    for side in (bid, ask):
        if isinstance(side, bool) or not isinstance(side, (int, float)) \
                or not isfinite(float(side)) or float(side) <= 0:
            return "INVALID"
    if not isinstance(nbbo_ts, str) or not nbbo_ts:
        return "UNCLOCKED"
    try:
        observed = datetime.fromisoformat(nbbo_ts.replace("Z", "+00:00"))
    except ValueError:
        return "UNCLOCKED"
    if observed.tzinfo is None:
        return "UNCLOCKED"
    observed = observed.astimezone(timezone.utc)
    if observed > decision_clock:
        return "STALE"
    if (decision_clock - observed).total_seconds() > float(max_age_seconds):
        return "STALE"
    if float(bid) == float(ask):
        return "LOCKED"
    if float(bid) > float(ask):
        return "CROSSED"
    return "QUALIFIED"


def _reattest_owner_file(name: str, owner_read: Mapping[str, object]) -> object:
    """Re-read one attested owner file and require the reader's own digest.

    The composer consumes parsed artifacts, not the reader's summary, so the
    bytes must be loaded here — and loading them makes the join hostage to the
    file being unchanged between the reader's attestation and this
    composition.  The digest is recomputed over the RAW file bytes exactly as
    the reader computed it; any difference, or a file that can no longer be
    read at all, raises ``_OwnerBytesChanged`` (no retry, no fallback).
    """
    reads = owner_read.get("owner_reads")
    attested = reads.get(name) if isinstance(reads, Mapping) else None
    if not isinstance(attested, Mapping):
        raise RuntimeOwnerFactError(f"qualified owner read attests no {name} bytes")
    path_text = attested.get("path")
    expected = attested.get("sha256")
    if not isinstance(path_text, str) or not isinstance(expected, str):
        raise RuntimeOwnerFactError(f"qualified owner read attests no {name} digest")
    try:
        raw = Path(path_text).read_bytes()
    except OSError as exc:
        raise _OwnerBytesChanged(name) from exc
    if "sha256:" + sha256(raw).hexdigest() != expected:
        raise _OwnerBytesChanged(name)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:  # pragma: no cover - digest equality
        raise RuntimeOwnerFactError(f"attested {name} bytes are not JSON: {exc}") from exc


def _observed_nbbo_quality(owner_read: Mapping[str, object], decision_at: str) -> str:
    """Classify the observed quote ONLY if the owner row actually carries NBBO.

    Evidence only: the verdict never enters B4 facts and never changes the
    envelope state.  At BASE no owner publishes ``bid``/``ask``/``nbbo_ts``,
    so this is always ``MISSING``.  When a future owner does publish them, the
    ceiling it is aged against is the same freshness policy the live owner
    disclosed to the qualified read — never a value invented here.
    """
    observed = owner_read.get("observed")
    if not isinstance(observed, Mapping) or any(field not in observed for field in _NBBO_FIELDS):
        return "MISSING"
    reads = owner_read.get("owner_reads")
    live_read = reads.get("prophet_live") if isinstance(reads, Mapping) else None
    policy = live_read.get("quote_freshness_policy") if isinstance(live_read, Mapping) else None
    ceiling_minutes = policy.get("quote_max_age_min") if isinstance(policy, Mapping) else None
    if isinstance(ceiling_minutes, bool) or not isinstance(ceiling_minutes, (int, float)) \
            or not isfinite(float(ceiling_minutes)) or float(ceiling_minutes) <= 0:
        return "MISSING"
    return classify_nbbo(
        observed.get("bid"),
        observed.get("ask"),
        observed.get("nbbo_ts"),
        decision_at=decision_at,
        max_age_seconds=float(ceiling_minutes) * 60.0,
    )


def _binding_mismatches(
    binding: Mapping[str, object],
    assessment: Mapping[str, object],
    projection: Mapping[str, object],
    row: Mapping[str, object],
) -> list[str]:
    """The binding fields on which the owner read and the B3 pair disagree.

    Every field is compared against BOTH B3 carriers (the projection document
    and the receipt-bound assessment/row) so a mismatch is never repaired,
    re-labelled, or joined by any softer key.  Returns the typed reasons.
    """
    expected = {
        "security_id": (assessment.get("security_id"), row.get("security_id")),
        "episode_id": (assessment.get("episode_id"), row.get("episode_id")),
        "candidate_generation_id": (
            assessment.get("candidate_generation_id"),
            projection.get("candidate_generation_id"),
            row.get("candidate_generation_id"),
        ),
        "market_session": (
            assessment.get("market_session"),
            projection.get("market_session"),
        ),
    }
    return [
        f"SAME_READ_BINDING_MISMATCH:{field}"
        for field in _BINDING_FIELDS
        if any(binding.get(field) != value for value in expected[field])
    ]


def evaluate_same_read_entry_availability(
    repo_root: object,
    snapshot: object,
    *,
    candidate_source_event_id: str,
    candidate_source_receipt: str,
    native_live_root: object,
    alias_table: object,
    strategy_definition: Mapping[str, object],
    signal_gate_artifact: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Join ONE native B3 read and ONE native B4 owner read into one envelope.

    Returns the closed ``prophet.b4.same_read/v1`` result (``RESULT_KEYS``).
    ``state`` is ``EVALUATED`` only when B4 itself returned a row from facts
    the owner chain bound; every absent mandatory owner fact — reader refusal,
    binding mismatch, changed owner bytes, or a composer/evaluator contract
    refusal — types the envelope ``UNAVAILABLE_DATA`` with the owner's own
    reasons verbatim.  The row, when present, is returned unmodified.
    """
    result: dict[str, object] = {
        "schema": SAME_READ_SCHEMA,
        "state": _STATE_UNAVAILABLE,
        "availability": None,
        "b3_projection_id": None,
        "episode_id": None,
        "binding": None,
        "owner_read_schema": None,
        "nbbo_quality": "MISSING",
        "unavailable_reasons": [],
        "receipts": [],
    }

    # ── The ONE native B3 read; the pair only as verified_pair() serves it ──
    try:
        native = build_native_factual_assessment_result(
            snapshot,
            candidate_source_event_id=candidate_source_event_id,
            candidate_source_receipt=candidate_source_receipt,
        )
        assessment, projection = native.verified_pair()
    except _CONTRACT_ERRORS as exc:
        result["unavailable_reasons"] = [_typed_reason(exc)]
        return result
    episode_id = assessment.get("episode_id")
    result["b3_projection_id"] = projection.get("projection_id")
    result["episode_id"] = episode_id
    receipts = {
        str(assessment.get("source_receipt")),
        str(projection.get("projection_id")),
    }

    # ── The ONE owner read: same snapshot object, same key and receipt ──
    owner_read = read_native_b4_owner_inputs(
        repo_root,
        snapshot,
        candidate_source_event_id=candidate_source_event_id,
        candidate_source_receipt=candidate_source_receipt,
        native_live_root=native_live_root,
        alias_table=alias_table,
    )
    result["owner_read_schema"] = owner_read.get("schema")
    result["binding"] = owner_read.get("binding")

    # ── Owner refusal passthrough: the reader's reasons are already typed ──
    quote_input = owner_read.get("quote_input")
    reader_reasons = owner_read.get("unavailable_reasons")
    if quote_input is None or (isinstance(reader_reasons, list) and reader_reasons):
        result["unavailable_reasons"] = sorted(str(reason) for reason in (reader_reasons or []))
        result["receipts"] = sorted(receipts)
        return result
    if isinstance(quote_input, Mapping):
        receipt = quote_input.get("source_receipt")
        if isinstance(receipt, str):
            receipts.add(receipt)
    binding = owner_read.get("binding")
    if not isinstance(binding, Mapping):
        raise RuntimeOwnerFactError("qualified owner read published no binding")
    clocks = owner_read.get("clocks")
    if not isinstance(clocks, Mapping):
        raise RuntimeOwnerFactError("qualified owner read published no clocks")

    # ── Same-read binding: the owner read must BE the verified pair's native
    #    relation — never repaired, never joined by ticker. ──
    rows = [
        candidate
        for candidate in projection.get("rows", [])
        if isinstance(candidate, Mapping) and candidate.get("episode_id") == episode_id
    ]
    if len(rows) != 1:  # pragma: no cover - verified_pair enforces exactly one
        raise CandidateStateContractError(
            "verified pair does not carry exactly one bound episode row"
        )
    mismatches = _binding_mismatches(binding, assessment, projection, rows[0])
    if mismatches:
        result["unavailable_reasons"] = sorted(mismatches)
        result["receipts"] = sorted(receipts)
        return result

    # ── The owner bytes the composer will consume are the bytes attested ──
    try:
        quotes_envelope = _reattest_owner_file("quotes_full", owner_read)
        live_artifact = _reattest_owner_file("prophet_live", owner_read)
    except _OwnerBytesChanged as exc:
        result["unavailable_reasons"] = [f"SAME_READ_OWNER_BYTES_CHANGED:{exc.name}"]
        result["receipts"] = sorted(receipts)
        return result
    if not isinstance(quotes_envelope, Mapping) or not isinstance(live_artifact, Mapping):
        raise RuntimeOwnerFactError("attested owner payloads are not objects")

    decision_at = clocks.get("live_pass_ts")
    if not isinstance(decision_at, str) or not decision_at:
        raise RuntimeOwnerFactError("qualified owner read published no live pass clock")
    market_session = binding.get("market_session")

    result["nbbo_quality"] = _observed_nbbo_quality(owner_read, decision_at)

    # ── Facts only from the owner chain: the evaluator composes; this module
    #    never builds a facts mapping.  Geometry/metric owners do not exist at
    #    BASE, so their inputs are the empty "no owner fact" mappings. ──
    try:
        row = evaluate_runtime_entry_availability(
            projection,
            episode_id=episode_id,
            strategy_definition=strategy_definition,
            decision_at=decision_at,
            market_session=market_session,
            alias_table=alias_table,
            quotes_by_symbol=quotes_envelope.get("quotes"),
            live_state_artifact=live_artifact,
            entry_rows_by_symbol={},
            metric_inputs={},
            signal_gate_artifact=signal_gate_artifact,
        )
    except _CONTRACT_ERRORS as exc:
        result["unavailable_reasons"] = [_typed_reason(exc)]
        result["receipts"] = sorted(receipts)
        return result

    result["state"] = _STATE_EVALUATED
    result["availability"] = row
    if isinstance(row, Mapping) and isinstance(row.get("source_receipts"), list):
        receipts.update(str(receipt) for receipt in row["source_receipts"])
    result["receipts"] = sorted(receipts)
    return result
