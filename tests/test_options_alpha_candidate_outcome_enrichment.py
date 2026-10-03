"""Integration proof: real composer, view rebuild, validators, and receipt."""

from __future__ import annotations
import copy
import hashlib
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent))
import engine.options_signal_campaign as campaign_engine
import test_options_alpha_candidate_feed as candidate_fixture
import test_options_signal_campaign_effective_view as correction_fixture
from engine import options_alpha_candidate_outcome_enrichment as enrichment
from engine.options_alpha_candidate_feed import canonical_bytes, compose_candidate_feed
from engine.options_signal_campaign import (
    CampaignContractError,
    LedgerRow,
    LedgerSnapshot,
    _prefix_sha256,
    build_effective_outcome_view,
)


def _row(
    campaign, horizon, ordinal, *, complete=True, unavailable=False, quarantined=False
):
    revision = campaign["campaign_revision_id"]
    digest = hashlib.sha256(f"{revision}|{horizon}|{ordinal}".encode()).hexdigest()
    path = (
        "data/options_signal_episode/outcomes_h60.jsonl"
        if horizon == "h60"
        else "data/options_signal_episode/outcomes_session.jsonl"
    )
    source_schema = (
        "options.signal_episode_outcome/v1"
        if horizon == "h60"
        else "options.signal_episode_session_outcome/v1"
    )
    value = {
        "schema": "options.signal_campaign_outcome/v1",
        "campaign_outcome_id": "ocout_" + digest[:24],
        "campaign_id": campaign["campaign_id"],
        "campaign_revision_id": revision,
        "horizon": horizon,
        "anchor_policy": "final-member-availability/v1",
        "campaign_available_at": campaign["formed_at"],
        "anchor_episode_id": campaign["members"][-1]["episode_id"],
        "computed_at": (
            "2026-09-03T20:37:25.569588Z" if quarantined else "2026-10-15T15:00:00Z"
        ),
        "status": "complete" if complete else "incomplete",
        "reason": "source_not_matured" if not complete else None,
        "target_time": "2026-10-15T15:00:00Z",
        "matured_at": "2026-10-15T15:00:00Z",
        "measurement": {
            "kind": "synthetic-test-measurement",
            "target_aligned": complete,
            "source_measurement_sha256": "a" * 64,
        },
        "underlying": {
            "status": "unavailable" if unavailable else "complete",
            "ret": None if unavailable else 0.01,
            "mfe": None if unavailable else 0.02,
            "mae": None if unavailable else -0.01,
        },
        "option": {
            "status": "unavailable",
            "reason": "no_executable_nbbo_quote_path",
            "quote_basis": None,
            "ret": None,
            "mfe": None,
            "mae": None,
        },
        "source_outcome": {
            "path": path,
            "row": ordinal,
            "row_sha256": "b" * 64,
            "schema": source_schema,
            "outcome_id": "oout_" + "c" * 24,
            "episode_id": campaign["members"][-1]["episode_id"],
            "horizon_anchor": campaign["formed_at"],
            "price_receipt_sha256": None,
            "price_source": None,
            "price_vintage": None,
            "source_receipt_schema": None,
        },
        "source_outcome_prefix": {
            "path": path,
            "records": ordinal,
            "prefix_sha256": "d" * 64,
        },
        "member_outcome_coverage": {
            "expected_member_count": len(campaign["members"]),
            "observed_member_count": 0,
            "references": [],
            "missing_episode_ids": [m["episode_id"] for m in campaign["members"]],
        },
        "label_authority": "research_only",
        "training_eligible": False,
        "authority": dict(campaign_engine.FALSE_AUTHORITY),
    }
    raw = canonical_bytes(value)
    return LedgerRow(value, ordinal, raw, hashlib.sha256(raw).hexdigest())


def _view(monkeypatch, campaigns, rows):
    outcomes = correction_fixture._snapshot(rows, "outcomes")
    policy = correction_fixture._small_policy(
        campaign_count=campaigns.count,
        lawful_count=2,
        incident_count=3,
        quarantine_count=1,
        computed_at="2026-09-03T20:37:25.569588Z",
        campaign_snapshot=correction_fixture._relabel(
            campaigns, campaign_engine.CAMPAIGNS_PATH
        ),
        outcome_snapshot=outcomes,
    )
    monkeypatch.setattr(
        campaign_engine.CorrectionPolicy, "load_canonical", lambda root_dir=None: policy
    )

    def verify(p, physical_campaigns, physical_outcomes):
        generation, lawful = p.incident_generation, p.value["lawful_prefix"]["outcomes"]
        if (
            physical_campaigns.count < generation["campaigns"]["records"]
            or physical_outcomes.count < generation["outcomes"]["records"]
        ):
            raise CampaignContractError("synthetic source shorter than incident")
        if (
            _prefix_sha256(physical_campaigns, generation["campaigns"]["records"])
            != generation["campaigns"]["prefix_sha256"]
        ):
            raise CampaignContractError("synthetic campaign prefix changed")
        if (
            _prefix_sha256(physical_outcomes, generation["outcomes"]["records"])
            != generation["outcomes"]["prefix_sha256"]
        ):
            raise CampaignContractError("synthetic outcome prefix changed")
        if (
            _prefix_sha256(physical_outcomes, lawful["records"])
            != lawful["prefix_sha256"]
        ):
            raise CampaignContractError("synthetic lawful prefix changed")
        return lawful["records"], generation["outcomes"]["records"]

    monkeypatch.setattr(campaign_engine, "_verify_policy_prefixes", verify)
    receipt = correction_fixture._receipt(policy)
    return (
        build_effective_outcome_view(
            campaigns, outcomes, policy, activation_receipt=receipt
        ),
        receipt,
    )


def _candidate(monkeypatch, tmp_path):
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    initial = candidate_fixture._episodes_for(True, count=2)
    candidate_fixture._build_campaign_snapshot(
        tmp_path, episodes_specs=initial, monkeypatch=monkeypatch
    )
    specs = candidate_fixture._episodes_for(True, count=3)
    campaigns = candidate_fixture._build_campaign_snapshot(
        tmp_path, episodes_specs=specs, monkeypatch=monkeypatch
    )
    micro = {
        s["source_event_id"]: candidate_fixture._micro_for(
            s["source_event_id"], available_at=s["available_at"]
        )
        for s in specs
    }
    feed = compose_candidate_feed(
        **candidate_fixture._composer_kwargs(
            campaigns, micro_map=micro, activation=candidate_fixture.ACTIVATION_RECEIPT
        )
    )
    return feed, campaigns, campaigns.rows[0].value


def _history_bytes(candidate):
    value = copy.deepcopy(candidate)
    value.pop(enrichment.POST_FORMATION_KEY, None)
    value.pop(enrichment.CAMPAIGN_CONTEXT_KEY, None)
    return canonical_bytes(value)


def test_real_composed_feed_joins_effective_view_only_and_reseals(
    tmp_path, monkeypatch
):
    feed, campaigns, campaign = _candidate(monkeypatch, tmp_path)
    rows = [
        _row(campaign, "h60", 1),
        _row(campaign, "eod", 2, complete=False),
        _row(campaign, "1d", 3, quarantined=True),
        _row(campaign, "5d", 4),
        _row(campaign, "10d", 5),
        _row(campaign, "3d", 6, complete=False, unavailable=True),
    ]
    view, receipt = _view(monkeypatch, campaigns, rows)
    original_history = _history_bytes(feed["formed_candidates"][0])
    assert (
        feed["formed_candidates"][0]["first_qualifying_campaign_revision_id"]
        != feed["formed_candidates"][0]["current_campaign_revision_id"]
    )
    enriched = enrichment.enrich_candidate_outcomes(
        feed, effective_outcomes=view, correction_activation_receipt=receipt
    )
    again = enrichment.enrich_candidate_outcomes(
        enriched, effective_outcomes=view, correction_activation_receipt=receipt
    )
    horizons = enriched["formed_candidates"][0][enrichment.POST_FORMATION_KEY][
        "horizons"
    ]
    assert again == enriched
    assert (
        horizons["h60"]["state"] == "available"
        and horizons["eod"]["state"] == "unavailable"
    )
    assert (
        horizons["1d"]["state"] == "unavailable"
        and horizons["1d"]["campaign_outcome_id"] is None
    )
    assert horizons["3d"]["state"] == "unavailable" and set(horizons) == set(
        enrichment.HORIZONS
    )
    assert _history_bytes(enriched["formed_candidates"][0]) == original_history
    assert (
        enriched["formed_candidates"][0]["candidate_id"]
        == feed["formed_candidates"][0]["candidate_id"]
    )
    assert (
        enriched["formed_candidates"][0]["frozen_formation"]
        == feed["formed_candidates"][0]["frozen_formation"]
    )


def test_tail_changes_only_outcomes_and_real_view_rejects_duplicate_or_malformed_rows(
    tmp_path, monkeypatch
):
    feed, campaigns, campaign = _candidate(monkeypatch, tmp_path)
    base = [
        _row(campaign, "h60", 1),
        _row(campaign, "eod", 2),
        _row(campaign, "1d", 3, quarantined=True),
        _row(campaign, "5d", 4),
        _row(campaign, "10d", 5),
    ]
    first_view, receipt = _view(monkeypatch, campaigns, base)
    first = enrichment.enrich_candidate_outcomes(
        feed, effective_outcomes=first_view, correction_activation_receipt=receipt
    )
    second_view, receipt = _view(
        monkeypatch, campaigns, base + [_row(campaign, "3d", 6)]
    )
    second = enrichment.enrich_candidate_outcomes(
        first, effective_outcomes=second_view, correction_activation_receipt=receipt
    )
    assert _history_bytes(first["formed_candidates"][0]) == _history_bytes(
        second["formed_candidates"][0]
    )
    assert (
        first["formed_candidates"][0][enrichment.POST_FORMATION_KEY]["horizons"]["3d"][
            "state"
        ]
        == "pending"
    )
    assert (
        second["formed_candidates"][0][enrichment.POST_FORMATION_KEY]["horizons"]["3d"][
            "state"
        ]
        == "available"
    )
    assert first["feed_id"] != second["feed_id"]
    with pytest.raises(CampaignContractError, match="duplicate campaign outcome key"):
        _view(monkeypatch, campaigns, base + [_row(campaign, "5d", 6)])
    malformed = _row(campaign, "3d", 6)
    del malformed.value["underlying"]
    raw = canonical_bytes(malformed.value)
    malformed = LedgerRow(
        malformed.value, malformed.ordinal, raw, hashlib.sha256(raw).hexdigest()
    )
    malformed_view, receipt = _view(monkeypatch, campaigns, base + [malformed])
    with pytest.raises(CampaignContractError):
        enrichment.enrich_candidate_outcomes(
            feed,
            effective_outcomes=malformed_view,
            correction_activation_receipt=receipt,
        )


def test_campaign_context_is_canonical_copied_and_frozen_source_bound(
    tmp_path, monkeypatch
):
    feed, campaigns, campaign = _candidate(monkeypatch, tmp_path)
    view, receipt = _view(
        monkeypatch,
        campaigns,
        [
            _row(campaign, "h60", 1),
            _row(campaign, "eod", 2),
            _row(campaign, "1d", 3, quarantined=True),
        ],
    )
    expected_group = copy.deepcopy(campaign["group"])
    expected_counts = copy.deepcopy(campaign["descriptive"]["flow_side_counts"])
    expected_intent = copy.deepcopy(campaign["intent"])

    enriched = enrichment.enrich_candidate_outcomes(
        feed, effective_outcomes=view, correction_activation_receipt=receipt
    )
    context = enriched["formed_candidates"][0][enrichment.CAMPAIGN_CONTEXT_KEY]
    assert context == {
        "schema": "options.alpha_candidate_campaign_context/v1",
        "campaign_revision_id": campaign["campaign_revision_id"],
        "group": expected_group,
        "flow_side_counts": expected_counts,
        "intent": expected_intent,
    }
    pristine = copy.deepcopy(enriched)
    context["group"]["ticker"] = "MUTATED"
    context["flow_side_counts"]["~buy"] = 999
    context["intent"]["direction_reliability"] = "MUTATED"
    assert campaign["group"] == expected_group
    assert campaign["descriptive"]["flow_side_counts"] == expected_counts
    assert campaign["intent"] == expected_intent
    assert (
        enrichment.enrich_candidate_outcomes(
            pristine, effective_outcomes=view, correction_activation_receipt=receipt
        )
        == pristine
    )


def test_campaign_context_refuses_wrong_frozen_revision_or_source_hash(
    tmp_path, monkeypatch
):
    feed, campaigns, campaign = _candidate(monkeypatch, tmp_path)
    view, receipt = _view(
        monkeypatch,
        campaigns,
        [
            _row(campaign, "h60", 1),
            _row(campaign, "eod", 2),
            _row(campaign, "1d", 3, quarantined=True),
        ],
    )

    wrong_revision = copy.deepcopy(feed)
    wrong_revision["formed_candidates"][0]["first_qualifying_campaign_revision_id"] = (
        wrong_revision["formed_candidates"][0]["current_campaign_revision_id"]
    )
    with pytest.raises(
        enrichment.CandidateOutcomeEnrichmentError,
        match="campaign context frozen revision mismatch",
    ):
        enrichment.enrich_candidate_outcomes(
            wrong_revision,
            effective_outcomes=view,
            correction_activation_receipt=receipt,
        )

    wrong_hash = copy.deepcopy(feed)
    wrong_hash["formed_candidates"][0]["versioned_updates"][0][
        "revision_digest_sha256"
    ] = ("0" * 64)
    with pytest.raises(
        enrichment.CandidateOutcomeEnrichmentError,
        match="campaign context source hash mismatch",
    ):
        enrichment.enrich_candidate_outcomes(
            wrong_hash, effective_outcomes=view, correction_activation_receipt=receipt
        )
