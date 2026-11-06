"""Boundary checks for the daily candidate publisher integration."""

from __future__ import annotations

from pathlib import Path

import sys
import copy
import json
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from scripts import build_options_alpha_candidate_feed as builder


def test_absent_activation_is_structured_inert_and_never_touches_client_or_clock(
    tmp_path,
):
    class ExplosiveClient:
        def __getattr__(self, name):
            raise AssertionError(f"inactive run touched R2: {name}")

    def clock():
        raise AssertionError("inactive run invented/observed a clock")

    assert builder.run(
        root=tmp_path, client=ExplosiveClient(), bucket="test", clock=clock
    ) == {
        "produced": False,
        "state": "inactive",
        "reason": "activation_receipt_absent",
    }


def test_real_staged_decision_availability_projects_original_measurements(monkeypatch):
    # The real date-keyed parser is used, including its decision/availability
    # ordering and durable availability binding; yaml is only an optional
    # config dependency of its transport module.
    event = {
        "id": "evt_1",
        "ts": "2026-08-14T14:01:00Z",
        "observed_at": "2026-08-14T14:01:02Z",
        "microstructure": {
            "schema": "options.trade_nbbo_microstructure/v1",
            "source_print_count": 1,
            "nbbo_valid_print_count": 1,
            "nbbo_premium_coverage": 0.25,
            "nbbo_covered_premium_usd": 25.0,
            "source_premium_usd": 100.0,
            "nbbo_print_coverage": 1.0,
            "at_ask_share": None,
            "at_bid_share": None,
            "inside_share": None,
            "outside_share": None,
            "aggression_share": None,
            "aggression_balance": None,
            "spread_median_usd": None,
            "spread_median_pct": None,
            "quote_age_median_ms": None,
            "quote_age_max_ms": None,
        },
    }
    records = [
        {
            "schema": "live_flow.event_stage/v1",
            "kind": "decision",
            "event_id": "evt_1",
            "event": event,
        },
        {
            "schema": "live_flow.event_stage/v1",
            "kind": "availability",
            "event_id": "evt_1",
            "available_at": "2026-08-14T14:02:00Z",
        },
        {
            "schema": "live_flow.event_stage/v1",
            "kind": "decision",
            "event_id": "legacy_1",
            "event": {
                "id": "legacy_1",
                "ts": "2026-08-14T14:03:00Z",
                "observed_at": "2026-08-14T14:03:00Z",
            },
        },
        {
            "schema": "live_flow.event_stage/v1",
            "kind": "availability",
            "event_id": "legacy_1",
            "available_at": "2026-08-14T14:03:01Z",
        },
    ]
    projected = builder._microstructure(records, "2026-08-14")["evt_1"]
    for key in builder._MEASURED:
        value = event["microstructure"][key]
        assert projected[key] == value
    assert set(builder._microstructure(records, "2026-08-14")) == {"evt_1"}
    event["microstructure"].pop("source_premium_usd")
    assert builder._microstructure(records, "2026-08-14") == {}


def test_active_real_composer_enricher_and_publisher_preserve_candidate_identity(
    tmp_path, monkeypatch
):
    """Exercise the live boundary with real campaign snapshot/view machinery."""
    import test_options_alpha_candidate_feed as candidate_fixture
    import test_options_alpha_candidate_outcome_enrichment as enrichment_fixture
    import engine.options_signal_campaign as campaign_engine
    from test_publish_options_alpha_candidate_r2 import FakeS3

    feed, campaigns, campaign = enrichment_fixture._candidate(monkeypatch, tmp_path)
    view, correction = enrichment_fixture._view(
        monkeypatch,
        campaigns,
        [
            enrichment_fixture._row(campaign, "h60", 1),
            enrichment_fixture._row(campaign, "eod", 2),
            enrichment_fixture._row(campaign, "1d", 3, quarantined=True),
        ],
    )
    # The active composition fixture intentionally uses a small correction
    # incident; the full-count test below owns real checkpoint validation.
    monkeypatch.setattr(
        builder,
        "_load_sources",
        lambda root, receipt_path: (campaigns, view, correction),
    )
    root = tmp_path / "runtime"
    correction_path = root / builder.CORRECTION_RECEIPT_PATH
    (root / builder.ACTIVATION_PATH).parent.mkdir(parents=True)
    (root / builder.ACTIVATION_PATH).write_text(
        json.dumps(candidate_fixture.ACTIVATION_RECEIPT), encoding="utf-8"
    )
    (root / builder.POLICY_PATH).write_text(
        json.dumps(candidate_fixture.POLICY), encoding="utf-8"
    )
    measured = {
        "schema": "options.trade_nbbo_microstructure/v1",
        "source_print_count": 4,
        "nbbo_valid_print_count": 3,
        "nbbo_premium_coverage": 0.9,
        "nbbo_covered_premium_usd": 900000.0,
        "source_premium_usd": 1000000.0,
        "nbbo_print_coverage": 0.75,
        "at_ask_share": None,
        "at_bid_share": None,
        "inside_share": None,
        "outside_share": None,
        "aggression_share": None,
        "aggression_balance": None,
        "spread_median_usd": None,
        "spread_median_pct": None,
        "quote_age_median_ms": None,
        "quote_age_max_ms": None,
    }

    def stage(session):
        rows = []
        for event_id, stamp in zip(
            ("evt-000", "evt-001", "evt-002"),
            ("2026-08-13T14:00:00Z", "2026-08-13T14:00:30Z", "2026-08-13T14:01:00Z"),
        ):
            event = {
                "id": event_id,
                "ts": stamp,
                "observed_at": stamp,
                "microstructure": copy.deepcopy(measured),
            }
            rows.extend(
                (
                    {
                        "schema": "live_flow.event_stage/v1",
                        "kind": "decision",
                        "event_id": event_id,
                        "event": event,
                    },
                    {
                        "schema": "live_flow.event_stage/v1",
                        "kind": "availability",
                        "event_id": event_id,
                        "available_at": stamp,
                    },
                )
            )
        return rows

    s3 = FakeS3()
    # Outcome rows record 2026-10-15 facts. The publication clock must not
    # precede those facts; the August event session below stays historical.
    ticks = iter(
        [
            "2026-10-16T15:00:00Z",
            "2026-10-16T15:01:00Z",
            "2026-10-16T15:02:00Z",
            "2026-10-16T15:03:00Z",
            "2026-10-16T15:04:00Z",
            "2026-10-16T15:05:00Z",
            "2026-10-16T15:06:00Z",
            "2026-10-16T15:07:00Z",
        ]
    )
    clock = lambda: next(ticks)
    first = builder.run(
        root=root,
        client=s3,
        bucket="b",
        clock=clock,
        sessions=lambda: ["2026-08-13"],
        fetch=stage,
    )
    first_sealed = builder.read_pair(s3, "b")
    assert first_sealed is not None
    candidate_id = first_sealed.feed["formed_candidates"][0]["candidate_id"]
    first_external = first_sealed.receipt_last_modified
    second = builder.run(
        root=root,
        client=s3,
        bucket="b",
        clock=clock,
        sessions=lambda: ["2026-08-13"],
        fetch=stage,
    )
    assert first["produced"] and second["produced"]
    sealed = builder.read_pair(s3, "b")
    assert sealed is not None
    assert (
        sealed.feed["formed_candidates"][0]["candidate_id"]
        == feed["formed_candidates"][0]["candidate_id"]
    )
    assert (
        sealed.receipt["candidates"][candidate_id]["first_consumer_published_at"]
        == first_external
    )
    assert "post_formation_outcomes" in sealed.feed["formed_candidates"][0]


def test_load_sources_reads_full_receipted_v2_checkpoint_from_filesystem(
    tmp_path, monkeypatch
):
    """Isolated full-count proof of the reader/checkpoint/effective-view seam.

    The existing fixture uses production incident counts and hashes.  Its
    episode/H60/session bytes are deliberately relabelled outcome bytes because
    this test proves receipt/checkpoint plumbing, not economic episode labels.
    """
    import engine.options_signal_campaign as campaign_engine
    import test_options_signal_campaign_effective_view as effective_fixture

    campaigns, outcomes = effective_fixture._bound_snapshot()
    policy = effective_fixture._bound_policy(campaigns, outcomes)
    monkeypatch.setattr(
        campaign_engine.CorrectionPolicy, "load_canonical", lambda root_dir=None: policy
    )
    receipt = effective_fixture._receipt(policy)
    view = campaign_engine.build_effective_outcome_view(
        campaigns, outcomes, policy, activation_receipt=receipt
    )
    episodes = effective_fixture._relabel(outcomes, campaign_engine.EPISODES_PATH)
    h60 = effective_fixture._relabel(outcomes, campaign_engine.H60_PATH)
    session = effective_fixture._relabel(outcomes, campaign_engine.SESSION_PATH)
    checkpoint = campaign_engine._build_effective_checkpoint(
        episodes, h60, session, view, receipt
    )
    for path, snapshot in (
        (campaign_engine.CAMPAIGNS_PATH, campaigns),
        (campaign_engine.OUTCOMES_PATH, outcomes),
        (campaign_engine.EPISODES_PATH, episodes),
        (campaign_engine.H60_PATH, h60),
        (campaign_engine.SESSION_PATH, session),
    ):
        destination = tmp_path / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(snapshot.raw)
    checkpoint_path = tmp_path / campaign_engine.CHECKPOINT_PATH
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path.write_bytes(campaign_engine.canonical_bytes(checkpoint) + b"\n")
    correction_path = tmp_path / builder.CORRECTION_RECEIPT_PATH
    correction_path.parent.mkdir(parents=True, exist_ok=True)
    correction_path.write_bytes(campaign_engine.canonical_bytes(receipt) + b"\n")

    loaded_campaigns, loaded_view, loaded_receipt = builder._load_sources(
        tmp_path, correction_path
    )
    assert loaded_campaigns.digest == campaigns.digest
    assert loaded_view.raw_count == outcomes.count
    assert loaded_view.effective_count == view.effective_count
    assert loaded_receipt == receipt

    # A changed prefix or a physical tail beyond the accepted checkpoint is
    # never a valid consumer snapshot, even when its JSON remains well formed.
    campaign_path = tmp_path / campaign_engine.CAMPAIGNS_PATH
    changed = copy.deepcopy(campaigns.rows[0].value)
    changed["campaign_outcome_id"] += "-changed"
    campaign_path.write_bytes(
        campaign_engine.canonical_bytes(changed)
        + b"\n"
        + b"".join(row.raw + b"\n" for row in campaigns.rows[1:])
    )
    with pytest.raises(campaign_engine.CampaignContractError):
        builder._load_sources(tmp_path, correction_path)
    campaign_path.write_bytes(campaigns.raw)
    outcome_path = tmp_path / campaign_engine.OUTCOMES_PATH
    outcome_path.write_bytes(outcomes.raw + outcomes.rows[-1].raw + b"\n")
    with pytest.raises(
        (campaign_engine.CampaignContractError, builder.DailyCandidateError)
    ):
        builder._load_sources(tmp_path, correction_path)
    outcome_path.write_bytes(outcomes.raw)

    checkpoint_path.unlink()
    with pytest.raises(builder.DailyCandidateError, match="effective v2"):
        builder._load_sources(tmp_path, correction_path)


@pytest.mark.parametrize("client,bucket", [(None, "b"), (object(), "")])
def test_active_configuration_refuses_before_source_or_recovery(
    tmp_path, monkeypatch, client, bucket
):
    import test_options_alpha_candidate_feed as candidate_fixture

    for path, value in (
        (builder.ACTIVATION_PATH, candidate_fixture.ACTIVATION_RECEIPT),
        (builder.POLICY_PATH, candidate_fixture.POLICY),
    ):
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value))

    def unexpected(*args, **kwargs):
        raise AssertionError("configuration refusal reached source or recovery")

    monkeypatch.setattr(builder, "_load_sources", unexpected)
    monkeypatch.setattr(builder, "recover_pending_pair", unexpected)
    with pytest.raises(builder.DailyCandidateError, match="configured R2"):
        builder.run(root=tmp_path, client=client, bucket=bucket)


def test_invalid_activation_refuses_before_pending_recovery(tmp_path, monkeypatch):
    import test_options_alpha_candidate_feed as candidate_fixture
    from engine.options_alpha_candidate_feed import CandidateFeedContractError

    receipt = copy.deepcopy(candidate_fixture.ACTIVATION_RECEIPT)
    receipt["activation_disposition"]["state"] = "blocked"
    for path, value in (
        (builder.ACTIVATION_PATH, receipt),
        (builder.POLICY_PATH, candidate_fixture.POLICY),
    ):
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value))

    def unexpected(*args, **kwargs):
        raise AssertionError("invalid activation reached recovery")

    monkeypatch.setattr(builder, "recover_pending_pair", unexpected)
    monkeypatch.setattr(builder, "_load_publisher_journal", unexpected)
    with pytest.raises(CandidateFeedContractError):
        builder.run(root=tmp_path, client=object(), bucket="b")
