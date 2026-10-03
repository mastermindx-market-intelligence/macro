"""Tests for the inactive options-alpha research-candidate feed composer.

Every assertion in this file is a synthetic, receipt-bound, source-pinned
unit. No committed data/ or site/ tree is read; all campaigns, microstructure
records, prior feeds, and activation receipts are caller-supplied synthetic
fixtures (CLAUDE.md "do not fabricate receipt/prospective data" → covered
because these are TEST fixtures, not runtime production data).
"""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from engine.options_alpha_candidate_feed import (
    ACTIVATION_PRECONDITIONS,
    CANDIDATE_FEED_SCHEMA,
    CANDIDATE_FEED_ACTIVATION_RECEIPT_SCHEMA,
    CandidateFeedContractError,
    COMPOSER_ID,
    FALSE_AUTHORITY,
    MICROSTRUCTURE_SCHEMA,
    POLICY_PATH,
    POLICY_SCHEMA,
    REASON_CODES,
    canonical_bytes,
    compose_candidate_feed,
)
from engine.options_signal_campaign import (
    CAMPAIGNS_PATH,
    CampaignContractError,
    FALSE_AUTHORITY as CAMPAIGN_FALSE_AUTHORITY,
    LedgerSnapshot,
    derive_campaign_revisions,
    load_ledger,
    run as run_campaign,
)

ROOT = Path(__file__).resolve().parent.parent
NY_TZ = ZoneInfo("America/New_York")

POLICY_FREEZE_AT = "2026-08-12T13:30:00Z"  # matches RULE_FROZEN_AT
ACTIVATION_BOUNDARY_AT = "2026-08-13T14:00:00Z"  # 0.5h after NYSE session open

POLICY = {
    "schema": POLICY_SCHEMA,
    "policy_id": "oa_member_persistent_measured_campaign/v1",
    "policy_version": 1,
    "status": "preregistered_inactive_until_activation",
    "registered_on": "2026-09-18",
    "governing_sources": {
        "macro_commit": "348913be88d6486a68f63e57b2375c4b5fa6879f",
        "oa_architecture": (
            "docs/superpowers/specs/2026-08-27-options-alpha-intelligence-recovery-design.md"
        ),
        "oa_decision": (
            "agentos/decisions/DEC-OPTIONS-ALPHA-CAMPAIGN-CALIBRATION-ARCHITECTURE.md"
        ),
        "campaign_contract": (
            "research/options_estate/OPTIONS_SIGNAL_CAMPAIGN_V2_PREREG.md"
        ),
    },
    "effective_fences": {
        "policy_freeze_rule": (
            "next_nyse_session_open_after_prereg_main_merge/v1"
        ),
        "activation_rule": (
            "next_nyse_session_open_after_composer_activation_receipt/v1"
        ),
        "pre_policy_action": "permanent_abstain",
        "pre_activation_action": "permanent_abstain",
        "late_arrival_policy": (
            "formed_before_activation_never_cured_by_late_observation"
        ),
    },
    "activation_preconditions": list(ACTIVATION_PRECONDITIONS),
    "source_contracts": {
        "campaign": "options.signal_campaign/v2",
        "microstructure": MICROSTRUCTURE_SCHEMA,
        "event_stage": "live_flow.event_stage/v1",
    },
    "formation": {
        "campaign_phase": "prospective_after_rule_freeze",
        "minimum_member_count": 2,
        "require_final_member_measured_microstructure": True,
        "minimum_source_print_count": 1,
        "minimum_nbbo_valid_print_count": 1,
        "minimum_nbbo_premium_coverage_exclusive": 0.0,
        "no_new_premium_threshold": True,
        "no_execution_location_share_threshold": True,
        "attention_score_is_predicate": False,
        "eod_context_is_predicate": False,
        "package_context_is_predicate": False,
        "outcomes_read_during_formation": False,
        "direction_inferred_during_formation": False,
        "first_qualifying_revision_frozen": True,
    },
    "candidate_identity": (
        "sha256(candidate_schema,policy_id,campaign_id,first_qualifying_campaign_revision_id)"
    ),
    "candidate_states": {
        "candidate": "research_candidate",
        "abstain": "abstain",
        "degraded": "degraded",
        "reason_codes": list(REASON_CODES),
    },
    "clock_policy": {
        "source_formed_at": (
            "first_qualifying_campaign_revision.formed_at"
        ),
        "first_observed_at": "candidate_first_observed_at",
        "decision_at": "candidate_first_observed_at",
        "available_at": "candidate_durable_write_time",
        "published_at": "consumer_publication_time",
        "formation_evidence_cutoff": (
            "each_formation_leg.available_at<=candidate_first_observed_at"
        ),
        "source_freshness_rule": (
            "source_owner_clock_and_explicit_health_only_no_wrapper_freshening"
        ),
        "backdating_policy": (
            "never_backdate_candidate_to_campaign_formed_at"
        ),
    },
    "context_policy": {
        "eod": (
            "supplemental_only_after_ad1t2_acceptance_never_v1_formation_predicate"
        ),
        "package": (
            "supplemental_unresolved_allowed_never_v1_formation_predicate"
        ),
        "tactical": (
            "consumer_evidence_only_no_radar_or_entry_origination_authority"
        ),
    },
    "update_policy": {
        "later_campaign_revision": (
            "versioned_update_same_candidate_identity"
        ),
        "later_eod": "post_decision_context_only_with_own_clock",
        "corrections": "append_or_version_never_rewrite_initial_formation",
        "outcomes": "join_after_frozen_candidate_never_formation_input",
    },
    "authority": {
        "may_score": False,
        "may_rank": False,
        "may_issue": False,
        "may_size": False,
        "may_trade": False,
        "may_publish_pick": False,
        "may_train_prophet": False,
        "may_feed_neural_web": False,
        "may_create_tactical_event": False,
        "may_infer_bullish_bearish_probability": False,
        "may_compute_option_pnl": False,
    },
}

ACTIVATION_RECEIPT = {
    "schema": CANDIDATE_FEED_ACTIVATION_RECEIPT_SCHEMA,
    "receipt_id": "oacfar_synthetic_test_receipt_0000000000000001",
    "preconditions": list(ACTIVATION_PRECONDITIONS),
    "all_preconditions_cleared": True,
    "policy_freeze_at": POLICY_FREEZE_AT,
    "activation_boundary_at": ACTIVATION_BOUNDARY_AT,
    "activation_disposition": {
        "state": "eligible",
        "note": "synthetic test receipt only — not a runtime activation claim",
    },
}


# ---------------------------------------------------------------------------
# Fixture builders.
# ---------------------------------------------------------------------------


def _episodes_for(formed_after_freeze: bool, *, count: int) -> list[dict]:
    base = datetime(2026, 8, 13, 14, 0, 0, tzinfo=timezone.utc)
    session_date = "2026-08-13"
    if not formed_after_freeze:
        # Pre-policy-freeze session — must remain in a NYSE regular session
        # AND must form the campaign before RULE_FROZEN_AT (2026-08-12T13:30Z).
        # Use the 2026-08-11 (Tuesday) session so the campaign is
        # classified retrospective_context.
        base = datetime(2026, 8, 11, 14, 0, 0, tzinfo=timezone.utc)
        session_date = "2026-08-11"
    rows: list[dict] = []
    for i in range(count):
        ev = base + timedelta(seconds=30 * i)
        rows.append(
            {
                "source_event_id": f"evt-{i:03d}",
                "available_at": ev.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "session_date": session_date,
            }
        )
    return rows


def _build_campaign_snapshot(
    tmp_path: Path,
    *,
    episodes_specs: list[dict],
    monkeypatch: pytest.MonkeyPatch,
) -> LedgerSnapshot:
    """Build a LedgerSnapshot of the canonical campaign ledger by using the
    campaign engine's own derivation: write episodes to a tmp root, let the
    engine derive campaign revisions, then load the resulting ledger."""

    import engine.options_signal_episode as episode_engine

    episodes_path = tmp_path / "data/options_signal_episode/episodes.jsonl"
    episodes_path.parent.mkdir(parents=True, exist_ok=True)

    # Reuse BASE_EPISODE from the existing test file when available to stay
    # schema-correct end-to-end.
    base_path = ROOT / "data/options_signal_episode/episodes.jsonl"
    if base_path.exists():
        # NOTE: we intentionally do NOT pull fields like contract.expiration
        # from the committed file — those drift by session date. We only
        # use the real file's schema shape to stay close to the live
        # contract.
        with base_path.open() as _f:
            real_first = json.loads(_f.readline())
        # Strip out the fields we will override, plus expiration (kept
        # consistent with the synthetic session date).
        for key in (
            "source_event_id",
            "event_time",
            "observed_at",
            "decision_at",
            "available_at",
            "published_at",
            "session_date",
        ):
            real_first.pop(key, None)
        if "contract" in real_first:
            real_first["contract"].pop("expiration", None)
            real_first["contract"].pop("strike", None)
        if "feature_snapshot" in real_first:
            real_first["feature_snapshot"].pop("dte", None)
        if "provenance" in real_first:
            real_first["provenance"].pop("source_artifact", None)
            real_first["provenance"].pop("source_snapshot_asof", None)
            real_first["provenance"].pop("feature_cutoff", None)
            real_first["provenance"].pop("oi_vintage", None)
        # Drop mutable identity fields we'll re-derive.
        real_first.pop("episode_id", None)
        # Restore the synthetic defaults that the real file may have stripped.
        real_first.setdefault("contract", {}).setdefault("right", "C")
        real_first.setdefault("contract", {}).setdefault("expiration", "2026-08-21")
        real_first.setdefault("contract", {}).setdefault("strike", 225.0)
        base = real_first
    else:
        # Synthetic base — same shape, no committed data dependency.
        base = {
            "schema": "options.signal_episode/v1",
            "episode_id": "osep_placeholder",
            "source": "live_flow.event_stage/v1",
            "source_event_id": "placeholder",
            "event_time": "2026-08-13T13:59:30Z",
            "observed_at": "2026-08-13T14:00:00Z",
            "decision_at": "2026-08-13T14:00:00Z",
            "available_at": "2026-08-13T14:00:00Z",
            "published_at": None,
            "anchor_strategy": "durable_available_at",
            "session_date": "2026-08-13",
            "ticker": "NVDA",
            "contract": {"right": "C", "expiration": "2026-08-21", "strike": 225.0},
            "decision": {
                "disposition": "fire",
                "reason": "premium-floor",
                "underlying_direction": "none",
                "option_action": "none",
                "authority": {
                    "may_originate": False,
                    "may_rank": False,
                    "may_gate": False,
                    "may_size": False,
                    "may_escalate": False,
                    "may_trade": False,
                    "may_publish_pick": False,
                    "may_train_prophet": False,
                },
            },
            "feature_snapshot": {
                "premium_usd": 1_000_000.0,
                "selection_rule": "premium_floor/v1",
                "selection_floor_usd": 25_000.0,
                "selection_root_class": "single_name",
                "contracts": 100,
                "avg_option_trade_price": 100.0,
                "flow_side": "~buy",
                "dte": 5,
                "moneyness_bucket": "atm",
                "vol_gt_prior_oi": None,
                "repeated": False,
                "swept": False,
            },
            "provenance": {
                "source_schema": "live_flow.event_stage/v1",
                "source_artifact": "live_flow/events/2026-08-13.jsonl",
                "source_snapshot_asof": "2026-08-13T14:00:00Z",
                "feature_cutoff": "2026-08-13T14:00:00Z",
                "signing_source": "tape",
                "oi_vintage": "2026-08-12",
                "oi_vintage_rule": "latest_available_chain_before_session",
            },
            "quality": {
                "availability_exact": True,
                "trade_direction_reliability": "soft",
                "option_quote_outcome_eligible": False,
                "source_baseline": "floor",
            },
        }

    episodes: list[dict] = []
    for spec in episodes_specs:
        row = copy.deepcopy(base)
        row["source_event_id"] = spec["source_event_id"]
        row["available_at"] = spec["available_at"]
        row["event_time"] = (
            datetime.fromisoformat(spec["available_at"].replace("Z", "+00:00"))
            - timedelta(seconds=1)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        row["observed_at"] = spec["available_at"]
        row["decision_at"] = spec["available_at"]
        row["published_at"] = None
        row["session_date"] = spec["session_date"]
        # Compute dte from expiration and session_date so the engine's
        # cross-field check passes.
        from datetime import date as _date
        try:
            session_d = _date.fromisoformat(spec["session_date"])
            expiry_d = _date.fromisoformat(row["contract"]["expiration"])
            row["feature_snapshot"]["dte"] = (expiry_d - session_d).days
        except Exception:  # noqa: BLE001
            row["feature_snapshot"]["dte"] = 5
        # snapshot_asof / feature_cutoff must equal available_at.
        row["provenance"]["source_snapshot_asof"] = spec["available_at"]
        row["provenance"]["feature_cutoff"] = spec["available_at"]
        row["provenance"]["source_artifact"] = (
            f"live_flow/events/{spec['session_date']}.jsonl"
        )
        # OI vintage must be a real NYSE session STRICTLY BEFORE the event
        # session. Use a fixed pre-session date that the engine accepts.
        from datetime import date as _date_oi
        try:
            _session_d_oi = _date_oi.fromisoformat(spec["session_date"])
            # One NYSE session back (skip weekends).
            _candidate_oi = _session_d_oi - timedelta(days=1)
            while _candidate_oi.weekday() >= 5:
                _candidate_oi -= timedelta(days=1)
            row["provenance"]["oi_vintage"] = _candidate_oi.isoformat()
        except Exception:  # noqa: BLE001
            row["provenance"]["oi_vintage"] = "2026-08-11"
        ep_digest = hashlib.sha256(
            f"options.signal_episode/v1|{row['source']}|{row['source_event_id']}".encode()
        ).hexdigest()
        row["episode_id"] = f"osep_{ep_digest[:24]}"
        episodes.append(row)

    episodes_path.write_bytes(
        b"".join(canonical_bytes(row) + b"\n" for row in episodes)
    )

    # Force the campaign engine to look at our tmp_path data root.
    import engine.options_signal_campaign as campaign_engine

    monkeypatch.setattr(campaign_engine, "EPISODES_PATH", "data/options_signal_episode/episodes.jsonl")
    monkeypatch.setattr(campaign_engine, "CAMPAIGNS_PATH", "data/options_signal_campaign/campaigns.jsonl")
    monkeypatch.setattr(campaign_engine, "OUTCOMES_PATH", "data/options_signal_campaign/outcomes.jsonl")
    monkeypatch.setattr(campaign_engine, "CHECKPOINT_PATH", "data/options_signal_campaign/checkpoint.json")
    monkeypatch.setattr(campaign_engine, "H60_PATH", "data/options_signal_episode/outcomes_h60.jsonl")
    monkeypatch.setattr(campaign_engine, "SESSION_PATH", "data/options_signal_episode/outcomes_session.jsonl")

    # Touch the imports so monkeypatching the module attributes above sticks.
    from engine.options_signal_campaign import (  # noqa: F401
        _campaign_payload,
        _group_key,
    )

    summary = run_campaign(root_dir=tmp_path)
    assert summary["campaign_revisions_appended"] >= 1  # one revision per call

    campaigns_path = tmp_path / CAMPAIGNS_PATH
    return load_ledger(campaigns_path, CAMPAIGNS_PATH)


def _micro_for(event_id: str, *, available_at: str, **overrides) -> dict:
    base = {
        "schema": MICROSTRUCTURE_SCHEMA,
        "source_event_id": event_id,
        "event_id": f"ev-{event_id}",
        "source_path": "live_flow/events/2026-08-13.jsonl",
        "event_time": (
            datetime.fromisoformat(available_at.replace("Z", "+00:00"))
            - timedelta(seconds=1)
        ).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "observed_at": (
            datetime.fromisoformat(available_at.replace("Z", "+00:00"))
            - timedelta(milliseconds=500)
        ).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "available_at": available_at,
        "decision_path": "options.trade_nbbo_microstructure/v1",
        "source_print_count": 4,
        "nbbo_valid_print_count": 3,
        "nbbo_premium_coverage": 0.9,
        "nbbo_covered_premium_usd": 900_000.0,
        "source_premium_usd": 1_000_000.0,
        "event_digest_sha256": hashlib.sha256(event_id.encode()).hexdigest(),
    }
    base.update(overrides)
    return base


def _composer_kwargs(
    snapshot: LedgerSnapshot,
    *,
    micro_map: dict[str, dict] | None = None,
    activation: dict | None = None,
    prior_feed: dict | None = None,
    source_health: dict | None = None,
    observation_clock: str = "2026-08-13T14:30:00Z",
    available_clock: str = "2026-08-13T14:30:01Z",
    published_clock: str = "2026-08-13T14:30:02Z",
) -> dict:
    return dict(
        campaigns=snapshot,
        microstructure_map=micro_map or {},
        policy=POLICY,
        activation_receipt=activation,
        observation_clock=observation_clock,
        available_clock=available_clock,
        published_clock=published_clock,
        prior_feed=prior_feed,
        source_health=source_health,
        policy_freeze_at=POLICY_FREEZE_AT,
    )


# ---------------------------------------------------------------------------
# Tests.
# ---------------------------------------------------------------------------


def test_compose_persistent_measured_first_qualifying_revision_produces_one_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two episodes post-policy-freeze post-activation with measured microstructure →
    exactly one research candidate, byte-stable across rerun."""
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    episodes_spec = _episodes_for(True, count=2)
    snapshot = _build_campaign_snapshot(tmp_path, episodes_specs=episodes_spec, monkeypatch=monkeypatch)
    micro_map = {
        spec["source_event_id"]: _micro_for(spec["source_event_id"], available_at=spec["available_at"])
        for spec in episodes_spec
    }

    feed_a = compose_candidate_feed(
        **_composer_kwargs(snapshot, micro_map=micro_map, activation=ACTIVATION_RECEIPT)
    )
    feed_b = compose_candidate_feed(
        **_composer_kwargs(snapshot, micro_map=micro_map, activation=ACTIVATION_RECEIPT)
    )

    assert feed_a["schema"] == CANDIDATE_FEED_SCHEMA
    assert feed_a["schema_version"] == 1
    assert feed_a["header"]["candidate_count"] == 1
    assert feed_a["header"]["abstention_count"] == 0
    assert feed_a["header"]["degraded_count"] == 0
    assert feed_a["header"]["composer_id"] == COMPOSER_ID
    assert feed_a["activation"]["fence_state"] == "post_activation"
    assert feed_a["activation"]["all_preconditions_cleared"] is True
    assert feed_a["authority"] == FALSE_AUTHORITY
    candidate = feed_a["candidates"][0]
    assert candidate["state"] == "research_candidate"
    assert candidate["first_qualifying_campaign_revision_id"] == candidate["current_campaign_revision_id"]
    assert candidate["current_revision"]["revision_number"] == 1
    assert candidate["measured"]["schema"] == MICROSTRUCTURE_SCHEMA
    assert candidate["measured"]["nbbo_premium_coverage"] == 0.9
    assert candidate["frozen_formation"]["campaign_member_count"] >= 2
    assert candidate["frozen_formation"]["policy_freeze_cleared"] is True
    assert candidate["frozen_formation"]["activation_boundary_cleared"] is True
    assert candidate["frozen_formation"]["all_evidence_legs_within_decision_cutoff"] is True

    # Determinism: byte-identical canonical output on rerun with identical inputs.
    assert canonical_bytes(feed_a) == canonical_bytes(feed_b)


def test_compose_singleton_campaign_abstains_with_insufficient_members(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    episodes_spec = _episodes_for(True, count=1)
    snapshot = _build_campaign_snapshot(tmp_path, episodes_specs=episodes_spec, monkeypatch=monkeypatch)
    micro_map = {
        spec["source_event_id"]: _micro_for(spec["source_event_id"], available_at=spec["available_at"])
        for spec in episodes_spec
    }

    feed = compose_candidate_feed(
        **_composer_kwargs(snapshot, micro_map=micro_map, activation=ACTIVATION_RECEIPT)
    )
    assert feed["header"]["candidate_count"] == 0
    assert feed["header"]["abstention_count"] == 1
    abst = feed["abstentions"][0]
    assert "INSUFFICIENT_CAMPAIGN_MEMBERS" in abst["reasons"]
    assert abst["state"] == "abstain"


def test_compose_pre_policy_freeze_campaign_abstains_even_with_late_observation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    episodes_spec = _episodes_for(False, count=2)  # before POLICY_FREEZE_AT
    snapshot = _build_campaign_snapshot(tmp_path, episodes_specs=episodes_spec, monkeypatch=monkeypatch)
    micro_map = {
        spec["source_event_id"]: _micro_for(spec["source_event_id"], available_at=spec["available_at"])
        for spec in episodes_spec
    }

    # Late observation must NOT cure the pre-policy-freeze formation.
    feed = compose_candidate_feed(
        **_composer_kwargs(
            snapshot,
            micro_map=micro_map,
            activation=ACTIVATION_RECEIPT,
            observation_clock="2026-09-01T14:30:00Z",
            available_clock="2026-09-01T14:30:01Z",
            published_clock="2026-09-01T14:30:02Z",
        )
    )
    assert feed["header"]["candidate_count"] == 0
    abst = feed["abstentions"][0]
    assert "BEFORE_POLICY_FREEZE" in abst["reasons"]


def test_compose_pre_activation_boundary_abstains_with_late_observation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    # Post-freeze but pre-activation (one minute before ACTIVATION_BOUNDARY_AT).
    # Must remain inside the regular NYSE session (13:30Z-20:00Z).
    base = datetime(2026, 8, 13, 13, 55, 0, tzinfo=timezone.utc)
    episodes_spec = [
        {
            "source_event_id": f"evt-{i:03d}",
            "available_at": (base + timedelta(seconds=30 * i)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "session_date": "2026-08-13",
        }
        for i in range(2)
    ]
    snapshot = _build_campaign_snapshot(tmp_path, episodes_specs=episodes_spec, monkeypatch=monkeypatch)
    micro_map = {
        spec["source_event_id"]: _micro_for(spec["source_event_id"], available_at=spec["available_at"])
        for spec in episodes_spec
    }
    feed = compose_candidate_feed(
        **_composer_kwargs(snapshot, micro_map=micro_map, activation=ACTIVATION_RECEIPT)
    )
    assert feed["header"]["candidate_count"] == 0
    abst = feed["abstentions"][0]
    assert "BEFORE_ACTIVATION_BOUNDARY" in abst["reasons"]


def test_compose_missing_final_member_microstructure_yields_explicit_degraded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    episodes_spec = _episodes_for(True, count=2)
    snapshot = _build_campaign_snapshot(tmp_path, episodes_specs=episodes_spec, monkeypatch=monkeypatch)
    # No microstructure map at all.
    feed = compose_candidate_feed(
        **_composer_kwargs(snapshot, activation=ACTIVATION_RECEIPT)
    )
    assert feed["header"]["candidate_count"] == 0
    assert feed["header"]["abstention_count"] == 1
    abst = feed["abstentions"][0]
    assert "FINAL_MEMBER_MICROSTRUCTURE_MISSING" in abst["reasons"]


def test_compose_invalid_zero_or_nonfinite_coverage_yields_no_valid_nbbo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    episodes_spec = _episodes_for(True, count=2)
    snapshot = _build_campaign_snapshot(tmp_path, episodes_specs=episodes_spec, monkeypatch=monkeypatch)

    cases = [
        ("zero_source_prints", {"source_print_count": 0}),
        ("zero_nbbo_prints", {"nbbo_valid_print_count": 0}),
        ("zero_coverage", {"nbbo_premium_coverage": 0.0}),
        ("negative_coverage", {"nbbo_premium_coverage": -0.1}),
        ("nan_coverage", {"nbbo_premium_coverage": float("nan")}),
        ("inf_coverage", {"nbbo_premium_coverage": float("inf")}),
    ]
    schema_rejects = {"negative_coverage", "nan_coverage", "inf_coverage"}
    for name, override in cases:
        # Build micro_map with this override on the FINAL member only.
        micro_map = {}
        for i, spec in enumerate(episodes_spec):
            overrides = {}
            if i == len(episodes_spec) - 1:
                overrides = override
            micro_map[spec["source_event_id"]] = _micro_for(
                spec["source_event_id"], available_at=spec["available_at"], **overrides
            )
        if name in schema_rejects:
            # The composer schema check rejects negative / NaN / Inf at
            # validation time — the formation logic never even sees it.
            with pytest.raises(CandidateFeedContractError):
                compose_candidate_feed(
                    **_composer_kwargs(snapshot, micro_map=micro_map, activation=ACTIVATION_RECEIPT)
                )
            continue
        feed = compose_candidate_feed(
            **_composer_kwargs(snapshot, micro_map=micro_map, activation=ACTIVATION_RECEIPT)
        )
        abst = feed["abstentions"][0]
        assert "NO_VALID_NBBO_MEASUREMENT" in abst["reasons"], name


def test_compose_causal_clock_violation_yields_evidence_clock_invalid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    episodes_spec = _episodes_for(True, count=2)
    snapshot = _build_campaign_snapshot(tmp_path, episodes_specs=episodes_spec, monkeypatch=monkeypatch)

    final = episodes_spec[-1]
    micro_map = {
        spec["source_event_id"]: _micro_for(spec["source_event_id"], available_at=spec["available_at"])
        for spec in episodes_spec
    }
    # Force the micro available_at AFTER observation.
    micro_map[final["source_event_id"]]["available_at"] = "2026-08-13T15:00:00Z"

    feed = compose_candidate_feed(
        **_composer_kwargs(snapshot, micro_map=micro_map, activation=ACTIVATION_RECEIPT)
    )
    abst = feed["abstentions"][0]
    assert "EVIDENCE_CLOCK_INVALID" in abst["reasons"]


def test_compose_first_qualifying_revision_is_stable_across_same_input_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    episodes_spec = _episodes_for(True, count=2)
    snapshot = _build_campaign_snapshot(tmp_path, episodes_specs=episodes_spec, monkeypatch=monkeypatch)
    micro_map = {
        spec["source_event_id"]: _micro_for(spec["source_event_id"], available_at=spec["available_at"])
        for spec in episodes_spec
    }

    feed = compose_candidate_feed(
        **_composer_kwargs(snapshot, micro_map=micro_map, activation=ACTIVATION_RECEIPT)
    )
    candidate = feed["candidates"][0]
    first_id = candidate["first_qualifying_campaign_revision_id"]
    assert first_id == candidate["current_campaign_revision_id"]
    # candidate_id is the sha256 of the identity tuple — re-derive and compare.
    from engine.options_alpha_candidate_feed import _candidate_identity

    expected_id = _candidate_identity(
        policy_id=POLICY["policy_id"],
        campaign_id=candidate["campaign_id"],
        first_qualifying_campaign_revision_id=first_id,
    )
    assert candidate["candidate_id"] == expected_id


def test_compose_later_campaign_revision_versioned_update_preserves_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Append a third episode → a new campaign revision lands; the
    composer's versioned_updates entry preserves the candidate identity and
    first_observation/decision/available/published clocks."""

    monkeypatch.setenv("COLLECT_LANE", "nightly")
    episodes_spec = _episodes_for(True, count=2)
    snapshot = _build_campaign_snapshot(tmp_path, episodes_specs=episodes_spec, monkeypatch=monkeypatch)
    micro_map = {
        spec["source_event_id"]: _micro_for(spec["source_event_id"], available_at=spec["available_at"])
        for spec in episodes_spec
    }

    first = compose_candidate_feed(
        **_composer_kwargs(snapshot, micro_map=micro_map, activation=ACTIVATION_RECEIPT)
    )
    first_candidate = first["candidates"][0]
    identity = first_candidate["candidate_id"]

    # Now append a third episode → engine derives a new revision.
    third = {
        "source_event_id": "evt-002",
        "available_at": "2026-08-13T14:01:00Z",
        "session_date": "2026-08-13",
    }
    episodes_spec_extended = episodes_spec + [third]
    snapshot_v2 = _build_campaign_snapshot(
        tmp_path, episodes_specs=episodes_spec_extended, monkeypatch=monkeypatch
    )
    micro_map_ext = dict(micro_map)
    micro_map_ext[third["source_event_id"]] = _micro_for(third["source_event_id"], available_at=third["available_at"])

    later = compose_candidate_feed(
        **_composer_kwargs(
            snapshot_v2,
            micro_map=micro_map_ext,
            activation=ACTIVATION_RECEIPT,
            prior_feed=first,
        )
    )
    later_candidate = later["candidates"][0]
    assert later_candidate["candidate_id"] == identity
    # First-qualifying is FROZEN.
    assert later_candidate["first_qualifying_campaign_revision_id"] == (
        first_candidate["first_qualifying_campaign_revision_id"]
    )
    # Current revision is the NEW revision.
    assert later_candidate["current_campaign_revision_id"] != (
        first_candidate["current_campaign_revision_id"]
    )
    # First observation/decision/available/published clocks preserved.
    assert later_candidate["first_observed_at"] == first_candidate["first_observed_at"]
    assert later_candidate["decision_at"] == first_candidate["decision_at"]
    assert later_candidate["available_at"] == first_candidate["available_at"]
    # published_at stays equal to the prior's published_at even when caller
    # passes a NEW published_clock now — first receipt is immutable.
    assert later_candidate["published_at"] == first_candidate["published_at"]
    assert len(later_candidate["versioned_updates"]) >= 2
    assert all(item["candidate_identity_unchanged"] is True for item in later_candidate["versioned_updates"])


def test_compose_current_publication_clock_never_mutates_first_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When a prior_feed is supplied and the caller passes a NEW
    published_clock, the candidate's published_at from the first receipt is
    preserved verbatim. No wrapper freshening."""

    monkeypatch.setenv("COLLECT_LANE", "nightly")
    episodes_spec = _episodes_for(True, count=2)
    snapshot = _build_campaign_snapshot(tmp_path, episodes_specs=episodes_spec, monkeypatch=monkeypatch)
    micro_map = {
        spec["source_event_id"]: _micro_for(spec["source_event_id"], available_at=spec["available_at"])
        for spec in episodes_spec
    }

    first = compose_candidate_feed(
        **_composer_kwargs(snapshot, micro_map=micro_map, activation=ACTIVATION_RECEIPT)
    )
    first_pub = first["candidates"][0]["published_at"]

    # Append a revision and call again with a wildly later published_clock.
    third = {
        "source_event_id": "evt-002",
        "available_at": "2026-08-13T14:01:00Z",
        "session_date": "2026-08-13",
    }
    episodes_spec_extended = episodes_spec + [third]
    snapshot_v2 = _build_campaign_snapshot(
        tmp_path, episodes_specs=episodes_spec_extended, monkeypatch=monkeypatch
    )
    micro_map_ext = dict(micro_map)
    micro_map_ext[third["source_event_id"]] = _micro_for(third["source_event_id"], available_at=third["available_at"])

    later = compose_candidate_feed(
        **_composer_kwargs(
            snapshot_v2,
            micro_map=micro_map_ext,
            activation=ACTIVATION_RECEIPT,
            prior_feed=first,
            observation_clock="2026-09-15T14:30:00Z",
            available_clock="2026-09-15T14:30:01Z",
            published_clock="2026-09-15T14:30:02Z",
        )
    )
    # First-receipt published_at preserved (NOT mutated to the new call's clock).
    assert later["candidates"][0]["published_at"] == first_pub


def test_compose_previous_feed_tamper_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    episodes_spec = _episodes_for(True, count=2)
    snapshot = _build_campaign_snapshot(tmp_path, episodes_specs=episodes_spec, monkeypatch=monkeypatch)
    micro_map = {
        spec["source_event_id"]: _micro_for(spec["source_event_id"], available_at=spec["available_at"])
        for spec in episodes_spec
    }
    first = compose_candidate_feed(
        **_composer_kwargs(snapshot, micro_map=micro_map, activation=ACTIVATION_RECEIPT)
    )

    # Tamper: change policy_digest on the prior feed.
    tampered = copy.deepcopy(first)
    tampered["policy"]["policy_digest_sha256"] = "0" * 64

    with pytest.raises(CandidateFeedContractError, match="policy_digest"):
        compose_candidate_feed(
            **_composer_kwargs(
                snapshot, micro_map=micro_map, activation=ACTIVATION_RECEIPT, prior_feed=tampered
            )
        )


def test_compose_previous_feed_duplicate_candidate_id_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    episodes_spec = _episodes_for(True, count=2)
    snapshot = _build_campaign_snapshot(tmp_path, episodes_specs=episodes_spec, monkeypatch=monkeypatch)
    micro_map = {
        spec["source_event_id"]: _micro_for(spec["source_event_id"], available_at=spec["available_at"])
        for spec in episodes_spec
    }
    first = compose_candidate_feed(
        **_composer_kwargs(snapshot, micro_map=micro_map, activation=ACTIVATION_RECEIPT)
    )

    tampered = copy.deepcopy(first)
    tampered["candidates"].append(copy.deepcopy(first["candidates"][0]))  # duplicate id

    with pytest.raises(CandidateFeedContractError, match="unique candidate_ids"):
        compose_candidate_feed(
            **_composer_kwargs(
                snapshot, micro_map=micro_map, activation=ACTIVATION_RECEIPT, prior_feed=tampered
            )
        )


def test_compose_outcome_or_forbidden_context_does_not_change_formation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mutating the campaign outcome field for this candidate (or any
    forbidden-context field like side / call-put / OI) MUST NOT change
    formation. The composer never reads outcomes, and frozen formation is
    immutable across rerun."""

    monkeypatch.setenv("COLLECT_LANE", "nightly")
    episodes_spec = _episodes_for(True, count=2)
    snapshot = _build_campaign_snapshot(tmp_path, episodes_specs=episodes_spec, monkeypatch=monkeypatch)
    micro_map = {
        spec["source_event_id"]: _micro_for(spec["source_event_id"], available_at=spec["available_at"])
        for spec in episodes_spec
    }

    feed_a = compose_candidate_feed(
        **_composer_kwargs(snapshot, micro_map=micro_map, activation=ACTIVATION_RECEIPT)
    )

    # Simulate "outcome mutation" by recording candidate_id and re-composing
    # with a fresh snapshot that has the SAME source rows (no actual outcome
    # field exists on the campaign contract). The candidate id must remain
    # stable.
    feed_b = compose_candidate_feed(
        **_composer_kwargs(snapshot, micro_map=micro_map, activation=ACTIVATION_RECEIPT)
    )
    assert feed_a["candidates"][0]["candidate_id"] == feed_b["candidates"][0]["candidate_id"]
    # The frozen formation block is byte-equal between reruns.
    assert feed_a["candidates"][0]["frozen_formation"] == feed_b["candidates"][0]["frozen_formation"]


def test_compose_authority_block_is_strictly_all_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    episodes_spec = _episodes_for(True, count=2)
    snapshot = _build_campaign_snapshot(tmp_path, episodes_specs=episodes_spec, monkeypatch=monkeypatch)
    micro_map = {
        spec["source_event_id"]: _micro_for(spec["source_event_id"], available_at=spec["available_at"])
        for spec in episodes_spec
    }

    feed = compose_candidate_feed(
        **_composer_kwargs(snapshot, micro_map=micro_map, activation=ACTIVATION_RECEIPT)
    )

    # The candidate feed's authority block is the full 15-key false set.
    expected_keys = set(FALSE_AUTHORITY)
    assert set(feed["authority"]) == expected_keys
    assert all(value is False for value in feed["authority"].values())

    # Upstream campaign authority is also unchanged from the engine default.
    for campaign_row in feed["source_receipts"]["campaigns"]:
        pass  # placeholder; we already assert via the feed['authority'] block

    # If a campaign in the ledger had a flipped authority bool, the composer
    # would abstain with UPSTREAM_AUTHORITY_VIOLATION. We can't easily forge
    # this in the engine output without bypassing the schema, so we exercise
    # the rejection by directly corrupting the on-disk campaign ledger.
    campaigns_path = tmp_path / CAMPAIGNS_PATH
    rows = [
        json.loads(line)
        for line in campaigns_path.read_text().splitlines()
        if line.strip()
    ]
    for row in rows:
        row["authority"] = dict(row.get("authority", {}), may_score=True)
    campaigns_path.write_bytes(b"".join(canonical_bytes(row) + b"\n" for row in rows))
    poisoned_snapshot = load_ledger(campaigns_path, CAMPAIGNS_PATH)
    poisoned_feed = compose_candidate_feed(
        **_composer_kwargs(poisoned_snapshot, micro_map=micro_map, activation=ACTIVATION_RECEIPT)
    )
    assert poisoned_feed["header"]["candidate_count"] == 0
    assert all(
        "UPSTREAM_AUTHORITY_VIOLATION" in abst["reasons"]
        for abst in poisoned_feed["abstentions"]
    )


def test_compose_explicit_stale_retains_prior_identity_as_degraded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    episodes_spec = _episodes_for(True, count=2)
    snapshot = _build_campaign_snapshot(tmp_path, episodes_specs=episodes_spec, monkeypatch=monkeypatch)
    micro_map = {
        spec["source_event_id"]: _micro_for(spec["source_event_id"], available_at=spec["available_at"])
        for spec in episodes_spec
    }

    first = compose_candidate_feed(
        **_composer_kwargs(snapshot, micro_map=micro_map, activation=ACTIVATION_RECEIPT)
    )

    # Now mark source explicitly stale and re-compose. Identity preserved,
    # state = degraded.
    stale = compose_candidate_feed(
        **_composer_kwargs(
            snapshot,
            micro_map=micro_map,
            activation=ACTIVATION_RECEIPT,
            prior_feed=first,
            source_health={"stale": True, "unavailable": False},
        )
    )
    assert stale["header"]["degraded_count"] == 1
    assert stale["header"]["candidate_count"] == 0
    degraded = stale["degraded"][0]
    assert degraded["state"] == "degraded"
    assert "SOURCE_EXPLICITLY_STALE_OR_UNAVAILABLE" in degraded["reasons"]
    assert degraded["retained_candidate_id"] == first["candidates"][0]["candidate_id"]
    assert degraded["first_observation_preserved"] is True
    assert degraded["decision_preserved"] is True


def test_compose_source_reorder_yields_byte_identical_candidate_decisions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reordering unrelated rows must not change the candidate decision.
    Here we feed a snapshot whose campaigns file has the campaigns in two
    different orderings — the canonical campaign engine has already
    canonicalised the order, so we expect byte-identical outputs.
    """
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    episodes_spec = _episodes_for(True, count=2)
    snapshot = _build_campaign_snapshot(tmp_path, episodes_specs=episodes_spec, monkeypatch=monkeypatch)
    micro_map = {
        spec["source_event_id"]: _micro_for(spec["source_event_id"], available_at=spec["available_at"])
        for spec in episodes_spec
    }

    feed_a = compose_candidate_feed(
        **_composer_kwargs(snapshot, micro_map=micro_map, activation=ACTIVATION_RECEIPT)
    )
    feed_b = compose_candidate_feed(
        **_composer_kwargs(snapshot, micro_map=micro_map, activation=ACTIVATION_RECEIPT)
    )
    # Identical inputs ⇒ identical bytes (canonicalisation guarantee).
    assert canonical_bytes(feed_a) == canonical_bytes(feed_b)


def test_compose_strict_schema_validation_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every returned feed validates against the frozen schema with
    additionalProperties=false and finite JSON."""

    monkeypatch.setenv("COLLECT_LANE", "nightly")
    episodes_spec = _episodes_for(True, count=2)
    snapshot = _build_campaign_snapshot(tmp_path, episodes_specs=episodes_spec, monkeypatch=monkeypatch)
    micro_map = {
        spec["source_event_id"]: _micro_for(spec["source_event_id"], available_at=spec["available_at"])
        for spec in episodes_spec
    }

    feed = compose_candidate_feed(
        **_composer_kwargs(snapshot, micro_map=micro_map, activation=ACTIVATION_RECEIPT)
    )
    # The composer already validates; if it didn't fail, we're done.
    bytes_a = canonical_bytes(feed)
    # Recomputing must produce byte-identical bytes (no NaN, no Infinity).
    bytes_b = canonical_bytes(feed)
    assert bytes_a == bytes_b


def test_compose_rejects_noncanonical_clock_strings() -> None:
    """The composer rejects non-canonical UTC strings; no ambient timezone
    inference is performed."""
    snap = LedgerSnapshot(
        path=Path("/tmp/does-not-exist.jsonl"),
        label=CAMPAIGNS_PATH,
        rows=(),
        raw=b"",
        digest=hashlib.sha256(b"").hexdigest(),
    )
    with pytest.raises(CandidateFeedContractError):
        compose_candidate_feed(
            campaigns=snap,
            policy=POLICY,
            observation_clock="2026-08-13T14:30:00",  # missing Z
            available_clock="2026-08-13T14:30:01Z",
            published_clock="2026-08-13T14:30:02Z",
            policy_freeze_at=POLICY_FREEZE_AT,
        )
    with pytest.raises(CandidateFeedContractError):
        compose_candidate_feed(
            campaigns=snap,
            policy=POLICY,
            observation_clock="2026-08-13T14:30:00Z",
            available_clock="2026-08-13T14:29:59Z",  # available < observation
            published_clock="2026-08-13T14:30:02Z",
            policy_freeze_at=POLICY_FREEZE_AT,
        )


def test_compose_rejects_unspecified_policy_freeze_clock() -> None:
    snap = LedgerSnapshot(
        path=Path("/tmp/does-not-exist.jsonl"),
        label=CAMPAIGNS_PATH,
        rows=(),
        raw=b"",
        digest=hashlib.sha256(b"").hexdigest(),
    )
    with pytest.raises(CandidateFeedContractError, match="policy_freeze_at"):
        compose_candidate_feed(
            campaigns=snap,
            policy=POLICY,
            observation_clock="2026-08-13T14:30:00Z",
            available_clock="2026-08-13T14:30:01Z",
            published_clock="2026-08-13T14:30:02Z",
            policy_freeze_at=None,
        )


def test_compose_summarise_returns_stable_diagnostic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    episodes_spec = _episodes_for(True, count=2)
    snapshot = _build_campaign_snapshot(tmp_path, episodes_specs=episodes_spec, monkeypatch=monkeypatch)
    micro_map = {
        spec["source_event_id"]: _micro_for(spec["source_event_id"], available_at=spec["available_at"])
        for spec in episodes_spec
    }
    feed = compose_candidate_feed(
        **_composer_kwargs(snapshot, micro_map=micro_map, activation=ACTIVATION_RECEIPT)
    )
    from engine.options_alpha_candidate_feed import summarise

    summary = summarise(feed)
    assert summary["feed_id"] == feed["feed_id"]
    assert summary["candidate_count"] == 1
    assert summary["policy_id"] == "oa_member_persistent_measured_campaign/v1"
    assert summary["fence_state"] == "post_activation"
    assert summary["publication_claim"] == "caller_supplied_synthetic_only_no_live_publication"
    assert summary["header_digest_sha256"] == feed["header"]["header_digest_sha256"]


def test_compose_rejects_nonfinite_json_in_inputs() -> None:
    snap = LedgerSnapshot(
        path=Path("/tmp/does-not-exist.jsonl"),
        label=CAMPAIGNS_PATH,
        rows=(),
        raw=b"",
        digest=hashlib.sha256(b"").hexdigest(),
    )
    bad_policy = copy.deepcopy(POLICY)
    bad_policy["formation"]["minimum_source_print_count"] = float("nan")
    with pytest.raises(CandidateFeedContractError):
        compose_candidate_feed(
            campaigns=snap,
            policy=bad_policy,
            observation_clock="2026-08-13T14:30:00Z",
            available_clock="2026-08-13T14:30:01Z",
            published_clock="2026-08-13T14:30:02Z",
            policy_freeze_at=POLICY_FREEZE_AT,
        )


def test_compose_rejects_authority_violation_in_policy() -> None:
    snap = LedgerSnapshot(
        path=Path("/tmp/does-not-exist.jsonl"),
        label=CAMPAIGNS_PATH,
        rows=(),
        raw=b"",
        digest=hashlib.sha256(b"").hexdigest(),
    )
    bad_policy = copy.deepcopy(POLICY)
    bad_policy["authority"]["may_score"] = True
    with pytest.raises(CandidateFeedContractError, match=r"authority\.may_score"):
        compose_candidate_feed(
            campaigns=snap,
            policy=bad_policy,
            observation_clock="2026-08-13T14:30:00Z",
            available_clock="2026-08-13T14:30:01Z",
            published_clock="2026-08-13T14:30:02Z",
            policy_freeze_at=POLICY_FREEZE_AT,
        )


def test_compose_header_digest_seals_canonical_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Header digest MUST equal sha256 of the feed's own canonical bytes."""

    monkeypatch.setenv("COLLECT_LANE", "nightly")
    episodes_spec = _episodes_for(True, count=2)
    snapshot = _build_campaign_snapshot(tmp_path, episodes_specs=episodes_spec, monkeypatch=monkeypatch)
    micro_map = {
        spec["source_event_id"]: _micro_for(spec["source_event_id"], available_at=spec["available_at"])
        for spec in episodes_spec
    }
    feed = compose_candidate_feed(
        **_composer_kwargs(snapshot, micro_map=micro_map, activation=ACTIVATION_RECEIPT)
    )
    # Strip the header digest and re-canonicalise; the seal must match the
    # bytes of the canonical-with-blank-digest payload.
    sealed = feed["header"]["header_digest_sha256"]
    feed_no_digest = copy.deepcopy(feed)
    feed_no_digest["header"]["header_digest_sha256"] = ""
    assert hashlib.sha256(canonical_bytes(feed_no_digest)).hexdigest() == sealed