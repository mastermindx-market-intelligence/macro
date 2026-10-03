"""Pure post-formation underlying-outcome enrichment for candidate feeds.

This module is deliberately downstream of formation.  It neither reads an
outcome ledger while forming candidates nor creates a ledger, candidate
identity, option return, publisher, or control plane.
"""

from __future__ import annotations

import copy
from typing import Any

from engine import options_alpha_candidate_feed as candidate_feed
from engine import options_signal_campaign as campaign_engine
from engine.options_signal_campaign import EffectiveOutcomeView

HORIZONS = ("h60", "eod", "1d", "3d", "5d", "10d")
POST_FORMATION_KEY = "post_formation_outcomes"
CAMPAIGN_CONTEXT_KEY = "campaign_context"


class CandidateOutcomeEnrichmentError(ValueError):
    pass


def _outcome_payload(row: Any) -> dict[str, Any]:
    value = row.value
    status = value["status"]
    if status == "complete" and value["underlying"]["status"] == "complete":
        state = "available"
    elif status == "incomplete":
        # Campaign outcomes are append-only completed or *terminal*
        # incomplete source observations.  They are not an outstanding job.
        state = "unavailable"
    else:
        state = "unavailable"
    return {
        "state": state,
        "campaign_outcome_id": value["campaign_outcome_id"],
        "campaign_revision_id": value["campaign_revision_id"],
        "horizon": value["horizon"],
        "source_physical_ordinal": row.ordinal,
        "source_physical_row_sha256": row.sha256,
        "status": status,
        "reason": value["reason"],
        "campaign_available_at": value["campaign_available_at"],
        "computed_at": value["computed_at"],
        "target_time": value["target_time"],
        "matured_at": value["matured_at"],
        "underlying": copy.deepcopy(value["underlying"]),
        "source_outcome": copy.deepcopy(value["source_outcome"]),
        "source_outcome_prefix": copy.deepcopy(value["source_outcome_prefix"]),
    }


def _campaign_context(candidate: dict[str, Any], row: Any) -> dict[str, Any]:
    """Copy only descriptive contract facts from the frozen campaign revision."""
    revision_id = candidate["first_qualifying_campaign_revision_id"]
    if candidate["frozen_formation"]["campaign_revision_id"] != revision_id:
        raise CandidateOutcomeEnrichmentError(
            "campaign context frozen revision mismatch"
        )
    if row.value["campaign_revision_id"] != revision_id:
        raise CandidateOutcomeEnrichmentError("campaign context revision mismatch")
    updates = [
        update
        for update in candidate["versioned_updates"]
        if update["campaign_revision_id"] == revision_id
    ]
    if len(updates) != 1 or updates[0].get("revision_digest_sha256") != row.sha256:
        raise CandidateOutcomeEnrichmentError("campaign context source hash mismatch")
    return {
        "schema": "options.alpha_candidate_campaign_context/v1",
        "campaign_revision_id": revision_id,
        "group": copy.deepcopy(row.value["group"]),
        "flow_side_counts": copy.deepcopy(row.value["descriptive"]["flow_side_counts"]),
        "intent": copy.deepcopy(row.value["intent"]),
    }


def _absent(horizon: str, *, quarantined: bool) -> dict[str, Any]:
    return {
        "state": "unavailable" if quarantined else "pending",
        "campaign_outcome_id": None,
        "campaign_revision_id": None,
        "horizon": horizon,
        "source_physical_ordinal": None,
        "source_physical_row_sha256": None,
        "status": None,
        "reason": (
            "quarantined_campaign_outcome"
            if quarantined
            else "admitted_campaign_outcome_not_yet_present"
        ),
        "campaign_available_at": None,
        "computed_at": None,
        "target_time": None,
        "matured_at": None,
        "underlying": None,
        "source_outcome": None,
        "source_outcome_prefix": None,
    }


def enrich_candidate_outcomes(
    feed: dict[str, Any],
    *,
    effective_outcomes: EffectiveOutcomeView,
    correction_activation_receipt: dict[str, Any],
) -> dict[str, Any]:
    """Return a resealed v2 feed with mutable post-formation outcome evidence.

    Only ``EffectiveOutcomeView.admitted_rows`` are joined.  The frozen first
    qualifying revision, rather than the current revision, is the join key.
    """
    if not isinstance(effective_outcomes, EffectiveOutcomeView):
        raise CandidateOutcomeEnrichmentError(
            "effective_outcomes must be an EffectiveOutcomeView"
        )
    # A public dataclass constructor is not an authority boundary. Rebuild the
    # view through the campaign validator with the exact activation receipt.
    verified_view = campaign_engine.build_effective_outcome_view(
        effective_outcomes.campaigns,
        effective_outcomes.outcomes,
        effective_outcomes.policy,
        activation_receipt=correction_activation_receipt,
    )
    candidate_feed._validate_schema(
        feed, candidate_feed.CANDIDATE_FEED_V2_SCHEMA_FILENAME
    )
    for snapshot in (verified_view.campaigns, verified_view.outcomes):
        raw = b"".join(item.raw + b"\n" for item in snapshot.rows)
        if raw != snapshot.raw or candidate_feed._sha256(raw) != snapshot.digest:
            raise CandidateOutcomeEnrichmentError(
                "effective-view snapshot bytes are inconsistent"
            )
        for ordinal, item in enumerate(snapshot.rows, 1):
            if item.ordinal != ordinal or item.raw != candidate_feed.canonical_bytes(
                item.value
            ):
                raise CandidateOutcomeEnrichmentError(
                    "effective-view ledger row is inconsistent"
                )
            if item.sha256 != candidate_feed._sha256(item.raw):
                raise CandidateOutcomeEnrichmentError(
                    "effective-view ledger row hash is inconsistent"
                )
    campaign_rows = {
        item.value["campaign_revision_id"]: item
        for item in verified_view.campaigns.rows
    }
    by_key: dict[tuple[str, str], Any] = {}
    for item in verified_view.admitted_rows:
        # The effective-view construction checks correction receipt and prefix
        # identity.  Validate the admitted row itself before exposing any of
        # its fields in this downstream, source-only view.
        campaign_engine._validate_schema(
            item.value, "options.signal_campaign_outcome.v1.schema.json"
        )
        key = (item.value["campaign_revision_id"], item.value["horizon"])
        if key in by_key:
            raise CandidateOutcomeEnrichmentError("duplicate admitted outcome key")
        by_key[key] = item
    enriched = copy.deepcopy(feed)
    for candidate in enriched["formed_candidates"]:
        revision_id = candidate["first_qualifying_campaign_revision_id"]
        row = campaign_rows.get(revision_id)
        if row is None:
            raise CandidateOutcomeEnrichmentError(
                "frozen candidate revision is absent from campaign snapshot"
            )
        candidate[CAMPAIGN_CONTEXT_KEY] = _campaign_context(candidate, row)
        candidate[POST_FORMATION_KEY] = {
            "schema": "options.alpha_candidate_post_formation_outcomes/v1",
            "join_revision_id": revision_id,
            "horizons": {
                horizon: (
                    _outcome_payload(by_key[(revision_id, horizon)])
                    if (revision_id, horizon) in by_key
                    else _absent(
                        horizon,
                        quarantined=(revision_id, horizon)
                        in verified_view.quarantined_keys,
                    )
                )
                for horizon in HORIZONS
            },
        }
        if candidate["first_qualifying_campaign_revision_id"] != revision_id:
            raise CandidateOutcomeEnrichmentError("enrichment rewrote frozen revision")
    # A feed identity is a publisher-facing payload identity.  Derive it from
    # immutable feed material plus this mutable outcome block, so a changed
    # outcome view cannot reuse a prior published feed_id.
    identity_base = copy.deepcopy(enriched)
    identity_base["feed_id"] = ""
    identity_base["header"]["header_digest_sha256"] = ""
    for candidate in identity_base["formed_candidates"]:
        candidate.pop(POST_FORMATION_KEY, None)
    outcome_block = [item[POST_FORMATION_KEY] for item in enriched["formed_candidates"]]
    enriched["feed_id"] = candidate_feed._feed_id(
        (
            candidate_feed.CANDIDATE_FEED_SCHEMA,
            candidate_feed._sha256(candidate_feed.canonical_bytes(identity_base)),
            candidate_feed._sha256(candidate_feed.canonical_bytes(outcome_block)),
        )
    )
    # Preserve candidate/source history and reseal the new payload.
    unsealed = copy.deepcopy(enriched)
    unsealed["header"]["header_digest_sha256"] = ""
    enriched["header"]["header_digest_sha256"] = candidate_feed._sha256(
        candidate_feed.canonical_bytes(unsealed)
    )
    candidate_feed._validate_schema(
        enriched, candidate_feed.CANDIDATE_FEED_V2_SCHEMA_FILENAME
    )
    return enriched
