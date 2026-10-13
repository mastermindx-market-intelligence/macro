"""Filing observation state for Fundamental Forensics (FIF A21).

A pure vocabulary and record algebra for ``(issuer_cik, accession)`` filing
observation.  It names what an incremental discovery check actually saw —
checked-no-change vs index-quiet vs source outage vs absent vs budget — and
binds publication to a source generation id, so "no new filings" can never be
advertised as a fresh check and a re-render can never mint freshness.

This module is deliberately a LEAF: no I/O, no filesystem, no network and no
clock read.  Every time is an explicit aware-UTC ISO-8601 argument; nothing
here may import from ``collectors/`` or ``scripts/``.  It maps the two
incumbent observation machines (Wave-2 ``OBSERVATION_OUTCOMES`` and FF-1
``REASON_CODES``/outcome rows) onto one state set without changing any
receipt or log schema — wiring ``observe()`` into those lanes is a later,
separately commissioned step.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from typing import Any, Mapping

from engine.fundamental_forensics.health import FRESHNESS_BUDGET_SECONDS

FILING_OBSERVATION_SCHEMA = "fundamental_forensics.filing_observation_state/v1"

#: What one observation of one (issuer, filing-or-index) actually saw.
OBSERVATION_STATES = (
    "new_filing",
    "new_content",
    "checked_no_change",
    "index_quiet",
    "source_outage",
    "absent_at_source",
    "budget_exhausted",
    "check_failed",
    "not_applicable",
)

#: The source answered authoritatively; only these advance
#: ``last_successful_check_at``.  ``index_quiet`` is excluded on purpose: an
#: index diff that skipped this issuer is NOT a byte-level check.
SUCCESSFUL_CHECK_STATES = frozenset(
    {"new_filing", "new_content", "checked_no_change", "absent_at_source"}
)

FRESHNESS = ("current", "stale", "never_checked")

#: What a publication pointer was minted from.  The generation id names the
#: immutable source object (bundle id / snapshot id / issuer manifest id).
GENERATION_KINDS = ("disclosure_bundle", "source_snapshot", "issuer_manifest")

# Wave-2 ``OBSERVATION_OUTCOMES`` (acquisition.py) → state.  ``missing`` is
# resolved through ``missing_cause`` below: an explicit SEC 404, a bounded
# byte budget, or a transient retry exhaustion are three different facts.
WAVE2_OUTCOME_MAP = {
    "unchanged": "checked_no_change",
    "new_filing": "new_filing",
    "new_content": "new_content",
    # ``missing`` is not one state: an explicit SEC 404, a bounded byte
    # budget and an exhausted transient retry are three different facts, so
    # this member is resolved through ``missing_cause`` in
    # ``classify_wave2_outcome`` rather than mapped to a single state.
    "missing": None,
}
WAVE2_MISSING_CAUSE_STATE = {
    "http_404": "absent_at_source",
    "byte_budget": "budget_exhausted",
    "transient_exhausted": "source_outage",
}

# FF-1 ``broad_sec_store.REASON_CODES`` → state, total and exactly-once.
#   source_outage  — the SEC did not answer usably (429/5xx/timeout retries
#                    exhausted, full-index endpoint unavailable).
#   budget_exhausted — the source answered but this run refused to pay the
#                    bytes/issuers: ``response_too_large`` is the bounded-ingest
#                    cap (classify_fetch_error, broad_sec_store.py:559),
#                    ``edgar_index_too_large`` the master.zip caps
#                    (broad_sec_store.py:893,917,933), ``queue_overflow`` the
#                    Company Facts byte/run budget and affected-issuer cap
#                    ("Company Facts byte budget exhausted",
#                    broad_sec_store.py:2925,2929; cap bounds :3243,3250), and
#                    ``historical_submissions_budget_exhausted`` the historical
#                    shard budget.
#   check_failed   — integrity, binding, store, recovery and universe codes:
#                    our side cannot attest the check, not the source's.
BROAD_SEC_REASON_STATE = {
    "universe_invalid": "check_failed",
    "sec_429_exhausted": "source_outage",
    "sec_5xx_exhausted": "source_outage",
    "sec_timeout_exhausted": "source_outage",
    "response_too_large": "budget_exhausted",
    "invalid_sec_json": "check_failed",
    "source_binding_failure": "check_failed",
    "store_write_failure": "check_failed",
    "store_readback_failure": "check_failed",
    "issuer_manifest_invalid": "check_failed",
    "queue_overflow": "budget_exhausted",
    "historical_submissions_required": "check_failed",
    "edgar_index_unavailable": "source_outage",
    "edgar_index_too_large": "budget_exhausted",
    "edgar_index_invalid": "check_failed",
    "edgar_index_member_missing": "check_failed",
    "edgar_index_cik_mismatch": "check_failed",
    "edgar_index_gap": "check_failed",
    "edgar_index_correction_requires_reconciliation": "check_failed",
    "edgar_index_event_not_causally_admitted": "check_failed",
    "recovery_plan_required": "check_failed",
    "recovery_plan_invalid": "check_failed",
    "recovery_in_progress": "check_failed",
    "historical_submissions_conflict": "check_failed",
    "historical_submissions_budget_exhausted": "budget_exhausted",
}

_TIMESTAMP_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|\+00:00)$"
)
_CIK_RE = re.compile(r"^[0-9]{1,10}$")


class FilingObservationError(ValueError):
    """A filing-observation input is unusable; ``code`` names why."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


def _parse_timestamp(value: Any, *, field: str) -> datetime:
    if not isinstance(value, str) or not _TIMESTAMP_RE.fullmatch(value):
        raise FilingObservationError(
            f"{field} must be an aware UTC ISO-8601 timestamp (Z or +00:00): {value!r}",
            code="malformed_timestamp",
        )
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(None):
        raise FilingObservationError(
            f"{field} must be UTC: {value!r}", code="malformed_timestamp"
        )
    return parsed


def _canonical_cik(issuer_cik: Any) -> str:
    if isinstance(issuer_cik, bool) or isinstance(issuer_cik, int):
        text = str(issuer_cik)
    elif isinstance(issuer_cik, str):
        text = issuer_cik.strip()
    else:
        raise FilingObservationError(
            f"issuer_cik must be digits: {issuer_cik!r}", code="invalid_issuer_cik"
        )
    if not _CIK_RE.fullmatch(text):
        raise FilingObservationError(
            f"issuer_cik must be 1-10 digits: {issuer_cik!r}", code="invalid_issuer_cik"
        )
    return f"{int(text):010d}"


def _canonical_accession(accession: Any) -> str | None:
    if accession is None:
        return None
    if not isinstance(accession, str) or not accession.strip():
        raise FilingObservationError(
            f"accession must be a non-empty string or None: {accession!r}",
            code="invalid_accession",
        )
    return accession.strip()


def _record_id(issuer_cik: str, accession: str | None) -> str:
    canonical = json.dumps(
        [FILING_OBSERVATION_SCHEMA, issuer_cik, accession],
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return "ffobs_" + sha256(canonical.encode("utf-8")).hexdigest()[:32]


def _canonical_publication(publication: Any) -> dict[str, Any] | None:
    if publication is None:
        return None
    if not isinstance(publication, Mapping):
        raise FilingObservationError(
            "publication must be an object or null", code="invalid_publication"
        )
    return dict(publication)


def classify_wave2_outcome(outcome: Any, *, missing_cause: str | None = None) -> str:
    """Map one Wave-2 observation outcome onto a state, failing closed."""
    if not isinstance(outcome, str) or outcome not in WAVE2_OUTCOME_MAP:
        raise FilingObservationError(f"unknown Wave-2 outcome: {outcome!r}", code="unknown_outcome")
    if outcome != "missing":
        return WAVE2_OUTCOME_MAP[outcome]
    state = WAVE2_MISSING_CAUSE_STATE.get(missing_cause)
    if state is None:
        raise FilingObservationError(
            f"missing outcome requires missing_cause in {sorted(WAVE2_MISSING_CAUSE_STATE)}: "
            f"{missing_cause!r}",
            code="missing_cause_required",
        )
    return state


def classify_broad_sec_observation(
    outcome: Any,
    *,
    reason_code: str | None = None,
    submissions_unchanged: bool | None = None,
    new_accessions: Any = None,
) -> str:
    """Map one FF-1 observation row onto a state, failing closed.

    ``observed_no_relevant_change`` is an index-diff-only fact — the issuer was
    not in the work set, so no Submissions bytes were checked — and can never
    become ``checked_no_change`` (broad_sec_store.py:3510-3517).  An
    ``observed`` row with ``submissions_unchanged`` reuses the prior manifest
    (broad_sec_store.py:3769-3782) and is the byte-level no-change; new
    accessions are a new filing; anything else that forced a fresh manifest is
    changed content (broad_sec_store.py:3790+).
    """
    if outcome == "observed_no_relevant_change":
        return "index_quiet"
    if outcome == "observed":
        if submissions_unchanged is True:
            return "checked_no_change"
        accessions = tuple(new_accessions or ())
        if accessions:
            return "new_filing"
        if submissions_unchanged is False and not accessions:
            return "new_content"
        raise FilingObservationError(
            "observed outcome requires submissions_unchanged or new_accessions evidence",
            code="observation_evidence_required",
        )
    if outcome == "failed":
        if reason_code is None:
            raise FilingObservationError(
                "failed outcome requires a reason_code", code="reason_code_required"
            )
        state = BROAD_SEC_REASON_STATE.get(reason_code)
        if state is None:
            raise FilingObservationError(
                f"unknown FF-1 reason_code: {reason_code!r}", code="unknown_reason_code"
            )
        return state
    raise FilingObservationError(f"unknown FF-1 outcome: {outcome!r}", code="unknown_outcome")


def _validated_prior(
    prior: Mapping[str, Any], *, record_id: str
) -> tuple[datetime, datetime | None, dict[str, Any] | None, Any]:
    if not isinstance(prior, Mapping):
        raise FilingObservationError("prior must be a mapping", code="record_mismatch")
    if prior.get("record_id") != record_id:
        raise FilingObservationError(
            f"prior record_id {prior.get('record_id')!r} does not match {record_id!r}",
            code="record_mismatch",
        )
    if "last_checked_at" not in prior or prior.get("last_checked_at") is None:
        raise FilingObservationError(
            "prior record has no last_checked_at", code="record_mismatch"
        )
    last_checked = _parse_timestamp(prior.get("last_checked_at"), field="prior.last_checked_at")
    last_successful = prior.get("last_successful_check_at")
    last_successful_dt = (
        _parse_timestamp(last_successful, field="prior.last_successful_check_at")
        if last_successful is not None
        else None
    )
    publication = _canonical_publication(prior.get("publication"))
    return last_checked, last_successful_dt, publication, prior.get("state")


def observe(
    *,
    issuer_cik: str,
    accession: str | None,
    state: str,
    checked_at: str,
    prior: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Record one observation of one (issuer, filing) as a new immutable dict.

    No clock, run id or render id enters the record id: a re-delivered row at
    the same check time with the same state is idempotent, an out-of-order
    delivery cannot rewind the check clock, and only a state in
    ``SUCCESSFUL_CHECK_STATES`` advances ``last_successful_check_at``.
    """
    if state not in OBSERVATION_STATES:
        raise FilingObservationError(f"unknown observation state: {state!r}", code="unknown_state")
    checked = _parse_timestamp(checked_at, field="checked_at")
    cik = _canonical_cik(issuer_cik)
    canonical_accession = _canonical_accession(accession)
    record_id = _record_id(cik, canonical_accession)
    if prior is not None:
        last_checked, carried_successful, publication, prior_state = _validated_prior(
            prior, record_id=record_id
        )
        if checked < last_checked:
            raise FilingObservationError(
                f"checked_at {checked_at!r} precedes prior last_checked_at "
                f"{prior.get('last_checked_at')!r}",
                code="clock_regression",
            )
        if checked == last_checked and prior_state != state:
            raise FilingObservationError(
                f"conflicting duplicate at {checked_at!r}: {prior_state!r} vs {state!r}",
                code="conflicting_duplicate",
            )
        # One carry rule spans fresh rows and duplicate deliveries alike: a
        # successful state stamps this check, anything else carries the prior
        # successful check forward untouched — so a re-delivered row at the
        # same time with the same state reproduces the prior record exactly.
        last_successful = checked if state in SUCCESSFUL_CHECK_STATES else carried_successful
    else:
        publication = None
        last_successful = checked if state in SUCCESSFUL_CHECK_STATES else None
    return {
        "schema": FILING_OBSERVATION_SCHEMA,
        "record_id": record_id,
        "issuer_cik": cik,
        "accession": canonical_accession,
        "state": state,
        "last_checked_at": checked.isoformat().replace("+00:00", "Z"),
        "last_successful_check_at": (
            last_successful.isoformat().replace("+00:00", "Z") if last_successful else None
        ),
        "publication": publication,
    }


def mark_published(
    record: Mapping[str, Any],
    *,
    generation_kind: str,
    generation_id: str,
    published_at: str,
) -> dict[str, Any]:
    """Bind a publication pointer to a source generation id, monotonically.

    Publishing requires a successful check behind the record, cannot rewind an
    existing publication to an older stamp, and an identical republish returns
    a record equal to the input.  The record itself is never mutated.
    """
    if generation_kind not in GENERATION_KINDS:
        raise FilingObservationError(
            f"unknown generation kind: {generation_kind!r}", code="unknown_generation_kind"
        )
    if not isinstance(generation_id, str) or not generation_id.strip():
        raise FilingObservationError(
            "generation_id must be a non-empty string", code="invalid_generation_id"
        )
    published = _parse_timestamp(published_at, field="published_at")
    if not isinstance(record, Mapping):
        raise FilingObservationError("record must be a mapping", code="record_mismatch")
    cik = _canonical_cik(record.get("issuer_cik"))
    canonical_accession = _canonical_accession(record.get("accession"))
    record_id = _record_id(cik, canonical_accession)
    if record.get("record_id") != record_id:
        raise FilingObservationError(
            f"record record_id {record.get('record_id')!r} does not match {record_id!r}",
            code="record_mismatch",
        )
    if record.get("schema") != FILING_OBSERVATION_SCHEMA:
        raise FilingObservationError(
            f"record schema {record.get('schema')!r} is not {FILING_OBSERVATION_SCHEMA!r}",
            code="record_mismatch",
        )
    last_successful = record.get("last_successful_check_at")
    if last_successful is None:
        raise FilingObservationError(
            "cannot publish a record with no successful check",
            code="publish_without_successful_check",
        )
    _parse_timestamp(last_successful, field="record.last_successful_check_at")
    existing = _canonical_publication(record.get("publication"))
    if existing is not None and existing.get("published_at") is not None:
        existing_at = _parse_timestamp(existing.get("published_at"), field="publication.published_at")
        if published < existing_at:
            raise FilingObservationError(
                f"published_at {published_at!r} precedes existing "
                f"{existing.get('published_at')!r}",
                code="publication_regression",
            )
        if (
            published == existing_at
            and existing.get("generation_kind") == generation_kind
            and existing.get("generation_id") == generation_id
        ):
            # Identical republish: idempotent, record unchanged field-for-field.
            return dict(record)
    updated = dict(record)
    updated["publication"] = {
        "generation_kind": generation_kind,
        "generation_id": generation_id,
        "published_at": published.isoformat().replace("+00:00", "Z"),
    }
    return updated


def freshness(
    record: Mapping[str, Any],
    *,
    as_of: str,
    sla_seconds: int = FRESHNESS_BUDGET_SECONDS,
) -> str:
    """Classify a record's successful-check age against the SLA at ``as_of``.

    ``never_checked`` when no successful check exists (an outage or quiet index
    row is not freshness), ``stale`` past ``sla_seconds``, else ``current``;
    an ``as_of`` earlier than the successful check is a clock-order violation.
    """
    if isinstance(sla_seconds, bool) or not isinstance(sla_seconds, (int, float)) or sla_seconds <= 0:
        raise FilingObservationError(
            f"sla_seconds must be a positive number: {sla_seconds!r}", code="invalid_sla_seconds"
        )
    evaluated = _parse_timestamp(as_of, field="as_of")
    if not isinstance(record, Mapping):
        raise FilingObservationError("record must be a mapping", code="record_mismatch")
    last_successful = record.get("last_successful_check_at")
    if last_successful is None:
        return "never_checked"
    checked = _parse_timestamp(last_successful, field="record.last_successful_check_at")
    if evaluated < checked:
        raise FilingObservationError(
            f"as_of {as_of!r} precedes the successful check at {last_successful!r}",
            code="clock_order_violation",
        )
    age = (evaluated - checked).total_seconds()
    return "stale" if age > sla_seconds else "current"
