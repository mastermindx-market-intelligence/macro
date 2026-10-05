"""Prospective BioCatalyst outcome accrual from replay-validated history facts.

This is a narrow BC-P5 adapter over existing owners:
- Record History owns source snapshots and registry change facts.
- BC-M0a family-clock receipts own the accrual start boundary.
- BC-O1b OperationalStore remains the sole outcome-record writer.

The first admitted slice is trial_progression_termination only. A registry
overallStatus change can be carried as the source-native status after the family
clock opened. This module does not infer endpoint success, materiality, issuer
exposure, probability, ranking, or investment action, and it never backfills a
fact known before the recorded clock start.
"""
from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
import re
from typing import Any, Mapping

from engine.biocatalyst.operational_store import AppendReceipt, OperationalStore
from engine.sector_intelligence.contracts import (
    ContractRegistry,
    ContractValidationError,
    canonical_json_sha256,
)


OUTCOME_RECORD_KIND = "outcome_observation"
OUTCOME_CONTRACT_ID = "biocatalyst_outcome_record.v1"
ACTIVATION_CONTRACT_ID = "biocatalyst_family_clock_activation.v1"
HISTORY_FACT_CONTRACT_ID = "trial_registry_change_fact.v1"
HISTORY_SNAPSHOT_CONTRACT_ID = "trial_history_source_snapshot.v1"

TRIAL_PROGRESSION_FAMILY = "trial_progression_termination"
TRIAL_STATUS_FACT_KIND = "registry_status_changed"

_SOURCE_STATUS = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_NCT = re.compile(r"^NCT[0-9]{8}$")
_SHA256 = re.compile(r"^[a-f0-9]{64}$")


class OutcomeAccrualError(ValueError):
    """One bounded refusal while projecting a source fact into BC-O1b."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _record(value: object, code: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise OutcomeAccrualError(code)
    return value


@lru_cache(maxsize=1)
def _contract_registry() -> ContractRegistry:
    return ContractRegistry()


def _registered(
    contract_id: str,
    value: Mapping[str, Any],
    code: str,
) -> None:
    try:
        _contract_registry().validate(contract_id, value)
    except ContractValidationError as exc:
        raise OutcomeAccrualError(code) from exc


def _utc(value: object, code: str) -> tuple[str, datetime]:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise OutcomeAccrualError(code)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OutcomeAccrualError(code) from exc
    if parsed.tzinfo is None:
        raise OutcomeAccrualError(code)
    return value, parsed.astimezone(timezone.utc)


def _verify_self_hash(
    document: Mapping[str, Any], field: str, code: str
) -> str:
    digest = document.get(field)
    if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
        raise OutcomeAccrualError(code)
    probe = {key: value for key, value in document.items() if key != field}
    if canonical_json_sha256(probe) != digest:
        raise OutcomeAccrualError(code)
    return digest


def _activation_start(activation: Mapping[str, Any]) -> tuple[str, datetime]:
    _registered(
        ACTIVATION_CONTRACT_ID,
        activation,
        "OUTCOME_ACCRUAL_ACTIVATION_NOT_ADMITTED",
    )
    if (
        activation.get("contract_id") != ACTIVATION_CONTRACT_ID
        or activation.get("schema_version") != "1.0.0"
        or activation.get("family_id") != TRIAL_PROGRESSION_FAMILY
        or activation.get("clock_state") != "opened"
        or activation.get("backfill") != "forbidden_no_history_recorded"
        or activation.get("authority") != "facts_and_context_only"
        or activation.get("blockers") != []
        or activation.get("ineligible_source_ids") != []
        or activation.get("unsatisfied_preconditions") != []
        or set(activation.get("satisfied_preconditions") or ()) != {
            "frozen_policy_version",
            "eligible_source_registration",
            "o1b_outcome_writer",
        }
    ):
        raise OutcomeAccrualError("OUTCOME_ACCRUAL_ACTIVATION_NOT_ADMITTED")
    policy_version = activation.get("policy_version")
    if not isinstance(policy_version, str) or not re.fullmatch(r"m0a\.[0-9]{1,4}", policy_version):
        raise OutcomeAccrualError("OUTCOME_ACCRUAL_ACTIVATION_NOT_ADMITTED")
    return _utc(
        activation.get("accrual_start_known_at"),
        "OUTCOME_ACCRUAL_ACTIVATION_NOT_ADMITTED",
    )


def _validate_fact(fact: Mapping[str, Any]) -> str:
    _verify_self_hash(fact, "fact_payload_sha256", "OUTCOME_ACCRUAL_FACT_HASH_INVALID")
    _registered(
        HISTORY_FACT_CONTRACT_ID,
        fact,
        "OUTCOME_ACCRUAL_FACT_INVALID",
    )
    if (
        fact.get("contract_id") != HISTORY_FACT_CONTRACT_ID
        or fact.get("schema_version") != "1.0.0"
        or fact.get("source_fact") is not True
        or fact.get("current_only") is not False
        or fact.get("interpretation") != "registry_record_changed"
        or fact.get("protocol_change_asserted") is not False
        or fact.get("materiality_assessed") is not False
    ):
        raise OutcomeAccrualError("OUTCOME_ACCRUAL_FACT_INVALID")
    if fact.get("kind") != TRIAL_STATUS_FACT_KIND:
        raise OutcomeAccrualError("OUTCOME_ACCRUAL_FACT_KIND_NOT_ADMITTED")
    nct_id = fact.get("nct_id")
    if not isinstance(nct_id, str) or _NCT.fullmatch(nct_id) is None:
        raise OutcomeAccrualError("OUTCOME_ACCRUAL_SOURCE_BINDING_INVALID")
    return nct_id


def _validate_snapshot_binding(
    fact: Mapping[str, Any], snapshot: Mapping[str, Any], nct_id: str
) -> tuple[str, datetime, str, datetime]:
    _verify_self_hash(
        snapshot,
        "snapshot_payload_sha256",
        "OUTCOME_ACCRUAL_SNAPSHOT_HASH_INVALID",
    )
    _registered(
        HISTORY_SNAPSHOT_CONTRACT_ID,
        snapshot,
        "OUTCOME_ACCRUAL_SNAPSHOT_INVALID",
    )
    if (
        snapshot.get("contract_id") != HISTORY_SNAPSHOT_CONTRACT_ID
        or snapshot.get("schema_version") != "1.0.0"
    ):
        raise OutcomeAccrualError("OUTCOME_ACCRUAL_SNAPSHOT_INVALID")
    if (
        snapshot.get("nct_id") != nct_id
        or snapshot.get("source_snapshot_id") != fact.get("after_source_snapshot_ref")
        or snapshot.get("source_version") != fact.get("after_source_version")
    ):
        raise OutcomeAccrualError("OUTCOME_ACCRUAL_SOURCE_BINDING_INVALID")

    retrieved_literal, retrieved = _utc(
        snapshot.get("retrieved_at"), "OUTCOME_ACCRUAL_SNAPSHOT_CLOCK_INVALID"
    )
    transaction_literal, transaction = _utc(
        snapshot.get("transaction_from"), "OUTCOME_ACCRUAL_SNAPSHOT_CLOCK_INVALID"
    )
    if transaction < retrieved:
        raise OutcomeAccrualError("OUTCOME_ACCRUAL_SNAPSHOT_CLOCK_INVALID")
    return retrieved_literal, retrieved, transaction_literal, transaction


def build_trial_progression_outcome(
    *,
    fact: Mapping[str, Any],
    after_snapshot: Mapping[str, Any],
    activation: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Project one post-activation registry status change into BC-O1b.

    None means the source fact was already knowable before the immutable
    family-clock start. That is an explicit no-backfill disposition, not a
    negative outcome.
    """

    fact = _record(fact, "OUTCOME_ACCRUAL_FACT_INVALID")
    after_snapshot = _record(
        after_snapshot, "OUTCOME_ACCRUAL_SNAPSHOT_INVALID"
    )
    activation = _record(
        activation, "OUTCOME_ACCRUAL_ACTIVATION_NOT_ADMITTED"
    )

    _start_literal, accrual_start = _activation_start(activation)
    nct_id = _validate_fact(fact)
    (
        retrieved_literal,
        retrieved_at,
        transaction_literal,
        _transaction_at,
    ) = _validate_snapshot_binding(fact, after_snapshot, nct_id)

    if retrieved_at < accrual_start:
        return None

    source_status = fact.get("after_value")
    if not isinstance(source_status, str) or _SOURCE_STATUS.fullmatch(source_status) is None:
        raise OutcomeAccrualError("OUTCOME_ACCRUAL_SOURCE_STATUS_INVALID")

    fact_digest = str(fact["fact_payload_sha256"])
    payload = {
        "contract_id": OUTCOME_CONTRACT_ID,
        "schema_version": "1.0.0",
        "outcome_id": f"oc:trial_progression:{fact_digest[:24]}",
        "family_id": TRIAL_PROGRESSION_FAMILY,
        "subject_ref": f"nct:{nct_id}",
        "seed_layer": "study_conduct",
        "value": source_status.casefold(),
        "value_authority": "source_native_status_only",
        "censoring_state": "right_censored_open_window",
        # The policy calls this a revisable state, so even source statuses such
        # as COMPLETED or TERMINATED remain non-terminal in the outcome ledger.
        "terminality": "non_terminal",
        # Record History provides a day-granular source submission date. Do not
        # manufacture midnight precision: use the exact retained retrieval time.
        "effective_at": retrieved_literal,
        "known_at": retrieved_literal,
        "observed_at": transaction_literal,
        "evidence_refs": [f"internal:ctgov_change_{fact_digest[:32]}"],
        "policy_version": str(activation["policy_version"]),
        "resolver_type": "deterministic_source_statement",
        "revision_of": None,
    }
    _registered(
        OUTCOME_CONTRACT_ID,
        payload,
        "OUTCOME_ACCRUAL_OUTPUT_INVALID",
    )
    return payload


def append_trial_progression_outcome(
    store: OperationalStore,
    *,
    fact: Mapping[str, Any],
    after_snapshot: Mapping[str, Any],
    activation: Mapping[str, Any],
    recorded_at: str | None = None,
) -> AppendReceipt | None:
    """Append one eligible status-change outcome through the existing O1b writer."""

    payload = build_trial_progression_outcome(
        fact=fact,
        after_snapshot=after_snapshot,
        activation=activation,
    )
    if payload is None:
        return None
    fact_digest = str(fact["fact_payload_sha256"])
    return store.append(
        OUTCOME_RECORD_KIND,
        payload,
        idempotency_key=f"bcp5:trial_progression:{fact_digest[:24]}",
        recorded_at=recorded_at,
    )


__all__ = [
    "OutcomeAccrualError",
    "append_trial_progression_outcome",
    "build_trial_progression_outcome",
]
