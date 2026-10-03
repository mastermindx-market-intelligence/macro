"""Pure receipt-bound options-alpha research-candidate feed composer (inactive).

This module is the implementation carrier for the OA-1C research-candidate
composer. It is **inactive** until the four named activation preconditions are
cleared by the upstream owning program. It **DOES NOT** perform runtime
publication, durable writes, network I/O, clock inference. It must always be
called with caller-supplied receipts and explicit clocks.

The composer derives ``options.alpha_candidate_feed/v1`` from canonical
``options.signal_campaign/v2`` evidence and validated measured
``options.trade_nbbo_microstructure/v1`` receipts. It reuses the campaign
engine's ``LedgerSnapshot``/``load_ledger``/``canonical_bytes``/
``validate_campaign``/receipt machinery — never duplicating the prefix or
identity math.

Authority all authority remains ``False``. No scores, ranks, sizes, issues, trades,
training signals, neural-web feeds, calibration claims, P&L calculations,
tactical events, or directional probability claims are produced.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Sequence

from jsonschema import Draft202012Validator, FormatChecker

from engine.options_signal_campaign import (
    CAMPAIGN_SCHEMA,
    CampaignContractError,
    LedgerSnapshot,
    canonical_bytes as _campaign_canonical_bytes,
    validate_campaign,
)

CANDIDATE_FEED_SCHEMA = "options.alpha_candidate_feed/v1"
CANDIDATE_FEED_ACTIVATION_RECEIPT_SCHEMA = (
    "options.alpha_candidate_feed_activation_receipt/v1"
)
MICROSTRUCTURE_SCHEMA = "options.trade_nbbo_microstructure/v1"
POLICY_SCHEMA = "options.alpha_candidate_formation_policy/v1"
EVENT_STAGE_SCHEMA = "live_flow.event_stage/v1"

POLICY_PATH = "research/options_estate/options_alpha_candidate_formation_policy_v1.json"
ACTIVATION_RECEIPT_PATH = (
    "research/options_estate/options_alpha_candidate_feed_activation_receipt_v1.json"
)
ACTIVATION_RECEIPT_SCHEMA_FILENAME = (
    "options.alpha_candidate_feed_activation_receipt.v1.schema.json"
)
CANDIDATE_FEED_SCHEMA_FILENAME = "options.alpha_candidate_feed.v1.schema.json"
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
    + hashlib.sha256(b"oacf_composer|oa1c|inactive|v1").hexdigest()[:24]
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
    except Exception as exc:  # noqa: BLE001
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


@dataclass(frozen=True)
class CallerClocks:
    """Caller-supplied explicit clocks used by the composer.

    The composer MUST NOT infer any clock from ambient sources.
    """

    observation: str  # first_observed_at = decision_at
    available: str
    published: str


def _validate_caller_clocks(clocks: CallerClocks) -> tuple[datetime, datetime, datetime]:
    obs = _utc(clocks.observation, "caller.observation")
    av = _utc(clocks.available, "caller.available")
    pub = _utc(clocks.published, "caller.published")
    if not (obs <= av <= pub):
        raise CandidateFeedContractError(
            "caller clocks must satisfy observation <= available <= published"
        )
    return obs, av, pub


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
    _validate_schema(policy, "options.alpha_candidate_formation_policy.v1.schema.json")
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


def _validate_activation_receipt(
    receipt: dict[str, Any] | None,
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
        CANDIDATE_FEED_SCHEMA,
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
) -> dict[str, Any] | None:
    if prior is None:
        return None
    if not isinstance(prior, dict):
        raise CandidateFeedContractError("prior_feed must be a dict")
    _validate_schema(prior, CANDIDATE_FEED_SCHEMA_FILENAME)
    if prior["policy"]["policy_digest_sha256"] != policy_digest:
        raise CandidateFeedContractError(
            "prior_feed.policy.policy_digest_sha256 disagrees with current policy"
        )
    seen: set[str] = set()
    for candidate in prior.get("candidates", ()):
        if not isinstance(candidate, dict) or "candidate_id" not in candidate:
            raise CandidateFeedContractError("prior_feed.candidate missing candidate_id")
        cid = candidate["candidate_id"]
        if cid in seen:
            raise CandidateFeedContractError(
                "prior_feed.candidates must have unique candidate_ids"
            )
        seen.add(cid)
    if prior["policy"]["policy_id"] != "oa_member_persistent_measured_campaign/v1":
        raise CandidateFeedContractError("prior_feed.policy.policy_id is not accepted")
    if prior.get("publication_claim", {}).get("claim") != (
        "caller_supplied_synthetic_only_no_live_publication"
    ):
        raise CandidateFeedContractError(
            "prior_feed.publication_claim.claim must be synthetic-only"
        )
    return prior


def _prior_candidate_history(
    prior: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    if prior is None:
        return {}
    return {item["candidate_id"]: item for item in prior.get("candidates", ())}


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
        "source_schema": CAMPAIGN_SCHEMA,
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
    if activation_boundary is not None and formed_at < activation_boundary:
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


def _build_candidate_payload(
    *,
    campaign: dict[str, Any],
    micro: dict[str, Any],
    policy: dict[str, Any],
    policy_digest: str,
    policy_freeze_at: datetime,
    activation_boundary: datetime | None,
    observation: datetime,
    available: datetime,
    published: datetime,
    prior_candidate: dict[str, Any] | None,
    candidate_id: str,
    source_prefix_receipt: dict[str, Any],
    first_qualifying_revision_id: str,
    all_revisions: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    """Compose a single research_candidate record. ``prior_candidate`` (when
    provided by a validated prior feed) preserves the immutable
    first_observation/decision/available/published clocks for this identity
    and seeds the versioned_updates list. ``observation``/``available``/
    ``published`` here are the composer-call clocks, not backdated to the
    campaign formed_at. ``all_revisions`` is the chronologically-ordered
    tuple of revisions belonging to this campaign_id; every revision
    between ``first_qualifying_revision_id`` and the latest becomes an
    entry in ``versioned_updates`` so the identity is frozen but the
    revision history is fully traceable."""

    formed_at = _utc(campaign["formed_at"], "campaign.formed_at")
    campaign_revision_id = campaign["campaign_revision_id"]
    micro_digest = _sha256(_campaign_canonical_bytes(micro))
    campaign_digest = _sha256(_campaign_canonical_bytes(campaign))
    evidence_digest = _sha256(
        canonical_bytes(
            {
                "campaign": campaign_digest,
                "micro": micro_digest,
                "policy": policy_digest,
                "campaign_revision_id": campaign_revision_id,
                "first_qualifying_campaign_revision_id": (
                    first_qualifying_revision_id
                ),
                "campaign_id": campaign["campaign_id"],
            }
        )
    )

    if prior_candidate is not None:
        first_qualifying = prior_candidate["first_qualifying_campaign_revision_id"]
        first_observed_at = prior_candidate["first_observed_at"]
        decision_at = prior_candidate["decision_at"]
        candidate_available_at = prior_candidate["available_at"]
        candidate_published_at = prior_candidate["published_at"]
        versioned_updates = list(
            prior_candidate.get("versioned_updates", ())
        )
    else:
        first_qualifying = first_qualifying_revision_id
        first_observed_at = observation.strftime("%Y-%m-%dT%H:%M:%SZ")
        decision_at = first_observed_at
        candidate_available_at = available.strftime("%Y-%m-%dT%H:%M:%SZ")
        candidate_published_at = published.strftime("%Y-%m-%dT%H:%M:%SZ")
        versioned_updates = []

    # Append a versioned_update entry for every revision in the campaign
    # group, skipping ones already recorded in the prior feed. This way
    # the versioned_updates list always reflects the full chronological
    # progression of the campaign's revisions under this candidate identity,
    # and the latest (current) revision is the tail entry.
    seen_revision_ids = {
        entry["campaign_revision_id"] for entry in versioned_updates
    }
    for rev in all_revisions:
        if rev["campaign_revision_id"] in seen_revision_ids:
            continue
        rev_digest = _sha256(_campaign_canonical_bytes(rev))
        versioned_updates.append(
            {
                "campaign_revision_id": rev["campaign_revision_id"],
                "revision_number": int(rev["revision_number"]),
                "revision_digest_sha256": rev_digest,
                "formed_at": rev["formed_at"],
                "first_observed_at": first_observed_at,
                "available_at": candidate_available_at,
                "published_at": candidate_published_at,
                "candidate_identity_unchanged": True,
            }
        )
        seen_revision_ids.add(rev["campaign_revision_id"])

    measured = {
        "source_print_count": int(micro["source_print_count"]),
        "nbbo_valid_print_count": int(micro["nbbo_valid_print_count"]),
        "nbbo_premium_coverage": float(micro["nbbo_premium_coverage"]),
        "source_premium_usd": float(micro["source_premium_usd"]),
        "nbbo_covered_premium_usd": float(micro["nbbo_covered_premium_usd"]),
        "schema": MICROSTRUCTURE_SCHEMA,
        "schema_digest_sha256": micro_digest,
    }

    frozen = {
        "campaign_revision_id": campaign_revision_id,
        "formed_at": campaign["formed_at"],
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
        "campaign_member_count": int(campaign["descriptive"]["member_count"]),
        "final_member_event_id": campaign["members"][-1]["source_event_id"],
        "measured_source_print_count": measured["source_print_count"],
        "measured_nbbo_valid_print_count": measured["nbbo_valid_print_count"],
        "measured_nbbo_premium_coverage": measured["nbbo_premium_coverage"],
        "all_evidence_legs_within_decision_cutoff": True,
        "evidence_digest_sha256": evidence_digest,
        "source_prefix_receipt": source_prefix_receipt,
    }

    return {
        "candidate_id": candidate_id,
        "campaign_id": campaign["campaign_id"],
        "final_event_id": campaign["members"][-1]["source_event_id"],
        "first_qualifying_campaign_revision_id": first_qualifying,
        "current_campaign_revision_id": campaign_revision_id,
        "source_formed_at": campaign["formed_at"],
        "first_observed_at": first_observed_at,
        "decision_at": decision_at,
        "available_at": candidate_available_at,
        "published_at": candidate_published_at,
        "frozen_formation": frozen,
        "measured": measured,
        "evidence_digests": {
            "campaign_row_digest_sha256": campaign_digest,
            "microstructure_row_digest_sha256": micro_digest,
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
    available: datetime,
    published: datetime,
    reasons: list[str],
) -> dict[str, Any]:
    return {
        "campaign_id": campaign["campaign_id"],
        "campaign_revision_id": campaign["campaign_revision_id"],
        "formed_at": campaign["formed_at"],
        "reasons": sorted(set(reasons)),
        "state": "abstain",
        "first_observed_at": observation.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "available_at": available.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "published_at": published.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _build_degraded(
    campaign: dict[str, Any],
    *,
    observation: datetime,
    available: datetime,
    published: datetime,
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
        "available_at": available.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "published_at": published.strftime("%Y-%m-%dT%H:%M:%SZ"),
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
    available_clock: str,
    published_clock: str,
    prior_feed: dict[str, Any] | None = None,
    source_health: dict[str, Any] | None = None,
    implementation_carrier: str = IMPLEMENTATION_CARRIER_DEFAULT,
    deterministic_seed: str | None = None,
    feed_id: str | None = None,
    policy_freeze_at: str | None = None,
) -> dict[str, Any]:
    """Compose an options.alpha_candidate_feed/v1 artifact from caller-supplied
    inputs.

    The composer is **pure**: no network, no filesystem, no ambient clocks, no
    outcome ledger reads. All clocks and receipts must be passed in. The
    returned object validates against the frozen
    ``options.alpha_candidate_feed/v1`` schema with ``additionalProperties:
    false`` and finite JSON."""

    if not isinstance(campaigns, LedgerSnapshot):
        raise CandidateFeedContractError("campaigns must be a LedgerSnapshot")
    _validate_policy(policy)
    clocks = _validate_caller_clocks(
        CallerClocks(observation_clock, available_clock, published_clock)
    )
    health = SourceHealth.from_dict(source_health)
    micro_map = _validate_microstructure_map(microstructure_map)
    activation = _validate_activation_receipt(activation_receipt)

    if policy_freeze_at is None:
        raise CandidateFeedContractError(
            "policy_freeze_at must be supplied explicitly (no local NYSE inference)"
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
    if freeze_at > clocks[0]:
        fence_state = "pre_policy_freeze"
    elif activation_boundary is None or activation_boundary > clocks[0]:
        fence_state = "post_policy_freeze_pre_activation"
    else:
        fence_state = "post_activation"

    policy_digest = _sha256(canonical_bytes(policy))
    prior = _validate_prior_feed(prior_feed, policy_digest=policy_digest)
    prior_history = _prior_candidate_history(prior)

    campaign_views, poisoned_reasons = _validated_campaign_views(campaigns)
    source_prefix_receipt = _campaign_prefix_receipt(campaigns)
    micro_receipt = _microstructure_receipt(micro_map)

    candidates: list[dict[str, Any]] = []
    abstentions: list[dict[str, Any]] = []
    degraded: list[dict[str, Any]] = []

    # Surface poisoned campaigns as abstentions FIRST so they are visible
    # regardless of any grouping decisions.
    for poisoned in poisoned_reasons:
        abstentions.append(
            _build_abstention(
                poisoned["campaign"],
                observation=clocks[0],
                available=clocks[1],
                published=clocks[2],
                reasons=poisoned["reasons"],
            )
        )

    # Group revisions by campaign_id; ONE candidate per campaign, with the
    # latest revision as "current" and the earliest qualifying revision as
    # "first_qualifying" (frozen at formation).
    campaigns_by_id: dict[str, list[dict[str, Any]]] = {}
    for view in campaign_views:
        cid = view.row["campaign_id"]
        campaigns_by_id.setdefault(cid, []).append(view.row)
    for cid in campaigns_by_id:
        campaigns_by_id[cid].sort(key=lambda row: row["formed_at"])

    for cid, revisions in campaigns_by_id.items():
        current = revisions[-1]
        first_qualifying = revisions[0]
        first_qualifying_revision_id = first_qualifying["campaign_revision_id"]

        candidate_id = _candidate_identity(
            policy["policy_id"],
            cid,
            first_qualifying_revision_id,
        )
        prior_candidate = prior_history.get(candidate_id)
        if prior_candidate is not None:
            # First-qualifying MUST match the prior feed's first-qualifying.
            # A divergence means the consumer replayed under a new formation;
            # this is a tamper / contract break.
            prior_first = prior_candidate["first_qualifying_campaign_revision_id"]
            if prior_first != first_qualifying_revision_id:
                raise CandidateFeedContractError(
                    f"prior_feed first_qualifying_campaign_revision_id "
                    f"{prior_first!r} does not match current formation "
                    f"{first_qualifying_revision_id!r}"
                )

        reasons, micro, _ = _campaign_reasons(
            current,
            micro_map,
            policy_freeze_at=freeze_at,
            activation_boundary=activation_boundary,
            observation=clocks[0],
            source_health=health,
        )

        if not reasons:
            candidates.append(
                _build_candidate_payload(
                    campaign=current,
                    micro=micro,
                    policy=policy,
                    policy_digest=policy_digest,
                    policy_freeze_at=freeze_at,
                    activation_boundary=activation_boundary,
                    observation=clocks[0],
                    available=clocks[1],
                    published=clocks[2],
                    prior_candidate=prior_candidate,
                    candidate_id=candidate_id,
                    source_prefix_receipt=source_prefix_receipt,
                    first_qualifying_revision_id=first_qualifying_revision_id,
                    all_revisions=tuple(revisions),
                )
            )
            continue

        # Either degraded (source explicit stale/unavailable with prior
        # identity) or plain abstention.
        if "SOURCE_EXPLICITLY_STALE_OR_UNAVAILABLE" in reasons and prior_candidate is not None:
            degraded.append(
                _build_degraded(
                    current,
                    observation=clocks[0],
                    available=clocks[1],
                    published=clocks[2],
                    prior_candidate=prior_candidate,
                    reasons=reasons,
                )
            )
        else:
            abstentions.append(
                _build_abstention(
                    current,
                    observation=clocks[0],
                    available=clocks[1],
                    published=clocks[2],
                    reasons=reasons,
                )
            )

    seed = deterministic_seed or _sha256(
        canonical_bytes(
            {
                "policy_digest": policy_digest,
                "campaigns_prefix": source_prefix_receipt["prefix_sha256"],
                "micro_digest": micro_receipt["entries_digest_sha256"],
                "observation": observation_clock,
                "available": available_clock,
                "published": published_clock,
            }
        )
    )

    generated_at = published_clock
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
            "published_at": prior["header"]["header_digest_sha256"],
            "first_observation_preserved": all(
                isinstance(item, dict) for item in prior.get("candidates", ())
            ),
            "candidate_identity_preserved": all(
                item.get("candidate_id") == _candidate_identity(
                    policy["policy_id"],
                    item["campaign_id"],
                    item["first_qualifying_campaign_revision_id"],
                )
                for item in prior.get("candidates", ())
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
            "candidate_count": len(candidates),
            "abstention_count": len(abstentions),
            "degraded_count": len(degraded),
            "header_digest_sha256": "",  # filled below
        },
        "policy": policy_block,
        "activation": activation_block,
        "source_receipts": {
            "campaigns": source_prefix_receipt,
            "microstructure_map": micro_receipt,
            "prior_feed": prior_receipt,
        },
        "candidates": candidates,
        "abstentions": abstentions,
        "degraded": degraded,
        "publication_claim": {
            "claim": "caller_supplied_synthetic_only_no_live_publication",
            "claim_reason": (
                "inactive OA-1C implementation: caller-supplied synthetic receipts; "
                "no runtime publication, no durable write, no network I/O, no "
                "ambient clock; composer is inert until owning publisher supplies "
                "valid activation preconditions and a real activation receipt"
            ),
        },
        "authority": dict(FALSE_AUTHORITY),
    }

    # Header digest seals the entire feed bytes.
    feed_bytes = canonical_bytes(feed)
    feed["header"]["header_digest_sha256"] = _sha256(feed_bytes)

    _validate_schema(feed, CANDIDATE_FEED_SCHEMA_FILENAME)
    return feed


# ---------------------------------------------------------------------------
# Diagnostic helpers (no I/O).
# ---------------------------------------------------------------------------


def summarise(feed: dict[str, Any]) -> dict[str, Any]:
    """Return a small diagnostic summary of a composed feed. Pure, no I/O."""
    return {
        "feed_id": feed["feed_id"],
        "generated_at": feed["generated_at"],
        "candidate_count": feed["header"]["candidate_count"],
        "abstention_count": feed["header"]["abstention_count"],
        "degraded_count": feed["header"]["degraded_count"],
        "policy_id": feed["policy"]["policy_id"],
        "policy_digest_sha256": feed["policy"]["policy_digest_sha256"],
        "fence_state": feed["activation"]["fence_state"],
        "all_preconditions_cleared": feed["activation"][
            "all_preconditions_cleared"
        ],
        "publication_claim": feed["publication_claim"]["claim"],
        "header_digest_sha256": feed["header"]["header_digest_sha256"],
    }


__all__ = [
    "ACTIVATION_PRECONDITIONS",
    "CANDIDATE_FEED_SCHEMA",
    "CANDIDATE_FEED_ACTIVATION_RECEIPT_SCHEMA",
    "CandidateFeedContractError",
    "CallerClocks",
    "COMPOSER_ID",
    "FALSE_AUTHORITY",
    "MICROSTRUCTURE_SCHEMA",
    "POLICY_PATH",
    "POLICY_SCHEMA",
    "REASON_CODES",
    "SourceHealth",
    "canonical_bytes",
    "compose_candidate_feed",
    "summarise",
]