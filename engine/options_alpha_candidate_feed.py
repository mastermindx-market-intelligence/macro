"""Pure source-only options-alpha research-candidate feed composer (inactive).

This module is the implementation carrier for the OA-1C research-candidate
composer. It is inactive until the four named activation preconditions are
cleared by the upstream owning program. It performs no runtime publication,
durable write, network I/O, or clock inference, and always requires an explicit
decision clock.

The composer derives ``options.alpha_candidate_feed/v2`` from canonical campaign
evidence and measured microstructure receipts. It reuses the campaign engine's
ledger and receipt machinery instead of duplicating prefix or identity math.

All authority remains false. No scores, ranks, sizes, issues, trades, training
signals, neural-web feeds, calibration claims, P&L calculations, tactical
events, or directional probability claims are produced.
"""
from __future__ import annotations

import hashlib
import copy
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Sequence

from jsonschema import Draft202012Validator, FormatChecker

import engine.options_signal_campaign as campaign_engine
from engine.options_signal_campaign import (
    CAMPAIGN_SCHEMA,
    CampaignContractError,
    LedgerSnapshot,
    canonical_bytes as _campaign_canonical_bytes,
    validate_campaign,
)

CANDIDATE_FEED_SCHEMA = "options.alpha_candidate_feed/v2"
CANDIDATE_IDENTITY_SCHEMA = "options.alpha_candidate_identity/v1"
CANDIDATE_FEED_ACTIVATION_RECEIPT_SCHEMA = (
    "options.alpha_candidate_feed_activation_receipt/v1"
)
MICROSTRUCTURE_SCHEMA = "options.trade_nbbo_microstructure/v1"
POLICY_SCHEMA = "options.alpha_candidate_formation_policy/v2"
EVENT_STAGE_SCHEMA = "live_flow.event_stage/v1"

POLICY_PATH = "research/options_estate/options_alpha_candidate_formation_policy_v2.json"
ACTIVATION_RECEIPT_PATH = (
    "research/options_estate/options_alpha_candidate_feed_activation_receipt_v1.json"
)
ACTIVATION_RECEIPT_SCHEMA_FILENAME = (
    "options.alpha_candidate_feed_activation_receipt.v1.schema.json"
)
CANDIDATE_FEED_V2_SCHEMA_FILENAME = "options.alpha_candidate_feed.v2.schema.json"
CANDIDATE_IDENTITY_SCHEMA_FILENAME = "options.alpha_candidate_identity.v1.schema.json"
PUBLICATION_RECEIPT_SCHEMA_FILENAME = (
    "options.alpha_candidate_feed_publication_receipt.v1.schema.json"
)
MICROSTRUCTURE_SCHEMA_FILENAME = "options.trade_nbbo_microstructure.v1.schema.json"

ACTIVATION_PRECONDITIONS: tuple[str, ...] = (
    "oa1t_measured_source_consumer_proven",
    "ad1t2_consumer_availability_production_accepted",
    "campaign_integrity_publication_runtime_accepted",
    "source_collision_review_clear",
)

REASON_CODES: tuple[str, ...] = (
    "BEFORE_POLICY_FREEZE",
    "BEFORE_ACTIVATION_BOUNDARY",
    "CAMPAIGN_RECEIPT_INVALID",
    "CAMPAIGN_NOT_PROSPECTIVE",
    "INSUFFICIENT_CAMPAIGN_MEMBERS",
    "FINAL_MEMBER_MICROSTRUCTURE_MISSING",
    "NO_VALID_NBBO_MEASUREMENT",
    "EVIDENCE_CLOCK_INVALID",
    "SOURCE_EXPLICITLY_STALE_OR_UNAVAILABLE",
    "UPSTREAM_AUTHORITY_VIOLATION",
)

FALSE_AUTHORITY: dict[str, bool] = {
    "may_originate": False,
    "may_rank": False,
    "may_score": False,
    "may_gate": False,
    "may_size": False,
    "may_issue": False,
    "may_trade": False,
    "may_publish_pick": False,
    "may_train_prophet": False,
    "may_feed_neural_web": False,
    "may_select": False,
    "may_escalate": False,
    "may_compute_option_pnl": False,
    "may_infer_bullish_bearish_probability": False,
    "may_create_tactical_event": False,
}

COMPOSER_ID = (
    "oacf_composer_"
    + hashlib.sha256(b"oacf_composer|oa1c|inactive|v2").hexdigest()[:24]
)
IMPLEMENTATION_CARRIER_DEFAULT = (
    "codex/options-alpha-candidate-feed-20261002 inactive implementation carrier"
)


class CandidateFeedContractError(ValueError):
    """Raised when a caller input, evidence receipt, or output violates the frozen
    OA-1C inactive composer contract."""


# ---------------------------------------------------------------------------
# Strict finite-JSON loader (no NaN, no Infinity, no duplicate keys).
# ---------------------------------------------------------------------------


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise CandidateFeedContractError(f"duplicate JSON object key {key!r}")
        value[key] = item
    return value


def _strict_loads(raw: str | bytes) -> Any:
    return json.loads(
        raw,
        object_pairs_hook=_reject_duplicate_pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            CandidateFeedContractError(f"non-standard JSON constant {token}")
        ),
    )


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CandidateFeedContractError("value is not canonical finite JSON") from exc


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _stable_id(prefix: str, *parts: object) -> str:
    raw = "|".join(str(part) for part in parts).encode("utf-8")
    return f"{prefix}_{_sha256(raw)[:24]}"


# ---------------------------------------------------------------------------
# Canonical UTC clock helper.
# ---------------------------------------------------------------------------


def _canonical_utc(value: object, field: str) -> tuple[str, datetime]:
    if type(value) is not str or not value.endswith("Z"):
        raise CandidateFeedContractError(f"{field} must be canonical UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise CandidateFeedContractError(f"{field} is not a timestamp") from exc
    parsed = parsed.astimezone(timezone.utc)
    canonical = parsed.isoformat().replace("+00:00", "Z")
    if canonical != value:
        raise CandidateFeedContractError(f"{field} must be canonical UTC")
    return canonical, parsed


def _utc(value: object, field: str) -> datetime:
    return _canonical_utc(value, field)[1]


def _is_finite_number(value: object) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return math.isfinite(float(value))
    if isinstance(value, Decimal):
        return value.is_finite()
    return False


# ---------------------------------------------------------------------------
# Schema-validator cache.
# ---------------------------------------------------------------------------


_REPO_ROOT = Path(__file__).resolve().parent.parent


@lru_cache(maxsize=8)
def _schema_validator(filename: str) -> Draft202012Validator:
    path = _REPO_ROOT / "contracts/options" / filename
    try:
        schema = _strict_loads(path.read_bytes())
    except (OSError, ValueError, TypeError) as exc:
        raise CandidateFeedContractError(f"cannot load schema {path}") from exc
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _validate_schema(row: dict[str, Any], filename: str) -> None:
    errors = sorted(
        _schema_validator(filename).iter_errors(row), key=lambda err: list(err.path)
    )
    if errors:
        error = errors[0]
        where = ".".join(str(part) for part in error.path) or "<root>"
        raise CandidateFeedContractError(
            f"{filename} validation failed at {where}: {error.message}"
        )


# ---------------------------------------------------------------------------
# Caller-supplied input validation.
# ---------------------------------------------------------------------------


def _validate_decision_clock(value: str) -> datetime:
    return _utc(value, "decision_clock")


@dataclass(frozen=True)
class SourceHealth:
    """Explicit caller-supplied source health.

    No wrapper freshening: when ``stale`` or ``unavailable`` is True the
    composer downgrades to a ``degraded`` state and retains prior identity
    and history.
    """

    stale: bool = False
    unavailable: bool = False

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "SourceHealth":
        if value is None:
            return cls()
        if not isinstance(value, dict):
            raise CandidateFeedContractError("source_health must be a dict")
        stale = value.get("stale", False)
        unavailable = value.get("unavailable", False)
        if not isinstance(stale, bool) or not isinstance(unavailable, bool):
            raise CandidateFeedContractError("source_health flags must be booleans")
        return cls(stale=stale, unavailable=unavailable)


def _validate_policy(policy: dict[str, Any]) -> None:
    _validate_schema(policy, "options.alpha_candidate_formation_policy.v2.schema.json")
    formation = policy["formation"]
    if formation["campaign_phase"] != "prospective_after_rule_freeze":
        raise CandidateFeedContractError(
            "policy.formation.campaign_phase must be prospective_after_rule_freeze"
        )
    if formation["minimum_member_count"] != 2:
        raise CandidateFeedContractError("policy.formation.minimum_member_count must be 2")
    if formation["minimum_source_print_count"] != 1:
        raise CandidateFeedContractError(
            "policy.formation.minimum_source_print_count must be 1"
        )
    if formation["minimum_nbbo_valid_print_count"] != 1:
        raise CandidateFeedContractError(
            "policy.formation.minimum_nbbo_valid_print_count must be 1"
        )
    if formation["minimum_nbbo_premium_coverage_exclusive"] != 0.0:
        raise CandidateFeedContractError(
            "policy.formation.minimum_nbbo_premium_coverage_exclusive must be 0.0"
        )
    if not formation["first_qualifying_revision_frozen"]:
        raise CandidateFeedContractError(
            "policy.formation.first_qualifying_revision_frozen must be true"
        )
    if formation["outcomes_read_during_formation"]:
        raise CandidateFeedContractError(
            "policy.formation.outcomes_read_during_formation must be false"
        )
    if formation["direction_inferred_during_formation"]:
        raise CandidateFeedContractError(
            "policy.formation.direction_inferred_during_formation must be false"
        )
    if tuple(policy["activation_preconditions"]) != ACTIVATION_PRECONDITIONS:
        raise CandidateFeedContractError(
            "policy activation_preconditions must be the exact four prerequisites in order"
        )


def _validate_activation_receipt(
    receipt: dict[str, Any] | None,
    *,
    policy_freeze_at: str,
) -> dict[str, Any]:
    if receipt is None:
        return {
            "activation_receipt_id": None,
            "activation_receipt_digest_sha256": None,
            "activation_receipt_schema": CANDIDATE_FEED_ACTIVATION_RECEIPT_SCHEMA,
            "activation_receipt_path": ACTIVATION_RECEIPT_PATH,
            "activation_preconditions": list(ACTIVATION_PRECONDITIONS),
            "all_preconditions_cleared": False,
            "fence_state": "pre_policy_freeze",
            "policy_freeze_at": None,
            "activation_boundary_at": None,
        }
    _validate_schema(receipt, ACTIVATION_RECEIPT_SCHEMA_FILENAME)
    for field in ("policy_freeze_at", "activation_boundary_at"):
        if receipt.get(field) is not None:
            _canonical_utc(receipt[field], f"activation_receipt.{field}")
    # Normalise: the schema-validated receipt uses `receipt_id`; downstream
    # code expects namespaced `activation_receipt_id` and a digest. We bind
    # those here so the rest of the composer never reaches into the receipt
    # directly.
    digest = _sha256(canonical_bytes(receipt))
    if not receipt.get("all_preconditions_cleared", False):
        # A receipt that has not cleared all preconditions is treated as no
        # receipt at all for fence classification.
        raise CandidateFeedContractError(
            "activation receipt supplied but all_preconditions_cleared is false"
        )
    if receipt["activation_disposition"]["state"] != "eligible":
        raise CandidateFeedContractError(
            "activation receipt activation_disposition.state must be eligible"
        )
    if tuple(receipt["preconditions"]) != ACTIVATION_PRECONDITIONS:
        raise CandidateFeedContractError(
            "activation receipt preconditions must be the exact four prerequisites in order"
        )
    if receipt["policy_freeze_at"] != policy_freeze_at:
        raise CandidateFeedContractError(
            "activation receipt policy_freeze_at disagrees with caller policy freeze"
        )
    receipt_freeze = _utc(receipt["policy_freeze_at"], "activation policy freeze")
    receipt_boundary = (
        _utc(receipt["activation_boundary_at"], "activation boundary")
        if receipt["activation_boundary_at"] is not None
        else None
    )
    if receipt_boundary is None or receipt_boundary <= receipt_freeze:
        raise CandidateFeedContractError(
            "activation receipt activation_boundary_at must not precede policy_freeze_at"
        )
    normalised = dict(receipt)
    normalised["activation_receipt_id"] = receipt.get("receipt_id")
    normalised["activation_receipt_digest_sha256"] = digest
    return normalised


# ---------------------------------------------------------------------------
# Microstructure validation.
# ---------------------------------------------------------------------------


def _validate_microstructure_map(
    value: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise CandidateFeedContractError("microstructure_map must be a dict")
    out: dict[str, dict[str, Any]] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key:
            raise CandidateFeedContractError(
                "microstructure_map keys must be non-empty strings"
            )
        if not isinstance(item, dict):
            raise CandidateFeedContractError(
                f"microstructure_map[{key!r}] must be a dict"
            )
        _validate_schema(item, MICROSTRUCTURE_SCHEMA_FILENAME)
        if item["source_event_id"] != key:
            raise CandidateFeedContractError(
                f"microstructure_map[{key!r}] source_event_id disagrees with key"
            )
        for numeric in (
            "source_print_count",
            "nbbo_valid_print_count",
        ):
            if not isinstance(item[numeric], int) or item[numeric] < 0:
                raise CandidateFeedContractError(
                    f"microstructure_map[{key!r}].{numeric} must be a non-negative integer"
                )
        if not _is_finite_number(item["nbbo_premium_coverage"]):
            raise CandidateFeedContractError(
                f"microstructure_map[{key!r}].nbbo_premium_coverage must be finite"
            )
        if float(item["nbbo_premium_coverage"]) < 0.0 or float(
            item["nbbo_premium_coverage"]
        ) > 1.0:
            raise CandidateFeedContractError(
                f"microstructure_map[{key!r}].nbbo_premium_coverage out of range"
            )
        if not _is_finite_number(item["nbbo_covered_premium_usd"]):
            raise CandidateFeedContractError(
                f"microstructure_map[{key!r}].nbbo_covered_premium_usd must be finite"
            )
        if float(item["nbbo_covered_premium_usd"]) < 0.0:
            raise CandidateFeedContractError(
                f"microstructure_map[{key!r}].nbbo_covered_premium_usd must be >= 0"
            )
        if not _is_finite_number(item["source_premium_usd"]):
            raise CandidateFeedContractError(
                f"microstructure_map[{key!r}].source_premium_usd must be finite"
            )
        if float(item["source_premium_usd"]) < 0.0:
            raise CandidateFeedContractError(
                f"microstructure_map[{key!r}].source_premium_usd must be >= 0"
            )
        out[key] = item
    return out


# ---------------------------------------------------------------------------
# Candidate identity + formation computation.
# ---------------------------------------------------------------------------


def _candidate_identity(
    policy_id: str,
    campaign_id: str,
    first_qualifying_campaign_revision_id: str,
) -> str:
    return _stable_id(
        "oacnd",
        CANDIDATE_IDENTITY_SCHEMA,
        policy_id,
        campaign_id,
        first_qualifying_campaign_revision_id,
    )


def _feed_id(parts: Sequence[str]) -> str:
    return _stable_id("oacf", *parts)


# ---------------------------------------------------------------------------
# Prior-feed strict validation.
# ---------------------------------------------------------------------------


def _validate_prior_feed(
    prior: dict[str, Any] | None,
    *,
    policy_digest: str,
    policy_freeze_at: str,
    activation_boundary_at: str | None,
    campaigns: LedgerSnapshot,
    microstructure_map: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    if prior is None:
        return None
    if not isinstance(prior, dict):
        raise CandidateFeedContractError("prior_feed must be a dict")
    _validate_schema(prior, CANDIDATE_FEED_V2_SCHEMA_FILENAME)
    if prior["policy"]["policy_id"] != "oa_member_persistent_measured_campaign/v2":
        raise CandidateFeedContractError("prior_feed.policy.policy_id is not accepted")
    if prior["policy"]["policy_digest_sha256"] != policy_digest:
        raise CandidateFeedContractError(
            "prior_feed.policy.policy_digest_sha256 disagrees with current policy"
        )
    frozen_policy_checks = {
        "policy_id": "oa_member_persistent_measured_campaign/v2",
        "policy_version": 1,
        "policy_digest_sha256": policy_digest,
        "policy_freeze_at": policy_freeze_at,
        "activation_boundary_at": activation_boundary_at,
        "policy_freeze_cleared": True,
        "activation_boundary_cleared": True,
        "candidate_identity_schema": CANDIDATE_IDENTITY_SCHEMA,
    }
    for candidate in prior["formed_candidates"]:
        frozen = candidate["frozen_formation"]
        for field, expected in frozen_policy_checks.items():
            if frozen[field] != expected:
                raise CandidateFeedContractError(
                    "prior_feed frozen policy disagrees with passed policy or receipt: "
                    + field
                )
    expected_digest = prior["header"]["header_digest_sha256"]
    sealed = copy.deepcopy(prior)
    sealed["header"]["header_digest_sha256"] = ""
    actual_digest = _sha256(canonical_bytes(sealed))
    if actual_digest != expected_digest:
        raise CandidateFeedContractError(
            "prior_feed.header seal does not match canonical blank-header bytes"
        )
    source_receipt = dict(prior["source_receipts"]["campaigns"])
    source_receipt.pop("schema", None)
    try:
        prior_source_ordinal = campaign_engine.verify_campaign_receipt(
            source_receipt, campaigns, campaigns.label
        )
    except CampaignContractError as exc:
        raise CandidateFeedContractError(
            f"prior_feed campaign prefix receipt is invalid: {exc}"
        ) from exc
    seen: set[str] = set()
    seen_campaigns: set[str] = set()
    formed = prior["formed_candidates"]
    if prior["header"]["formed_candidate_count"] != len(formed):
        raise CandidateFeedContractError("prior_feed formed candidate count disagrees")
    for candidate in formed:
        if not isinstance(candidate, dict) or "candidate_id" not in candidate:
            raise CandidateFeedContractError("prior_feed.formed candidate missing candidate_id")
        cid = candidate["candidate_id"]
        campaign_id = candidate.get("campaign_id")
        if cid in seen or campaign_id in seen_campaigns:
            raise CandidateFeedContractError(
                "prior_feed.formed_candidates must have unique candidate_ids and campaign_ids"
            )
        seen.add(cid)
        seen_campaigns.add(campaign_id)
        _validate_prior_candidate_source(
            candidate,
            campaigns=campaigns,
            microstructure_map=microstructure_map,
            prior_source_ordinal=prior_source_ordinal,
        )
        disposition = candidate.get("current_disposition")
        if (
            not isinstance(disposition, dict)
            or candidate.get("state") != disposition.get("state")
            or candidate.get("reasons") != disposition.get("reasons")
        ):
            raise CandidateFeedContractError("prior_feed formed candidate disposition aliases disagree")
    if prior.get("publication_claim", {}).get("claim") != (
        "source_only_no_publication_effect"
    ):
        raise CandidateFeedContractError(
            "prior_feed.publication_claim.claim must be source-only"
        )
    return prior


def _candidate_source_receipt(candidate: dict[str, Any]) -> dict[str, Any]:
    receipt = dict(candidate["frozen_formation"]["source_prefix_receipt"])
    receipt.pop("schema", None)
    return receipt


def _validate_prior_candidate_source(
    candidate: dict[str, Any],
    *,
    campaigns: LedgerSnapshot,
    microstructure_map: dict[str, dict[str, Any]],
    prior_source_ordinal: int,
) -> None:
    try:
        formation_ordinal = campaign_engine.verify_campaign_receipt(
            _candidate_source_receipt(candidate), campaigns, campaigns.label
        )
    except CampaignContractError as exc:
        raise CandidateFeedContractError(
            f"prior_feed formation campaign prefix is invalid: {exc}"
        ) from exc

    if formation_ordinal == 0 or formation_ordinal > campaigns.count:
        raise CandidateFeedContractError("prior_feed formation prefix is empty")
    formation_row = campaigns.rows[formation_ordinal - 1].value
    frozen = candidate["frozen_formation"]
    formation_micro = candidate["formation_micro"]

    expected_identity = _candidate_identity(
        frozen["policy_id"], candidate["campaign_id"], frozen["campaign_revision_id"]
    )
    field_checks = (
        ("candidate_id", candidate["candidate_id"], expected_identity),
        (
            "campaign_id",
            candidate["campaign_id"],
            formation_row["campaign_id"],
        ),
        (
            "campaign_revision_id",
            frozen["campaign_revision_id"],
            formation_row["campaign_revision_id"],
        ),
        (
            "first_qualifying_campaign_revision_id",
            candidate["first_qualifying_campaign_revision_id"],
            frozen["campaign_revision_id"],
        ),
        ("formed_at", frozen["formed_at"], formation_row["formed_at"]),
        (
            "campaign_member_count",
            frozen["campaign_member_count"],
            formation_row["descriptive"]["member_count"],
        ),
        (
            "final_member_event_id",
            frozen["final_member_event_id"],
            formation_row["members"][-1]["source_event_id"],
        ),
        (
            "measured_source_print_count",
            frozen["measured_source_print_count"],
            formation_micro["source_print_count"],
        ),
        (
            "measured_nbbo_valid_print_count",
            frozen["measured_nbbo_valid_print_count"],
            formation_micro["nbbo_valid_print_count"],
        ),
        (
            "measured_nbbo_premium_coverage",
            frozen["measured_nbbo_premium_coverage"],
            formation_micro["nbbo_premium_coverage"],
        ),
    )
    mismatched = [name for name, left, right in field_checks if left != right]
    if mismatched:
        raise CandidateFeedContractError(
            "prior_feed formation fields disagree with physical source: "
            + ", ".join(mismatched)
        )

    source_micro = microstructure_map.get(frozen["final_member_event_id"])
    expected_micro_digest = formation_micro["schema_digest_sha256"]
    micro_field_checks = (
        ("source_print_count", "measured_source_print_count"),
        (
            "nbbo_valid_print_count",
            "measured_nbbo_valid_print_count",
        ),
        (
            "nbbo_premium_coverage",
            "measured_nbbo_premium_coverage",
        ),
        ("source_premium_usd", None),
        ("nbbo_covered_premium_usd", None),
        ("schema", None),
    )
    mismatched_micro = [
        field
        for field, frozen_key in micro_field_checks
        if source_micro is not None
        and (
            formation_micro[field] != source_micro[field]
            or (
                frozen_key is not None
                and frozen[frozen_key] != source_micro[field]
            )
        )
    ]
    if mismatched_micro:
        raise CandidateFeedContractError(
            "prior_feed formation microstructure fields disagree with source: "
            + ", ".join(mismatched_micro)
        )

    row_digest = _sha256(_campaign_canonical_bytes(formation_row))
    expected_evidence_digest = _sha256(
        canonical_bytes(
            {
                "campaign": row_digest,
                "micro": expected_micro_digest,
                "policy": frozen["policy_digest_sha256"],
                "campaign_revision_id": frozen["campaign_revision_id"],
                "campaign_id": candidate["campaign_id"],
            }
        )
    )
    if frozen["evidence_digest_sha256"] != expected_evidence_digest:
        raise CandidateFeedContractError(
            "prior_feed formation evidence digest is invalid"
        )

    matching_rows = [
        row for row in campaigns.rows
        if row.value["campaign_id"] == candidate["campaign_id"]
    ]
    if not matching_rows:
        raise CandidateFeedContractError(
            "prior_feed campaign history is absent from physical source"
        )
    formation_physical_row = next(
        (
            row for row in matching_rows
            if row.value["campaign_revision_id"] == frozen["campaign_revision_id"]
        ),
        None,
    )
    if (
        formation_physical_row is None
        or formation_physical_row.ordinal != formation_ordinal
    ):
        raise CandidateFeedContractError(
            "prior_feed formation revision is not at its physical prefix endpoint"
        )
    after_formation = [
        row
        for row in matching_rows
        if formation_ordinal <= row.ordinal <= prior_source_ordinal
    ]
    after_formation.sort(key=lambda row: row.value["revision_number"])
    expected_ids = [row.value["campaign_revision_id"] for row in after_formation]
    actual_ids = [
        entry["campaign_revision_id"] for entry in candidate["versioned_updates"]
    ]
    if actual_ids != expected_ids:
        raise CandidateFeedContractError(
            "prior_feed versioned updates disagree with exact physical source membership"
        )
    current_physical_row = after_formation[-1]
    current_revision_id = candidate["current_campaign_revision_id"]
    if current_physical_row.value["campaign_revision_id"] != current_revision_id:
        raise CandidateFeedContractError(
            "prior_feed current revision disagrees with physical source"
        )
    for entry, physical_row in zip(candidate["versioned_updates"], after_formation):
        value = physical_row.value
        expected = {
            "campaign_revision_id": value["campaign_revision_id"],
            "revision_number": int(value["revision_number"]),
            "revision_digest_sha256": _sha256(_campaign_canonical_bytes(value)),
            "formed_at": value["formed_at"],
        }
        for field, expected_value in expected.items():
            if entry[field] != expected_value:
                raise CandidateFeedContractError(
                    "prior_feed versioned update metadata disagrees with physical source: "
                    + field
                )


# ---------------------------------------------------------------------------
# Campaign-row check + fine-graining per campaign.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _CampaignView:
    row: dict[str, Any]
    ordinal: int
    sha256: str


def _validated_campaign_views(
    campaigns: LedgerSnapshot,
) -> tuple[list[_CampaignView], list[dict[str, Any]]]:
    """Validate every campaign row. Returns (views, poisoned_reasons):
    - views: rows that pass schema + authority check
    - poisoned_reasons: rows that flip an authority bool True → these become
      abstentions with UPSTREAM_AUTHORITY_VIOLATION (graceful stand-alone)
    """
    views: list[_CampaignView] = []
    seen_revisions: set[str] = set()
    poisoned_reasons: list[dict[str, Any]] = []
    for item in campaigns.rows:
        # Authority drift check FIRST: a campaign that has flipped any
        # authority bool to True is structurally invalid as a formation
        # input. We tag it with UPSTREAM_AUTHORITY_VIOLATION and skip
        # full schema validation so the composer abstains cleanly
        # instead of crashing with a generic schema error.
        auth = item.value.get("authority", {})
        flipped = [
            key
            for key in FALSE_AUTHORITY
            if bool(auth.get(key, False))
        ]
        if flipped:
            poisoned_reasons.append(
                {
                    "campaign": item.value,
                    "reasons": ["UPSTREAM_AUTHORITY_VIOLATION"],
                    "flipped_keys": flipped,
                }
            )
            continue

        # Either degraded (source explicit stale/unavailable with prior
        # identity) or plain abstention.
        # Reuse the campaign engine's strict validator (delegate, don't
        # duplicate) — schema, identity, formed_at clock, policies,
        # authority.
        try:
            validate_campaign(item.value)
        except CampaignContractError as exc:
            raise CandidateFeedContractError(
                f"campaign revision failed canonical validation: {exc}"
            ) from exc
        revision_id = item.value["campaign_revision_id"]
        if revision_id in seen_revisions:
            raise CandidateFeedContractError("duplicate campaign_revision_id in ledger")
        seen_revisions.add(revision_id)
        views.append(_CampaignView(item.value, item.ordinal, item.sha256))
    return views, poisoned_reasons


def _campaign_prefix_receipt(campaigns: LedgerSnapshot) -> dict[str, Any]:
    return {
        "path": campaigns.label,
        "records": campaigns.count,
        "prefix_sha256": campaigns.sha256,
        "schema": CAMPAIGN_SCHEMA,
    }


def _microstructure_receipt(
    micro_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    rows = [
        _campaign_canonical_bytes(item)
        for _, item in sorted(micro_map.items())
    ]
    digest = _sha256(b"".join(rows))
    return {
        "schema": MICROSTRUCTURE_SCHEMA,
        "entries_count": len(micro_map),
        "entries_digest_sha256": digest,
    }


# ---------------------------------------------------------------------------
# Per-campaign reasoning.
# ---------------------------------------------------------------------------


def _campaign_reasons(
    campaign: dict[str, Any],
    micro_map: dict[str, dict[str, Any]],
    *,
    policy_freeze_at: datetime,
    activation_boundary: datetime | None,
    observation: datetime,
    source_health: SourceHealth,
) -> tuple[list[str], dict[str, dict[str, Any]] | None, dict[str, Any] | None]:
    """Return (reasons, candidate_payload or None) per the frozen formation
    rule. Pure: never reads outcome ledgers or runs ambient clock."""

    reasons: list[str] = []
    formed_at = _utc(campaign["formed_at"], "campaign.formed_at")

    if formed_at < policy_freeze_at:
        reasons.append("BEFORE_POLICY_FREEZE")
    if activation_boundary is None or formed_at < activation_boundary:
        reasons.append("BEFORE_ACTIVATION_BOUNDARY")
    if campaign.get("evidence_phase") != "prospective_after_rule_freeze":
        reasons.append("CAMPAIGN_NOT_PROSPECTIVE")
    member_count = int(campaign["descriptive"]["member_count"])
    if member_count < 2:
        reasons.append("INSUFFICIENT_CAMPAIGN_MEMBERS")

    # Authority check — refuse if any campaign authority bool flipped true.
    auth = campaign.get("authority", {})
    if any(bool(auth.get(key, False)) for key in FALSE_AUTHORITY):
        reasons.append("UPSTREAM_AUTHORITY_VIOLATION")

    final_member = campaign["members"][-1]
    final_event_id = final_member["source_event_id"]
    micro = micro_map.get(final_event_id)

    if micro is None:
        reasons.append("FINAL_MEMBER_MICROSTRUCTURE_MISSING")

    if micro is not None:
        if (
            not isinstance(micro["source_print_count"], int)
            or micro["source_print_count"] < 1
        ):
            reasons.append("NO_VALID_NBBO_MEASUREMENT")
        if (
            not isinstance(micro["nbbo_valid_print_count"], int)
            or micro["nbbo_valid_print_count"] < 1
        ):
            reasons.append("NO_VALID_NBBO_MEASUREMENT")
        if not _is_finite_number(micro["nbbo_premium_coverage"]):
            reasons.append("NO_VALID_NBBO_MEASUREMENT")
        elif float(micro["nbbo_premium_coverage"]) <= 0.0:
            reasons.append("NO_VALID_NBBO_MEASUREMENT")
        micro_available = _utc(micro["available_at"], "micro.available_at")
        if micro_available > observation:
            reasons.append("EVIDENCE_CLOCK_INVALID")

    if source_health.stale or source_health.unavailable:
        reasons.append("SOURCE_EXPLICITLY_STALE_OR_UNAVAILABLE")

    return reasons, (micro if micro is not None else None), final_member


def _revision_is_qualifying(
    campaign: dict[str, Any],
    micro_map: dict[str, dict[str, Any]],
    *,
    policy_freeze_at: datetime,
    activation_boundary: datetime | None,
    observation: datetime,
) -> bool:
    """Qualification uses the preregistered decision-clock evidence cutoff."""
    reasons, _, _ = _campaign_reasons(
        campaign,
        micro_map,
        policy_freeze_at=policy_freeze_at,
        activation_boundary=activation_boundary,
        observation=observation,
        source_health=SourceHealth(),
    )
    return not reasons


def _prior_formation_ordinal(
    prior_candidate: dict[str, Any],
    campaigns: LedgerSnapshot,
) -> int:
    try:
        return campaign_engine.verify_campaign_receipt(
            _candidate_source_receipt(prior_candidate), campaigns, campaigns.label
        )
    except CampaignContractError as exc:
        raise CandidateFeedContractError(
            f"prior_feed formation campaign prefix is invalid: {exc}"
        ) from exc


def _build_candidate_payload(
    *,
    campaign: dict[str, Any],
    micro: dict[str, Any] | None,
    policy: dict[str, Any],
    policy_digest: str,
    policy_freeze_at: datetime,
    activation_boundary: datetime | None,
    observation: datetime,
    prior_candidate: dict[str, Any] | None,
    candidate_id: str,
    campaigns: LedgerSnapshot,
    first_qualifying_revision_id: str,
    formation_row_ordinal: int,
    all_revisions: tuple[dict[str, Any], ...],
    micro_map_for_formation_micro: dict[str, Any],
    current_physical_ordinal: int,
    revision_ordinal_by_revision_id: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Compose a single research_candidate record. ``prior_candidate`` (when
    provided by a validated prior feed) preserves the immutable
    first_observation/decision clocks for this identity
    and seeds the versioned_updates list. ``observation`` here is the
    actual composer-call decision clock, not backdated to the
    campaign formed_at. ``all_revisions`` is the chronologically-ordered
    tuple of revisions belonging to this campaign_id; only revisions
    whose physical ordinal lies in [formation_row_ordinal,
    current_physical_ordinal] become entries in ``versioned_updates`` so
    pre-formation revisions cannot leak in and the history is exactly
    the physical-prefix membership."""

    campaign_revision_id = campaign["campaign_revision_id"]
    formation_revision = campaigns.rows[formation_row_ordinal - 1].value
    formed_at = _utc(formation_revision["formed_at"], "campaign.formed_at")
    campaign_digest = _sha256(_campaign_canonical_bytes(campaign))

    if prior_candidate is not None:
        # Prior exists: never reach into the current micro_map for the
        # formation event's micro. Use the immutable prior formation
        # micro directly so a later missing current micro cannot crash
        # the composer or rewrite formation evidence.
        source_prefix_receipt = copy.deepcopy(
            prior_candidate["frozen_formation"]["source_prefix_receipt"]
        )
        first_qualifying = prior_candidate["first_qualifying_campaign_revision_id"]
        frozen_formation = copy.deepcopy(prior_candidate["frozen_formation"])
        formation_micro = copy.deepcopy(prior_candidate["formation_micro"])
        formation_micro_digest = formation_micro["schema_digest_sha256"]
        evidence_digest = frozen_formation["evidence_digest_sha256"]
        first_observed_at = prior_candidate["first_observed_at"]
        decision_at = prior_candidate["decision_at"]
        versioned_updates = list(
            prior_candidate.get("versioned_updates", ())
        )
    else:
        # First-time formation: look up current micro_map for the
        # formation event's micro. The micro MUST be present in the
        # current map at formation time; missing is a hard schema error.
        formation_micro = micro_map_for_formation_micro[
            formation_revision["members"][-1]["source_event_id"]
        ]
        formation_micro_digest = _sha256(_campaign_canonical_bytes(formation_micro))
        source_prefix_receipt = {
            "path": campaigns.label,
            "records": formation_row_ordinal,
            "prefix_sha256": hashlib.sha256(
                campaigns.prefix_raw(formation_row_ordinal)
            ).hexdigest(),
            "schema": CAMPAIGN_SCHEMA,
        }
        evidence_digest = _sha256(
            canonical_bytes(
                {
                    "campaign": _sha256(
                        _campaign_canonical_bytes(formation_revision)
                    ),
                    "micro": formation_micro_digest,
                    "policy": policy_digest,
                    "campaign_revision_id": first_qualifying_revision_id,
                    "campaign_id": formation_revision["campaign_id"],
                }
            )
        )
        first_qualifying = first_qualifying_revision_id
        first_observed_at = observation.strftime("%Y-%m-%dT%H:%M:%SZ")
        decision_at = first_observed_at
        versioned_updates = [
            {
                "campaign_revision_id": first_qualifying_revision_id,
                "revision_number": int(formation_revision["revision_number"]),
                "revision_digest_sha256": _sha256(
                    _campaign_canonical_bytes(formation_revision)
                ),
                "formed_at": formation_revision["formed_at"],
                "observed_at": decision_at,
                "candidate_identity_unchanged": True,
            }
        ]

    # Append a versioned_update entry for every revision in the physical
    # prefix membership [formation_row_ordinal, current_physical_ordinal],
    # skipping ones already recorded in the prior feed (which retain their
    # original observed_at — those are immutable). This way the
    # versioned_updates list reflects EXACTLY the physical-prefix membership
    # for this identity, never pre-formation revisions, and the latest
    # (current) revision is the tail entry.
    seen_revision_ids = {
        entry["campaign_revision_id"] for entry in versioned_updates
    }
    for rev in all_revisions:
        rev_id = rev["campaign_revision_id"]
        if rev_id in seen_revision_ids:
            continue
        rev_ordinal = (
            revision_ordinal_by_revision_id.get(rev_id, current_physical_ordinal)
            if revision_ordinal_by_revision_id is not None
            else current_physical_ordinal
        )
        if rev_ordinal < formation_row_ordinal or rev_ordinal > current_physical_ordinal:
            continue
        rev_digest = _sha256(_campaign_canonical_bytes(rev))
        versioned_updates.append(
            {
                "campaign_revision_id": rev_id,
                "revision_number": int(rev["revision_number"]),
                "revision_digest_sha256": rev_digest,
                "formed_at": rev["formed_at"],
                "observed_at": observation.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "candidate_identity_unchanged": True,
            }
        )
        seen_revision_ids.add(rev_id)

    if micro is not None:
        micro_digest = _sha256(_campaign_canonical_bytes(micro))
        measured: dict[str, Any] | None = {
            "source_print_count": int(micro["source_print_count"]),
            "nbbo_valid_print_count": int(micro["nbbo_valid_print_count"]),
            "nbbo_premium_coverage": float(micro["nbbo_premium_coverage"]),
            "source_premium_usd": float(micro["source_premium_usd"]),
            "nbbo_covered_premium_usd": float(micro["nbbo_covered_premium_usd"]),
            "schema": MICROSTRUCTURE_SCHEMA,
            "schema_digest_sha256": micro_digest,
        }
    else:
        measured = None

    frozen = {
        "campaign_revision_id": first_qualifying_revision_id,
        "formed_at": formation_revision["formed_at"],
        "candidate_identity_schema": CANDIDATE_IDENTITY_SCHEMA,
        "policy_id": policy["policy_id"],
        "policy_version": int(policy["policy_version"]),
        "policy_digest_sha256": policy_digest,
        "policy_freeze_at": policy_freeze_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "activation_boundary_at": (
            activation_boundary.strftime("%Y-%m-%dT%H:%M:%SZ")
            if activation_boundary is not None
            else None
        ),
        "policy_freeze_cleared": formed_at >= policy_freeze_at,
        "activation_boundary_cleared": (
            activation_boundary is None or formed_at >= activation_boundary
        ),
        **(
            frozen_formation
            if prior_candidate is not None
            else {"source_prefix_receipt": source_prefix_receipt}
        ),
    }
    if prior_candidate is None:
        frozen.update(
            {
                "campaign_member_count": int(
                    formation_revision["descriptive"]["member_count"]
                ),
                "final_member_event_id": formation_revision["members"][-1][
                    "source_event_id"
                ],
                "measured_source_print_count": int(
                    formation_micro["source_print_count"]
                ),
                "measured_nbbo_valid_print_count": int(
                    formation_micro["nbbo_valid_print_count"]
                ),
                "measured_nbbo_premium_coverage": float(
                    formation_micro["nbbo_premium_coverage"]
                ),
                "all_evidence_legs_within_decision_cutoff": True,
                "evidence_digest_sha256": evidence_digest,
            }
        )

    return {
        "candidate_id": candidate_id,
        "campaign_id": campaign["campaign_id"],
        "first_qualifying_campaign_revision_id": first_qualifying,
        "current_campaign_revision_id": campaign_revision_id,
        "source_formed_at": formation_revision["formed_at"],
        "first_observed_at": first_observed_at,
        "decision_at": decision_at,
        "frozen_formation": frozen,
        "formation_micro": {
            "source_print_count": int(formation_micro["source_print_count"]),
            "nbbo_valid_print_count": int(
                formation_micro["nbbo_valid_print_count"]
            ),
            "nbbo_premium_coverage": float(
                formation_micro["nbbo_premium_coverage"]
            ),
            "source_premium_usd": float(formation_micro["source_premium_usd"]),
            "nbbo_covered_premium_usd": float(
                formation_micro["nbbo_covered_premium_usd"]
            ),
            "schema": MICROSTRUCTURE_SCHEMA,
            "schema_digest_sha256": formation_micro_digest,
        },
        "measured": measured,
        "evidence_digests": {
            "campaign_row_digest_sha256": campaign_digest,
            "microstructure_row_digest_sha256": (
                micro_digest if measured is not None else None
            ),
            "policy_digest_sha256": policy_digest,
        },
        "missingness": [],
        "contradictions": [],
        "state": "research_candidate",
        "reasons": [],
        "current_revision": {
            "campaign_revision_id": campaign_revision_id,
            "revision_number": int(campaign["revision_number"]),
            "formed_at": campaign["formed_at"],
        },
        "versioned_updates": versioned_updates,
    }


def _build_abstention(
    campaign: dict[str, Any],
    *,
    observation: datetime,
    reasons: list[str],
) -> dict[str, Any]:
    return {
        "campaign_id": campaign["campaign_id"],
        "campaign_revision_id": campaign["campaign_revision_id"],
        "formed_at": campaign["formed_at"],
        "reasons": sorted(set(reasons)),
        "state": "abstain",
        "first_observed_at": observation.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _build_degraded(
    campaign: dict[str, Any],
    *,
    observation: datetime,
    prior_candidate: dict[str, Any] | None,
    reasons: list[str],
) -> dict[str, Any]:
    retained_id = (
        prior_candidate["candidate_id"] if prior_candidate is not None else None
    )
    first_observed = (
        prior_candidate["first_observed_at"]
        if prior_candidate is not None
        else observation.strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    return {
        "campaign_id": campaign["campaign_id"],
        "campaign_revision_id": campaign["campaign_revision_id"],
        "formed_at": campaign["formed_at"],
        "first_observed_at": first_observed,
        "retained_candidate_id": retained_id,
        "reasons": sorted(set(reasons)),
        "state": "degraded",
        "first_observation_preserved": prior_candidate is not None,
        "decision_preserved": prior_candidate is not None,
    }


# ---------------------------------------------------------------------------
# Public composer entry.
# ---------------------------------------------------------------------------


def compose_candidate_feed(
    *,
    campaigns: LedgerSnapshot,
    microstructure_map: dict[str, Any] | None = None,
    policy: dict[str, Any],
    activation_receipt: dict[str, Any] | None = None,
    observation_clock: str,
    prior_feed: dict[str, Any] | None = None,
    source_health: dict[str, Any] | None = None,
    implementation_carrier: str = IMPLEMENTATION_CARRIER_DEFAULT,
    deterministic_seed: str | None = None,
    feed_id: str | None = None,
    policy_freeze_at: str | None = None,
) -> dict[str, Any]:
    """Compose an options.alpha_candidate_feed/v2 artifact from caller-supplied
    inputs.

    The composer is **pure**: no network, no filesystem, no ambient clocks, no
    outcome ledger reads. All clocks and receipts must be passed in. The
    returned object validates against the frozen
    ``options.alpha_candidate_feed/v2`` schema with ``additionalProperties:
    false`` and finite JSON."""

    if not isinstance(campaigns, LedgerSnapshot):
        raise CandidateFeedContractError("campaigns must be a LedgerSnapshot")
    _validate_policy(policy)
    decision_clock = _validate_decision_clock(observation_clock)
    health = SourceHealth.from_dict(source_health)
    micro_map = _validate_microstructure_map(microstructure_map)
    if policy_freeze_at is None:
        raise CandidateFeedContractError(
            "policy_freeze_at must be supplied explicitly (no local NYSE inference)"
        )
    activation = _validate_activation_receipt(
        activation_receipt, policy_freeze_at=policy_freeze_at
    )
    freeze_at = _utc(policy_freeze_at, "policy_freeze_at")

    activation_boundary: datetime | None = None
    if activation.get("activation_receipt_id") is not None:
        if activation.get("activation_boundary_at") is None:
            raise CandidateFeedContractError(
                "activation receipt cleared preconditions but lacks activation_boundary_at"
            )
        activation_boundary = _utc(
            activation["activation_boundary_at"], "activation.activation_boundary_at"
        )

    # Fence-state classification — caller-supplied clocks do not change the
    # fence; the activation receipt's persisted activation_boundary_at does.
    if freeze_at > decision_clock:
        fence_state = "pre_policy_freeze"
    elif activation_boundary is None or activation_boundary > decision_clock:
        fence_state = "post_policy_freeze_pre_activation"
    else:
        fence_state = "post_activation"

    policy_digest = _sha256(canonical_bytes(policy))
    prior = _validate_prior_feed(
        prior_feed,
        policy_digest=policy_digest,
        policy_freeze_at=policy_freeze_at,
        activation_boundary_at=activation.get("activation_boundary_at"),
        campaigns=campaigns,
        microstructure_map=micro_map,
    )
    campaign_views, poisoned_reasons = _validated_campaign_views(campaigns)
    source_prefix_receipt = _campaign_prefix_receipt(campaigns)
    micro_receipt = _microstructure_receipt(micro_map)

    abstentions: list[dict[str, Any]] = []
    formed_candidates: list[dict[str, Any]] = []

    # Group revisions by campaign_id; ONE candidate per campaign, with the
    # latest revision as "current" and the earliest qualifying revision as
    # "first_qualifying" (frozen at formation).
    campaigns_by_id: dict[str, list[dict[str, Any]]] = {}
    view_ordinal_by_revision_id: dict[str, int] = {}
    poisoned_by_revision = {
        item["campaign"]["campaign_revision_id"]: item["reasons"]
        for item in poisoned_reasons
    }
    for view in campaign_views:
        cid = view.row["campaign_id"]
        campaigns_by_id.setdefault(cid, []).append(view.row)
        view_ordinal_by_revision_id[view.row["campaign_revision_id"]] = view.ordinal
    for item in campaigns.rows:
        row = item.value
        if row.get("campaign_revision_id") in poisoned_by_revision:
            campaigns_by_id.setdefault(row["campaign_id"], []).append(row)
            view_ordinal_by_revision_id[row["campaign_revision_id"]] = item.ordinal
    for cid in campaigns_by_id:
        campaigns_by_id[cid].sort(
            key=lambda row: view_ordinal_by_revision_id[row["campaign_revision_id"]]
        )

    for cid, revisions in campaigns_by_id.items():
        current = revisions[-1]
        prior_candidate = None
        # Prior lookup covers ALL formed records (formed_candidates,
        # including degraded state) so a candidate that has ever formed
        # never loses its identity in the next replay. The legacy
        # ``candidates`` array is also consulted for older feeds.
        if prior is not None:
            prior_pool: list[dict[str, Any]] = []
            prior_pool.extend(prior["formed_candidates"])
            for item in prior_pool:
                if item.get("campaign_id") == cid:
                    prior_candidate = item
                    break

        if prior_candidate is None:
            first_qualifying = next(
                (
                    row
                    for row in revisions
                    if _revision_is_qualifying(
                        row,
                        micro_map,
                        policy_freeze_at=freeze_at,
                        activation_boundary=activation_boundary,
                        observation=decision_clock,
                    )
                ),
                None,
            )
            first_qualifying_revision_id = (
                first_qualifying["campaign_revision_id"]
                if first_qualifying is not None
                else None
            )
            candidate_id = _candidate_identity(
                policy["policy_id"],
                cid,
                first_qualifying_revision_id,
            )
        else:
            first_qualifying_revision_id = prior_candidate[
                "first_qualifying_campaign_revision_id"
            ]
            candidate_id = prior_candidate["candidate_id"]

        if prior_candidate is not None:
            formation_row_ordinal = _prior_formation_ordinal(
                prior_candidate, campaigns
            )
        elif first_qualifying_revision_id is not None:
            formation_row_ordinal = view_ordinal_by_revision_id[
                first_qualifying_revision_id
            ]

        # Current physical ordinal for this campaign_id — the tail revision
        # in the campaigns ledger. Used to bound versioned_updates and to
        # make current_revision reflect the actual physical source.
        current_physical_ordinal = view_ordinal_by_revision_id[
            current["campaign_revision_id"]
        ]

        if current["campaign_revision_id"] in poisoned_by_revision:
            reasons = list(poisoned_by_revision[current["campaign_revision_id"]])
            micro = None
        else:
            reasons, micro, _ = _campaign_reasons(
                current,
                micro_map,
                policy_freeze_at=freeze_at,
                activation_boundary=activation_boundary,
                observation=decision_clock,
                source_health=health,
            )

        # Late older micro: a microstructure record whose available_at
        # lies between formation formed_at and the current decision_clock
        # is accepted. The rule change to use decision_clock as the
        # observation parameter (instead of row.formed_at) means the
        # existing _campaign_reasons check (micro_available <=
        # observation) now admits the late-older case.

        disposition_state = "research_candidate"
        disposition_reasons: list[str] = []

        if reasons and first_qualifying_revision_id is not None:
            # A formed identity retains an explicit current disposition. Decide
            # between degraded (current measurement or evidence failure)
            # and abstain (policy/activation fences without measurement
            # failure).
            measurement_reasons = {
                "FINAL_MEMBER_MICROSTRUCTURE_MISSING",
                "NO_VALID_NBBO_MEASUREMENT",
                "EVIDENCE_CLOCK_INVALID",
                "SOURCE_EXPLICITLY_STALE_OR_UNAVAILABLE",
                "CAMPAIGN_RECEIPT_INVALID",
            }
            if "UPSTREAM_AUTHORITY_VIOLATION" in reasons:
                disposition_state = "abstain"
            elif any(reason in measurement_reasons for reason in reasons):
                disposition_state = "degraded"
            else:
                disposition_state = "abstain"
            disposition_reasons = sorted(set(reasons))

        formed_record: dict[str, Any] | None = None
        if first_qualifying_revision_id is not None:
            formed_record = _build_candidate_payload(
                campaign=current,
                micro=(micro if not disposition_reasons else None),
                policy=policy,
                policy_digest=policy_digest,
                policy_freeze_at=freeze_at,
                activation_boundary=activation_boundary,
                observation=decision_clock,
                candidate_id=candidate_id,
                campaigns=campaigns,
                first_qualifying_revision_id=first_qualifying_revision_id,
                formation_row_ordinal=formation_row_ordinal,
                all_revisions=tuple(revisions),
                prior_candidate=prior_candidate,
                micro_map_for_formation_micro=micro_map,
                current_physical_ordinal=current_physical_ordinal,
                revision_ordinal_by_revision_id=view_ordinal_by_revision_id,
            )
            # Add the unified formed_candidates envelope (current_disposition).
            # The legacy `candidates` and `degraded` arrays stay schema-clean
            # so older consumers keep validating against the v2 contract.
            formed_envelope = copy.deepcopy(formed_record)
            formed_envelope["state"] = disposition_state
            formed_envelope["reasons"] = (
                list(disposition_reasons) if disposition_reasons else []
            )
            formed_envelope["current_disposition"] = {
                "state": disposition_state,
                "reasons": list(disposition_reasons),
            }
            if disposition_reasons and not micro:
                formed_envelope["missingness"] = sorted(set(disposition_reasons))
            formed_candidates.append(formed_envelope)

        if formed_record is None:
            abstentions.append(
                _build_abstention(
                    current,
                    observation=decision_clock,
                    reasons=reasons,
                )
            )

    seed = deterministic_seed or _sha256(
        canonical_bytes(
            {
                "policy_digest": policy_digest,
                "campaigns_prefix": source_prefix_receipt["prefix_sha256"],
                "micro_digest": micro_receipt["entries_digest_sha256"],
                "decision": observation_clock,
            }
        )
    )

    generated_at = observation_clock
    if feed_id is None:
        feed_id = _feed_id(
            (
                CANDIDATE_FEED_SCHEMA,
                policy_digest,
                source_prefix_receipt["prefix_sha256"],
                micro_receipt["entries_digest_sha256"],
                seed,
                generated_at,
            )
        )

    policy_block = {
        "policy_id": policy["policy_id"],
        "policy_version": int(policy["policy_version"]),
        "policy_digest_sha256": policy_digest,
        "policy_path": POLICY_PATH,
        "policy_schema": POLICY_SCHEMA,
    }

    activation_block = {
        "activation_receipt_id": activation.get("activation_receipt_id"),
        "activation_receipt_digest_sha256": activation.get(
            "activation_receipt_digest_sha256"
        ),
        "activation_receipt_schema": CANDIDATE_FEED_ACTIVATION_RECEIPT_SCHEMA,
        "activation_receipt_path": ACTIVATION_RECEIPT_PATH,
        "activation_preconditions": list(ACTIVATION_PRECONDITIONS),
        "all_preconditions_cleared": bool(
            activation.get("all_preconditions_cleared", False)
        ),
        "fence_state": fence_state,
        "policy_freeze_at": policy_freeze_at,
        "activation_boundary_at": (
            activation.get("activation_boundary_at")
            if activation.get("activation_boundary_at") is not None
            else None
        ),
    }

    prior_receipt = (
        {
            "feed_id": prior["feed_id"],
            "schema": CANDIDATE_FEED_SCHEMA,
            "feed_digest_sha256": _sha256(canonical_bytes(prior)),
            "policy_id": prior["policy"]["policy_id"],
            "policy_digest_sha256": prior["policy"]["policy_digest_sha256"],
            "composed_at": prior["generated_at"],
            "first_observation_preserved": all(
                isinstance(item, dict) for item in prior["formed_candidates"]
            ),
            "candidate_identity_preserved": all(
                item.get("candidate_id") == _candidate_identity(
                    policy["policy_id"],
                    item["campaign_id"],
                    item["first_qualifying_campaign_revision_id"],
                )
                for item in prior["formed_candidates"]
            ),
        }
        if prior is not None
        else None
    )

    feed: dict[str, Any] = {
        "schema": CANDIDATE_FEED_SCHEMA,
        "schema_version": 1,
        "generated_at": generated_at,
        "feed_id": feed_id,
        "header": {
            "composer_id": COMPOSER_ID,
            "implementation_carrier": implementation_carrier,
            "eligibility_state": (
                "synthetic_until_publisher_validates_activation"
                if not bool(activation.get("all_preconditions_cleared", False))
                else "preregistered_inactive_until_activation"
            ),
            "deterministic_seed": seed,
            "abstention_count": len(abstentions),
            "formed_candidate_count": len(formed_candidates),
            "header_digest_sha256": "",  # filled below
        },
        "policy": policy_block,
        "activation": activation_block,
        "source_receipts": {
            "campaigns": source_prefix_receipt,
            "microstructure_map": micro_receipt,
            "prior_feed": prior_receipt,
        },
        "formed_candidates": formed_candidates,
        "abstentions": abstentions,
        "publication_claim": {
            "claim": "source_only_no_publication_effect",
            "claim_reason": (
                "The composition is pure and does not prove local durability, "
                "upload, consumer publication, or activation."
            ),
        },
        "authority": dict(FALSE_AUTHORITY),
    }

    # Header digest seals the entire feed bytes.
    feed_bytes = canonical_bytes(feed)
    feed["header"]["header_digest_sha256"] = _sha256(feed_bytes)

    _validate_schema(feed, CANDIDATE_FEED_V2_SCHEMA_FILENAME)
    return feed


# ---------------------------------------------------------------------------
# Diagnostic helpers (no I/O).
# ---------------------------------------------------------------------------


def summarise(feed: dict[str, Any]) -> dict[str, Any]:
    """Return a small diagnostic summary of a composed feed. Pure, no I/O."""
    return {
        "feed_id": feed["feed_id"],
        "generated_at": feed["generated_at"],
        "formed_candidate_count": feed["header"]["formed_candidate_count"],
        "abstention_count": feed["header"]["abstention_count"],
        "formed_candidate_count": feed["header"]["formed_candidate_count"],
        "policy_id": feed["policy"]["policy_id"],
        "policy_digest_sha256": feed["policy"]["policy_digest_sha256"],
        "fence_state": feed["activation"]["fence_state"],
        "all_preconditions_cleared": feed["activation"][
            "all_preconditions_cleared"
        ],
        "publication_claim": feed["publication_claim"]["claim"],
        "header_digest_sha256": feed["header"]["header_digest_sha256"],
    }


def _expected_publication_receipt_id(payload_digest: str) -> str:
    return "oacfr_" + hashlib.sha256(
        b"options.alpha_candidate_feed_publication_receipt/v1|"
        + payload_digest.encode("ascii")
    ).hexdigest()[:25]


def validate_publication_receipt_binding(
    *,
    feed: dict[str, Any],
    payload: bytes,
    receipt: dict[str, Any],
    receipt_published_at: str | None = None,
) -> None:
    """Validate a snapshot's exact binding, not an historical transition.

    The optional publication clock is the separately observed receipt object's
    external metadata. This pure function cannot prove IO or reconstruct an
    overwritten receipt. Publishers MUST also validate the transition below.
    """
    _validate_schema(feed, CANDIDATE_FEED_V2_SCHEMA_FILENAME)
    _validate_schema(receipt, PUBLICATION_RECEIPT_SCHEMA_FILENAME)
    if payload != canonical_bytes(feed):
        raise CandidateFeedContractError("publication receipt payload bytes do not canonicalize to the feed")
    unsealed = copy.deepcopy(feed)
    unsealed["header"]["header_digest_sha256"] = ""
    if feed["header"]["header_digest_sha256"] != _sha256(canonical_bytes(unsealed)):
        raise CandidateFeedContractError("publication feed header seal is invalid")
    digest = _sha256(payload)
    if receipt["receipt_id"] != _expected_publication_receipt_id(digest):
        raise CandidateFeedContractError("publication receipt identity is not derived from the payload hash")
    if receipt["feed_id"] != feed["feed_id"]:
        raise CandidateFeedContractError("publication receipt feed_id disagrees with payload")
    if receipt["payload_sha256"] != digest:
        raise CandidateFeedContractError("publication receipt payload hash disagrees with payload")
    if receipt["payload_bytes"] != len(payload):
        raise CandidateFeedContractError("publication receipt payload size disagrees with payload")
    prefix = {key: feed["source_receipts"]["campaigns"][key] for key in ("path", "records", "prefix_sha256")}
    if receipt["campaign_prefix"] != prefix:
        raise CandidateFeedContractError("publication receipt campaign prefix disagrees with payload")
    if receipt["r2"]["payload_sha256"] != digest:
        raise CandidateFeedContractError("publication receipt R2 payload hash disagrees with payload")
    composition = _canonical_utc(feed["generated_at"], "feed.generated_at")[1]
    durability = _canonical_utc(receipt["local_durability_confirmed_at"], "local_durability_confirmed_at")[1]
    confirmed = _canonical_utc(receipt["payload_r2_confirmed_at"], "payload_r2_confirmed_at")[1]
    if not composition <= durability <= confirmed:
        raise CandidateFeedContractError("publication receipt clock ordering requires composition <= durability <= confirmation")
    formed_ids = [item["candidate_id"] for item in feed["formed_candidates"]]
    if (len(formed_ids) != len(set(formed_ids))
            or feed["header"]["formed_candidate_count"] != len(formed_ids)
            or set(receipt["candidates"]) != set(formed_ids)):
        raise CandidateFeedContractError("publication receipt candidate map disagrees with payload")
    external_clock = (
        _canonical_utc(receipt_published_at, "receipt_published_at")[1]
        if receipt_published_at is not None else None
    )
    prior = receipt["prior_receipt"]
    if prior is not None and prior["receipt_id"] == receipt["receipt_id"]:
        raise CandidateFeedContractError("publication receipt cannot name itself as prior")
    for entry in receipt["candidates"].values():
        if entry["first_receipt_id"] == receipt["receipt_id"]:
            if entry["first_consumer_published_at"] is not None:
                raise CandidateFeedContractError("current first receipt must carry a null external publication clock")
        else:
            if prior is None or entry["first_consumer_published_at"] is None:
                raise CandidateFeedContractError("historical first receipt requires a prior anchor and carried external publication clock")
            first_clock = _canonical_utc(entry["first_consumer_published_at"], "first_consumer_published_at")[1]
            if external_clock is not None and first_clock > external_clock:
                raise CandidateFeedContractError("first publication is after the receipt object's publication metadata")
    # External LastModified can have coarser precision than producer timestamps.
    # It is not interchangeable with, or ordered against, payload confirmation.


def validate_publication_receipt_transition(
    *,
    feed: dict[str, Any],
    payload: bytes,
    receipt: dict[str, Any],
    prior_feed: dict[str, Any] | None = None,
    prior_payload: bytes | None = None,
    prior_receipt: dict[str, Any] | None = None,
    prior_receipt_published_at: str | None = None,
) -> None:
    """Validate bootstrap or exact carry from the last sealed pair.

    Only the immediately preceding pair and its separately observed receipt
    metadata are needed, regardless of history length. Older first-publication
    values are continuity assertions preserved from that validated pair, not
    newly proven historical provider effects. Callers must obtain the metadata
    with the same readback that supplies prior_receipt and enforce CAS in IO.
    """
    validate_publication_receipt_binding(feed=feed, payload=payload, receipt=receipt)
    prior_args = (prior_feed, prior_payload, prior_receipt, prior_receipt_published_at)
    if all(value is None for value in prior_args):
        if receipt["prior_receipt"] is not None or feed["source_receipts"]["prior_feed"] is not None:
            raise CandidateFeedContractError("bootstrap cannot claim an unvalidated prior pair")
        return
    if any(value is None for value in prior_args):
        raise CandidateFeedContractError("continuation requires the complete prior pair and external receipt metadata")
    validate_publication_receipt_binding(
        feed=prior_feed, payload=prior_payload, receipt=prior_receipt,
        receipt_published_at=prior_receipt_published_at,
    )
    expected_anchor = {key: prior_receipt[key] for key in ("receipt_id", "payload_sha256")}
    if receipt["prior_receipt"] != expected_anchor:
        raise CandidateFeedContractError("publication prior anchor disagrees with the exact prior pair")
    if receipt["receipt_id"] == prior_receipt["receipt_id"]:
        raise CandidateFeedContractError("unchanged sealed pair is an IO no-op, not a new transition")
    source_prior = feed["source_receipts"]["prior_feed"]
    if source_prior != {
        "feed_id": prior_feed["feed_id"],
        "schema": prior_feed["schema"],
        "feed_digest_sha256": _sha256(prior_payload),
        "policy_id": prior_feed["policy"]["policy_id"],
        "policy_digest_sha256": prior_feed["policy"]["policy_digest_sha256"],
        "composed_at": prior_feed["generated_at"],
        "first_observation_preserved": True,
        "candidate_identity_preserved": True,
    }:
        raise CandidateFeedContractError("feed continuation disagrees with the prior payload")
    if _utc(feed["generated_at"], "generated_at") < _utc(prior_feed["generated_at"], "prior.generated_at"):
        raise CandidateFeedContractError("feed continuation composition clock moved backwards")
    old_entries = prior_receipt["candidates"]
    if not set(old_entries).issubset(receipt["candidates"]):
        raise CandidateFeedContractError("publication continuation lost a formed candidate")
    for candidate_id, actual in receipt["candidates"].items():
        old = old_entries.get(candidate_id)
        if old is None:
            expected = {"first_receipt_id": receipt["receipt_id"], "first_consumer_published_at": None}
        elif old["first_receipt_id"] == prior_receipt["receipt_id"]:
            expected = {"first_receipt_id": old["first_receipt_id"], "first_consumer_published_at": prior_receipt_published_at}
        else:
            expected = old
        if actual != expected:
            raise CandidateFeedContractError("publication continuation rewrote first receipt identity or external publication clock")


__all__ = [
    "ACTIVATION_PRECONDITIONS",
    "CANDIDATE_FEED_SCHEMA",
    "CANDIDATE_FEED_ACTIVATION_RECEIPT_SCHEMA",
    "CandidateFeedContractError",
    "COMPOSER_ID",
    "FALSE_AUTHORITY",
    "MICROSTRUCTURE_SCHEMA",
    "POLICY_PATH",
    "POLICY_SCHEMA",
    "REASON_CODES",
    "SourceHealth",
    "canonical_bytes",
    "compose_candidate_feed",
    "validate_publication_receipt_binding",
    "validate_publication_receipt_transition",
    "summarise",
]
