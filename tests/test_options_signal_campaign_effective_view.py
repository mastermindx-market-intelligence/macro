from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest

import engine.options_signal_campaign as campaign_engine
from engine.options_signal_campaign import (
    CORRECTION_POLICY_PATH,
    CORRECTION_POLICY_SHA256,
    EPISODES_PATH,
    FALSE_AUTHORITY,
    H60_PATH,
    SESSION_PATH,
    CampaignContractError,
    CorrectionPolicy,
    LedgerRow,
    LedgerSnapshot,
    _sha256,
    _build_effective_checkpoint,
    _campaign_outcome_key,
    _derive_campaign_outcomes_from_maps,
    _checkpoint_id,
    _key_digest,
    _prefix_sha256,
    _load_checkpoint,
    _verify_checkpoint,
    build_effective_outcome_view,
    canonical_bytes,
)


ROOT = Path(__file__).resolve().parent.parent
LAWFUL_COUNT = 24578
INCIDENT_COUNT = 28423
QUARANTINE_COUNT = INCIDENT_COUNT - LAWFUL_COUNT
COMPUTED_AT = "2026-09-03T20:37:25.569588Z"


def _row(name: str, ordinal: int, *, computed_at: str = "2026-09-02T20:00:00Z") -> LedgerRow:
    value = {
        "schema": "options.signal_campaign_outcome/v1",
        "campaign_outcome_id": f"ocout_{name}",
        "campaign_revision_id": f"ocrev_{name}",
        "horizon": "h60",
        "computed_at": computed_at,
        "authority": dict(FALSE_AUTHORITY),
    }
    raw = canonical_bytes(value)
    return LedgerRow(value, ordinal, raw, hashlib.sha256(raw).hexdigest())


def _snapshot(rows: list[LedgerRow], label: str) -> LedgerSnapshot:
    raw = b"".join(row.raw + b"\n" for row in rows)
    path = (
        label
        if label.startswith("data/")
        else f"data/options_signal_campaign/{label}.jsonl"
    )
    digest = hashlib.sha256(raw).hexdigest()
    return LedgerSnapshot(Path(path), path, tuple(rows), raw, digest)


def _relabel(snapshot: LedgerSnapshot, label: str) -> LedgerSnapshot:
    return LedgerSnapshot(Path(label), label, snapshot.rows, snapshot.raw, snapshot.digest)


def _bound_snapshot():
    lawful = [_row(f"lawful-{index}", index) for index in range(1, LAWFUL_COUNT + 1)]
    quarantined = [
        _row(f"quarantine-{index}", LAWFUL_COUNT + index, computed_at=COMPUTED_AT)
        for index in range(1, QUARANTINE_COUNT + 1)
    ]
    tail = [_row(f"tail-{index}", INCIDENT_COUNT + index) for index in range(1, 21)]
    campaign_snapshot = _snapshot(
        [_row(f"campaign-{index}", index, computed_at=COMPUTED_AT) for index in range(1, 8386)],
        "campaigns",
    )
    outcome_snapshot = _snapshot([*lawful, *quarantined, *tail], "outcomes")
    return campaign_snapshot, outcome_snapshot


def _bound_policy(campaigns: LedgerSnapshot, outcomes: LedgerSnapshot) -> CorrectionPolicy:
    policy = CorrectionPolicy.load_canonical(ROOT)
    value = copy.deepcopy(policy.value)
    value["incident_generation"]["campaigns"]["prefix_sha256"] = _prefix_sha256(
        campaigns, 8385
    )
    value["incident_generation"]["outcomes"]["prefix_sha256"] = _prefix_sha256(
        outcomes, INCIDENT_COUNT
    )
    value["lawful_prefix"]["outcomes"]["prefix_sha256"] = _prefix_sha256(
        outcomes, LAWFUL_COUNT
    )
    return CorrectionPolicy(policy.path, policy.file_sha256, value)


def _receipt(policy: CorrectionPolicy, *, active: bool = True) -> dict:
    value = {
        "schema": "options.signal_campaign_correction_activation/v1",
        "receipt_id": "synthetic-campaign-correction-receipt",
        "activated_at": "2026-10-03T00:00:00Z",
        "receipt_sha256": "0" * 64,
        "policy": {
            "policy_id": policy.value["policy_id"],
            "policy_version": policy.value["policy_version"],
            "path": CORRECTION_POLICY_PATH.as_posix(),
            "file_sha256": policy.file_sha256,
        },
        "activation_preconditions": {
            name: active for name in policy.activation_preconditions
        },
    }
    unsigned = dict(value)
    del unsigned["receipt_sha256"]
    value["receipt_sha256"] = _sha256(canonical_bytes(unsigned))
    return value


def test_default_policy_is_exact_and_implementation_remains_inactive(
    monkeypatch: pytest.MonkeyPatch,) -> None:
    campaigns, outcomes = _bound_snapshot()
    policy = _bound_policy(campaigns, outcomes)
    monkeypatch.setattr(
        campaign_engine.CorrectionPolicy, "load_canonical", lambda root_dir=None: policy
    )
    assert policy.file_sha256 == CORRECTION_POLICY_SHA256
    assert policy.quarantine["record_count"] == QUARANTINE_COUNT
    with pytest.raises(CampaignContractError, match="activation receipt"):
        build_effective_outcome_view(campaigns, outcomes, policy)


def test_effective_view_preserves_original_rows_and_reserves_quarantined_keys(
    monkeypatch: pytest.MonkeyPatch,) -> None:
    campaigns, outcomes = _bound_snapshot()
    policy = _bound_policy(campaigns, outcomes)
    monkeypatch.setattr(
        campaign_engine.CorrectionPolicy, "load_canonical", lambda root_dir=None: policy
    )
    view = build_effective_outcome_view(
        campaigns, outcomes, policy, activation_receipt=_receipt(policy)
    )
    assert view.raw_count == INCIDENT_COUNT + 20
    assert view.effective_count == LAWFUL_COUNT + 20
    assert len(view.quarantined_rows) == QUARANTINE_COUNT
    assert all(item.ordinal == index for index, item in enumerate(view.outcomes.rows, 1))
    assert view.admitted_rows == (
        outcomes.rows[:LAWFUL_COUNT] + outcomes.rows[INCIDENT_COUNT:]
    )
    assert len(view.occupied_keys) == outcomes.count
    assert view.admitted_rows[0] is outcomes.rows[0]
    assert view.quarantined_rows[0] is outcomes.rows[LAWFUL_COUNT]


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        ("shrink", "shorter than incident"),
        ("campaign_mutation", "campaign incident prefix changed"),
        ("outcome_mutation", "outcome incident prefix changed"),
        ("shift", "incident identity"),
    ],
)
def test_actual_prefix_law_rejects_shrink_mutation_and_shift(
    monkeypatch: pytest.MonkeyPatch,
    mutation: str, match: str
) -> None:
    campaigns, outcomes = _bound_snapshot()
    policy = _bound_policy(campaigns, outcomes)
    monkeypatch.setattr(
        campaign_engine.CorrectionPolicy, "load_canonical", lambda root_dir=None: policy
    )
    receipt = _receipt(policy)
    if mutation == "shrink":
        outcomes = _snapshot(list(outcomes.rows[:INCIDENT_COUNT - 1]), outcomes.label)
    elif mutation == "campaign_mutation":
        changed = _row("campaign-mutation", 1)
        changed_rows = [changed, *campaigns.rows[1:]]
        campaigns = _snapshot(changed_rows, campaigns.label)
    elif mutation == "outcome_mutation":
        changed = _row("lawful-mutation", 1)
        changed_rows = [changed, *outcomes.rows[1:]]
        outcomes = _snapshot(changed_rows, outcomes.label)
    else:
        changed = copy.deepcopy(outcomes.rows[LAWFUL_COUNT])
        changed.value["computed_at"] = "2026-09-03T20:37:25.569589Z"
        changed_rows = [*outcomes.rows[:LAWFUL_COUNT - 1], changed, *outcomes.rows[LAWFUL_COUNT + 1:]]
        outcomes = _snapshot(changed_rows, outcomes.label)
        policy = _bound_policy(campaigns, outcomes)
    monkeypatch.setattr(
        campaign_engine.CorrectionPolicy, "load_canonical", lambda root_dir=None: policy
    )
    with pytest.raises(CampaignContractError, match=match):
        build_effective_outcome_view(campaigns, outcomes, policy, activation_receipt=receipt)


def test_activation_receipt_rejects_absence_malformed_and_unmet_precondition(
    monkeypatch: pytest.MonkeyPatch,) -> None:
    campaigns, outcomes = _bound_snapshot()
    policy = _bound_policy(campaigns, outcomes)
    monkeypatch.setattr(
        campaign_engine.CorrectionPolicy, "load_canonical", lambda root_dir=None: policy
    )
    malformed = _receipt(policy)
    malformed["receipt_sha256"] = "1" * 64
    ineligible = _receipt(policy, active=False)
    for receipt in (None, {}, malformed, ineligible):
        with pytest.raises(CampaignContractError, match="activation"):
            build_effective_outcome_view(campaigns, outcomes, policy, activation_receipt=receipt)


def test_duplicate_keys_across_quarantine_admitted_and_tail_reject(
    monkeypatch: pytest.MonkeyPatch,) -> None:
    campaigns, outcomes = _bound_snapshot()
    policy = _bound_policy(campaigns, outcomes)
    monkeypatch.setattr(
        campaign_engine.CorrectionPolicy, "load_canonical", lambda root_dir=None: policy
    )
    duplicate = copy.deepcopy(outcomes.rows[LAWFUL_COUNT].value)
    duplicate["computed_at"] = "2026-09-02T20:00:00Z"
    raw = canonical_bytes(duplicate)
    raw_digest = hashlib.sha256(raw).hexdigest()
    duplicate_row = LedgerRow(
        duplicate, outcomes.count + 1, raw, raw_digest
    )
    outcomes = _snapshot([*outcomes.rows, duplicate_row], outcomes.label)
    with pytest.raises(CampaignContractError, match="duplicate"):
        build_effective_outcome_view(
            campaigns, outcomes, policy, activation_receipt=_receipt(policy)
        )


def test_effective_view_admits_only_nonquarantined_keys(
    monkeypatch: pytest.MonkeyPatch,) -> None:
    campaigns, outcomes = _bound_snapshot()
    policy = _bound_policy(campaigns, outcomes)
    monkeypatch.setattr(
        campaign_engine.CorrectionPolicy, "load_canonical", lambda root_dir=None: policy
    )
    view = build_effective_outcome_view(
        campaigns, outcomes, policy, activation_receipt=_receipt(policy)
    )
    quarantined_key = _campaign_outcome_key(view.quarantined_rows[0].value)
    assert quarantined_key not in view.admitted_keys
    assert quarantined_key in view.occupied_keys
    assert view.occupied_keys


def test_v2_checkpoint_is_strict_receipt_bound_and_replay_idempotent(
    monkeypatch: pytest.MonkeyPatch,tmp_path: Path) -> None:
    campaigns, outcomes = _bound_snapshot()
    policy = _bound_policy(campaigns, outcomes)
    monkeypatch.setattr(
        campaign_engine.CorrectionPolicy, "load_canonical", lambda root_dir=None: policy
    )
    receipt = _receipt(policy)
    view = build_effective_outcome_view(campaigns, outcomes, policy, activation_receipt=receipt)
    episodes = _relabel(outcomes, EPISODES_PATH)
    h60 = _relabel(outcomes, H60_PATH)
    session = _relabel(outcomes, SESSION_PATH)
    checkpoint = _build_effective_checkpoint(episodes, h60, session, view, receipt)
    assert checkpoint["schema"] == "options.signal_campaign_checkpoint/v2"
    assert checkpoint["correction"]["physical_raw_outcomes"] == outcomes.count
    assert checkpoint["correction"]["effective_outcomes"] == view.effective_count
    assert checkpoint["correction"]["reserved_keys"]["count"] == outcomes.count
    assert checkpoint["correction"]["reserved_keys"]["digest"] == _key_digest(view.occupied_keys)
    path = tmp_path / "checkpoint.json"
    path.write_bytes(canonical_bytes(checkpoint) + b"\n")
    loaded = _load_checkpoint(path)
    assert loaded == checkpoint
    _verify_checkpoint(
        loaded,
        _relabel(outcomes, EPISODES_PATH),
        _relabel(outcomes, H60_PATH),
        _relabel(outcomes, SESSION_PATH),
        campaigns,
        outcomes,
    )
    rebuilt = _build_effective_checkpoint(episodes, h60, session, view, receipt)
    assert rebuilt == checkpoint


def test_corrupted_v2_metadata_rejects(
    monkeypatch: pytest.MonkeyPatch,tmp_path: Path) -> None:
    campaigns, outcomes = _bound_snapshot()
    policy = _bound_policy(campaigns, outcomes)
    monkeypatch.setattr(
        campaign_engine.CorrectionPolicy, "load_canonical", lambda root_dir=None: policy
    )
    receipt = _receipt(policy)
    view = build_effective_outcome_view(campaigns, outcomes, policy, activation_receipt=receipt)
    checkpoint = _build_effective_checkpoint(
        _relabel(outcomes, EPISODES_PATH),
        _relabel(outcomes, H60_PATH),
        _relabel(outcomes, SESSION_PATH),
        view,
        receipt,
    )
    checkpoint["correction"]["effective_outcomes"] += 1
    checkpoint["checkpoint_id"] = _checkpoint_id(
        checkpoint["sources"], checkpoint["outputs"]
    )
    path = tmp_path / "checkpoint.json"
    path.write_bytes(canonical_bytes(checkpoint) + b"\n")
    loaded = _load_checkpoint(path)
    with pytest.raises(CampaignContractError, match="effective checkpoint metadata"):
        _verify_checkpoint(
            loaded,
            _relabel(outcomes, EPISODES_PATH),
            _relabel(outcomes, H60_PATH),
            _relabel(outcomes, SESSION_PATH),
            campaigns,
            outcomes,
        )


def test_receipt_cannot_substitute_a_synthetic_policy_object() -> None:
    campaigns, outcomes = _bound_snapshot()
    policy = _bound_policy(campaigns, outcomes)
    with pytest.raises(CampaignContractError, match="policy object is not canonical"):
        build_effective_outcome_view(
            campaigns, outcomes, policy, activation_receipt=_receipt(policy)
        )


def test_v1_default_output_and_incident_rejection_are_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.test_options_signal_campaign import _episode, _root

    monkeypatch.setenv("COLLECT_LANE", "nightly")
    root = _root(tmp_path, [_episode("one", "2026-08-10T14:02:00Z")])
    campaign_engine.run(root_dir=root)
    checkpoint = campaign_engine._load_checkpoint(root / campaign_engine.CHECKPOINT_PATH)
    assert checkpoint["schema"] == campaign_engine.CAMPAIGN_CHECKPOINT_SCHEMA

    campaign_path = root / campaign_engine.CAMPAIGNS_PATH
    outcome_path = root / campaign_engine.OUTCOMES_PATH
    campaign_bytes = campaign_path.read_bytes()
    outcome_bytes = outcome_path.read_bytes()
    campaign_engine._atomic_write(campaign_path, campaign_bytes[:-1])
    campaign_engine._atomic_write(outcome_path, outcome_bytes[:-1])
    with pytest.raises(campaign_engine.CampaignContractError, match="torn final line"):
        campaign_engine.run(root_dir=root)


def test_runtime_receipt_path_does_not_activate_without_eligible_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.test_options_signal_campaign import _episode, _root

    monkeypatch.delenv("COLLECT_LANE", raising=False)
    root = _root(tmp_path, [_episode("one", "2026-08-10T14:02:00Z")])
    campaigns, outcomes = _bound_snapshot()
    policy = _bound_policy(campaigns, outcomes)
    monkeypatch.setattr(
        campaign_engine.CorrectionPolicy,
        "load_canonical",
        lambda root_dir=None: policy,
    )
    default = campaign_engine.run(root_dir=root)
    assert default["checkpoint_id"].startswith("ocp_")
    assert not (root / campaign_engine.CHECKPOINT_PATH).exists()

    malformed = _receipt(policy)
    malformed["receipt_sha256"] = "1" * 64
    receipt_path = tmp_path / "activation-receipt.json"
    receipt_path.write_bytes(canonical_bytes(malformed) + b"\n")
    with pytest.raises(CampaignContractError, match="activation digest"):
        campaign_engine.run(
            root_dir=root,
            correction_activation_receipt_path=receipt_path,
        )

    eligible = _receipt(policy)
    effective_checkpoint = {
        "schema": campaign_engine.CAMPAIGN_CHECKPOINT_V2_SCHEMA,
        "checkpoint_id": default["checkpoint_id"],
    }
    monkeypatch.setattr(
        campaign_engine,
        "_load_activation_receipt",
        lambda path: eligible,
    )
    monkeypatch.setattr(
        campaign_engine,
        "_build_effective_checkpoint",
        lambda *args, **kwargs: effective_checkpoint,
    )
    effective = campaign_engine.run(
        root_dir=root,
        correction_activation_receipt_path=receipt_path,
    )
    assert effective["checkpoint_id"] == effective_checkpoint["checkpoint_id"]


def test_derivation_does_not_reissue_quarantined_or_admitted_keys() -> None:
    quarantined = _row("quarantined", 1, computed_at=COMPUTED_AT)
    campaign = _row("campaign", 1)
    campaign.value["members"] = [{"episode_id": "episode"}]
    campaign.value["campaign_revision_id"] = quarantined.value[
        "campaign_revision_id"
    ]
    campaigns = _snapshot([campaign], "campaigns")
    outcomes = _snapshot([quarantined], "outcomes")
    fresh, pending = _derive_campaign_outcomes_from_maps(
        campaigns,
        iter((quarantined,)),
        {},
        {},
        outcomes,
        outcomes,
    )
    assert fresh == []
    assert pending == 5


def test_derivation_honours_iterable_occupied_keys() -> None:
    rows = [_row("occupied", 1), _row("fresh", 2)]
    campaign = _row("campaign", 1)
    campaign.value["members"] = [
        {"episode_id": "episode"}
    ]
    campaigns = _snapshot([campaign], "campaigns")
    outcomes = _snapshot(rows, "outcomes")
    fresh, pending = _derive_campaign_outcomes_from_maps(
        campaigns,
        iter(rows[:1]),
        {},
        {},
        outcomes,
        outcomes,
    )
    assert fresh == []
    assert pending == 6
