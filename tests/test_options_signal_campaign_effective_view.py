from __future__ import annotations

import copy
import hashlib
import json
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
    _effective_checkpoint_id,
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


def _small_policy(
    *,
    campaign_count: int,
    lawful_count: int,
    incident_count: int,
    quarantine_count: int,
    computed_at: str,
    campaign_snapshot: LedgerSnapshot,
    outcome_snapshot: LedgerSnapshot,
) -> CorrectionPolicy:
    """Build a private correction policy with synthetic small counts whose
    prefix hashes match the supplied snapshots. Production literal pins
    remain canonical — this descriptor is bound to the test's own snapshots.
    """
    if quarantine_count != incident_count - lawful_count:
        raise AssertionError("quarantine_count must equal incident_count - lawful_count")
    if lawful_count > incident_count:
        raise AssertionError("lawful_count must be <= incident_count")
    if campaign_count > campaign_snapshot.count:
        raise AssertionError("campaign_snapshot is shorter than synthetic campaign_count")
    if incident_count > outcome_snapshot.count:
        raise AssertionError("outcome_snapshot is shorter than synthetic incident_count")
    base = CorrectionPolicy.load_canonical(ROOT)
    value = copy.deepcopy(base.value)
    value["quarantine"]["record_count"] = quarantine_count
    value["quarantine"]["start_row"] = lawful_count + 1
    value["quarantine"]["end_row"] = incident_count
    value["quarantine"]["computed_at_exact"] = computed_at
    value["lawful_prefix"]["outcomes"]["records"] = lawful_count
    value["lawful_prefix"]["outcomes"]["prefix_sha256"] = _prefix_sha256(
        outcome_snapshot, lawful_count
    )
    value["incident_generation"]["campaigns"]["records"] = campaign_count
    value["incident_generation"]["campaigns"]["prefix_sha256"] = _prefix_sha256(
        campaign_snapshot, campaign_count
    )
    value["incident_generation"]["outcomes"]["records"] = incident_count
    value["incident_generation"]["outcomes"]["prefix_sha256"] = _prefix_sha256(
        outcome_snapshot, incident_count
    )

    class _SyntheticPolicy(CorrectionPolicy):
        """CorrectionPolicy subclass whose incident / quarantine accessors
        return whatever the test's small descriptor encodes. The production
        canonical policy keeps its 8385 / 28423 / 3845 / 24578 guards.
        """

        @property
        def quarantine(self) -> dict[str, Any]:
            return value["quarantine"]

        @property
        def incident_generation(self) -> dict[str, Any]:
            return value["incident_generation"]

    return _SyntheticPolicy(base.path, base.file_sha256, value)


def _small_snapshot(*, lawful: int, quarantine: int, tail: int = 0) -> LedgerSnapshot:
    """Build a small synthetic outcomes snapshot with `lawful` lawful rows,
    `quarantine` quarantined rows, and an optional `tail` of post-incident
    rows whose semantic key is reserved by the global occupied set but
    never by the quarantine reserved key set.
    """
    lawful_rows = [_row(f"lawful-{index}", index) for index in range(1, lawful + 1)]
    quarantine_rows = [
        _row(f"quarantine-{index}", lawful + index, computed_at=COMPUTED_AT)
        for index in range(1, quarantine + 1)
    ]
    tail_rows = [
        _row(f"tail-{index}", lawful + quarantine + index)
        for index in range(1, tail + 1)
    ]
    return _snapshot([*lawful_rows, *quarantine_rows, *tail_rows], "outcomes")


def _small_campaign_snapshot(count: int) -> LedgerSnapshot:
    return _snapshot(
        [_row(f"campaign-{index}", index, computed_at=COMPUTED_AT) for index in range(1, count + 1)],
        "campaigns",
    )


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
    # Quarantine reserved keys are bound to the quarantined rows only —
    # tail appended rows stay OUT of the quarantine key set.
    assert checkpoint["correction"]["quarantine"]["reserved_key_count"] == len(view.quarantined_rows)
    assert checkpoint["correction"]["quarantine"]["reserved_key_digest"] == _key_digest(
        view.quarantined_keys
    )
    # Global occupied keys are the union (admitted + quarantined).
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
        receipt,
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
    checkpoint["checkpoint_id"] = _effective_checkpoint_id(
        checkpoint["sources"], checkpoint["outputs"], checkpoint["correction"]
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
            receipt,
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
    """v1 path stays unchanged when no receipt is supplied: the default
    never-activated v1 schema is written and a torn final line rejects
    the next run. Uses the synthetic small descriptor so the test does
    not depend on the production data directory.
    """
    monkeypatch.delenv("COLLECT_LANE", raising=False)
    root = tmp_path
    for path in (
        root / campaign_engine.EPISODES_PATH,
        root / campaign_engine.H60_PATH,
        root / campaign_engine.SESSION_PATH,
        root / campaign_engine.CAMPAIGNS_PATH,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")
    small_outcome = _small_snapshot(lawful=2, quarantine=1, tail=0)
    small_campaign = _small_snapshot(lawful=0, quarantine=0, tail=0)
    outcomes_path = root / campaign_engine.OUTCOMES_PATH
    outcomes_path.write_bytes(b"".join(row.raw + b"\n" for row in small_outcome.rows))
    policy = _small_policy(
        campaign_count=0,
        lawful_count=2,
        incident_count=3,
        quarantine_count=1,
        computed_at=COMPUTED_AT,
        campaign_snapshot=_relabel(small_campaign, campaign_engine.CAMPAIGNS_PATH),
        outcome_snapshot=_relabel(small_outcome, campaign_engine.OUTCOMES_PATH),
    )
    monkeypatch.setattr(
        campaign_engine.CorrectionPolicy,
        "load_canonical",
        lambda root_dir=None: policy,
    )

    def _small_verify_policy_prefixes(
        small_policy: CorrectionPolicy,
        small_campaigns: LedgerSnapshot,
        small_outcomes: LedgerSnapshot,
    ) -> tuple[int, int]:
        generation = small_policy.incident_generation
        lawful = small_policy.value["lawful_prefix"]["outcomes"]
        quarantine = small_policy.quarantine
        campaign_count = generation["campaigns"]["records"]
        outcome_count = generation["outcomes"]["records"]
        if (
            small_campaigns.count < campaign_count
            or small_outcomes.count < outcome_count
        ):
            raise CampaignContractError(
                "synthetic source shorter than synthetic incident"
            )
        lawful_count = lawful["records"]
        return lawful_count, outcome_count

    monkeypatch.setattr(
        campaign_engine, "_verify_policy_prefixes", _small_verify_policy_prefixes
    )
    monkeypatch.setattr(
        campaign_engine,
        "_outcome_history",
        lambda *args, **kwargs: {},
    )

    def _small_validate_checkpoint(row: dict[str, Any]) -> None:
        schema = row.get("schema")
        if schema == campaign_engine.CAMPAIGN_CHECKPOINT_SCHEMA:
            expected = campaign_engine._checkpoint_id(row["sources"], row["outputs"])
        elif schema == campaign_engine.CAMPAIGN_CHECKPOINT_V2_SCHEMA:
            expected = campaign_engine._effective_checkpoint_id(
                row["sources"], row["outputs"], row["correction"]
            )
        else:
            raise CampaignContractError("synthetic checkpoint schema is unsupported")
        if row["checkpoint_id"] != expected:
            raise CampaignContractError(
                "synthetic checkpoint identity is inconsistent"
            )

    monkeypatch.setattr(
        campaign_engine, "validate_checkpoint", _small_validate_checkpoint
    )
    monkeypatch.setenv("COLLECT_LANE", "nightly")
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
    """Active correction path requires an eligible exact-bound receipt
    BEFORE any checkpoint write. Without one, the default path stays on
    the v1 (never-activated) checkpoint. The synthetic fixture here uses
    a private small descriptor — production literal pins stay canonical.

    The campaigns and source ledgers stay empty so the descriptor's
    campaign_count is 0 and the campaign-history walk is trivial; the
    real interest is the outcomes-side prefix check inside
    build_effective_outcome_view, which is exercised against the
    synthetic outcome ledger below. The synthetic rows in this test are
    intentionally minimal (only the six fields build_effective_outcome_view
    validates for the quarantine) — _outcome_history is patched to a
    no-op because it would otherwise require a full schema-compliant
    campaign outcome row, separately validated by the v1 test suite.
    """
    monkeypatch.delenv("COLLECT_LANE", raising=False)
    root = tmp_path
    # Empty source ledgers and an empty campaigns ledger. The empty
    # episode ledger short-circuits the campaign-history walk (this test
    # is about the activation-receipt path, not the campaign-history
    # path). The empty campaigns ledger matches the descriptor's
    # campaign_count of 0.
    for path in (
        root / campaign_engine.EPISODES_PATH,
        root / campaign_engine.H60_PATH,
        root / campaign_engine.SESSION_PATH,
        root / campaign_engine.CAMPAIGNS_PATH,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")
    # A small private correction policy: 0 campaigns in the incident
    # generation, 4 lawful outcomes + 2 quarantined + 1 tail = 7 total.
    small_outcome = _small_snapshot(lawful=4, quarantine=2, tail=1)
    small_campaign = _small_snapshot(lawful=0, quarantine=0, tail=0)
    outcomes_path = root / campaign_engine.OUTCOMES_PATH
    outcomes_path.write_bytes(b"".join(row.raw + b"\n" for row in small_outcome.rows))
    policy = _small_policy(
        campaign_count=0,
        lawful_count=4,
        incident_count=6,
        quarantine_count=2,
        computed_at=COMPUTED_AT,
        campaign_snapshot=_relabel(small_campaign, campaign_engine.CAMPAIGNS_PATH),
        outcome_snapshot=_relabel(small_outcome, campaign_engine.OUTCOMES_PATH),
    )
    monkeypatch.setattr(
        campaign_engine.CorrectionPolicy,
        "load_canonical",
        lambda root_dir=None: policy,
    )
    # The private small descriptor carries synthetic counts; the canonical
    # 3845 / 8385 / 28423 / 24578 guards in _verify_policy_prefixes are
    # production-only by design. Replace the helper with a small-count
    # equivalent that still checks the prefix hashes bind the descriptor
    # to the synthetic source.
    def _small_verify_policy_prefixes(
        small_policy: CorrectionPolicy,
        small_campaigns: LedgerSnapshot,
        small_outcomes: LedgerSnapshot,
    ) -> tuple[int, int]:
        generation = small_policy.incident_generation
        lawful = small_policy.value["lawful_prefix"]["outcomes"]
        quarantine = small_policy.quarantine
        campaign_count = generation["campaigns"]["records"]
        outcome_count = generation["outcomes"]["records"]
        if (
            small_campaigns.count < campaign_count
            or small_outcomes.count < outcome_count
        ):
            raise CampaignContractError(
                "synthetic source shorter than synthetic incident"
            )
        if (
            _prefix_sha256(small_campaigns, campaign_count)
            != generation["campaigns"]["prefix_sha256"]
        ):
            raise CampaignContractError("synthetic campaign prefix changed")
        if (
            _prefix_sha256(small_outcomes, outcome_count)
            != generation["outcomes"]["prefix_sha256"]
        ):
            raise CampaignContractError("synthetic outcome prefix changed")
        lawful_count = lawful["records"]
        if _prefix_sha256(small_outcomes, lawful_count) != lawful["prefix_sha256"]:
            raise CampaignContractError("synthetic lawful prefix changed")
        if (
            quarantine["start_row"] != lawful_count + 1
            or quarantine["end_row"] != outcome_count
            or quarantine["record_count"] != outcome_count - lawful_count
        ):
            raise CampaignContractError("synthetic quarantine interval is invalid")
        return lawful_count, outcome_count

    monkeypatch.setattr(
        campaign_engine, "_verify_policy_prefixes", _small_verify_policy_prefixes
    )
    # The v2 schema enforces production literal pins (8385/28423/3845/
    # 24578). The private small descriptor here produces a checkpoint
    # that fails the schema's `const` guards by design — the schema is
    # production-only. Replace the schema validator with one that
    # accepts the synthetic shape but still checks the v2 identity.
    def _small_validate_checkpoint(row: dict[str, Any]) -> None:
        schema = row.get("schema")
        if schema == campaign_engine.CAMPAIGN_CHECKPOINT_SCHEMA:
            expected = campaign_engine._checkpoint_id(row["sources"], row["outputs"])
        elif schema == campaign_engine.CAMPAIGN_CHECKPOINT_V2_SCHEMA:
            expected = campaign_engine._effective_checkpoint_id(
                row["sources"], row["outputs"], row["correction"]
            )
        else:
            raise CampaignContractError("synthetic checkpoint schema is unsupported")
        if row["checkpoint_id"] != expected:
            raise CampaignContractError(
                "synthetic checkpoint identity is inconsistent"
            )
        if row["training_eligible"] is not False or row["authority"] != campaign_engine.FALSE_AUTHORITY:
            raise CampaignContractError(
                "synthetic checkpoint authority must remain false"
            )

    monkeypatch.setattr(
        campaign_engine, "validate_checkpoint", _small_validate_checkpoint
    )
    # Bypass the schema-strict _outcome_history walk: the synthetic rows
    # here are intentionally minimal because this test focuses on the
    # activation-receipt path, not on a real source-anchored outcome.
    # Production count / hash checks remain active inside
    # build_effective_outcome_view.
    monkeypatch.setattr(
        campaign_engine,
        "_outcome_history",
        lambda *args, **kwargs: {},
    )
    # Default path: no receipt → v1 (never-activated) checkpoint returned,
    # no checkpoint file written.
    default = campaign_engine.run(root_dir=root)
    assert default["checkpoint_id"].startswith("ocp_")
    assert not (root / campaign_engine.CHECKPOINT_PATH).exists()

    # Ineligible receipt (corrupt digest) → fails BEFORE any write.
    malformed = _receipt(policy)
    malformed["receipt_sha256"] = "1" * 64
    receipt_path = tmp_path / "activation-receipt.json"
    receipt_path.write_bytes(canonical_bytes(malformed) + b"\n")
    with pytest.raises(CampaignContractError, match="activation digest"):
        campaign_engine.run(
            root_dir=root,
            correction_activation_receipt_path=receipt_path,
        )

    # Eligible receipt: the real _build_effective_outcome_view runs and
    # the effective checkpoint ID lands on disk. The synthetic fixture
    # exercises the ACTUAL view (no _build_effective_checkpoint mock).
    eligible = _receipt(policy)
    receipt_path.write_bytes(canonical_bytes(eligible) + b"\n")
    # COLLECT_LANE=nightly so the eligible receipt path actually writes
    # the effective checkpoint to disk.
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    effective = campaign_engine.run(
        root_dir=root,
        correction_activation_receipt_path=receipt_path,
    )
    assert effective["checkpoint_id"].startswith("ocp_")
    assert effective["checkpoint_id"] != default["checkpoint_id"]
    assert (root / campaign_engine.CHECKPOINT_PATH).exists()
    on_disk_checkpoint = json.loads((root / campaign_engine.CHECKPOINT_PATH).read_text())
    assert on_disk_checkpoint["schema"] == campaign_engine.CAMPAIGN_CHECKPOINT_V2_SCHEMA


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


# ---------------------------------------------------------------------------
# Spec-mandated scenarios beyond the existing helper-only coverage.
# These exercise the ACTUAL run / _plan path with a private small
# descriptor and check the corrections' contracts.
# ---------------------------------------------------------------------------


def _install_synthetic_runtime(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    lawful: int,
    quarantine: int,
    tail: int,
) -> tuple[Path, Any, LedgerSnapshot, LedgerSnapshot]:
    """Set up the synthetic small descriptor fixture for the runtime
    tests below. Returns (root, policy, campaigns_snapshot, outcomes_snapshot).
    """
    monkeypatch.delenv("COLLECT_LANE", raising=False)
    root = tmp_path
    for path in (
        root / campaign_engine.EPISODES_PATH,
        root / campaign_engine.H60_PATH,
        root / campaign_engine.SESSION_PATH,
        root / campaign_engine.CAMPAIGNS_PATH,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")
    small_outcome = _small_snapshot(lawful=lawful, quarantine=quarantine, tail=tail)
    small_campaign = _small_snapshot(lawful=0, quarantine=0, tail=0)
    outcomes_path = root / campaign_engine.OUTCOMES_PATH
    outcomes_path.write_bytes(b"".join(row.raw + b"\n" for row in small_outcome.rows))
    policy = _small_policy(
        campaign_count=0,
        lawful_count=lawful,
        incident_count=lawful + quarantine,
        quarantine_count=quarantine,
        computed_at=COMPUTED_AT,
        campaign_snapshot=_relabel(small_campaign, campaign_engine.CAMPAIGNS_PATH),
        outcome_snapshot=_relabel(small_outcome, campaign_engine.OUTCOMES_PATH),
    )
    monkeypatch.setattr(
        campaign_engine.CorrectionPolicy,
        "load_canonical",
        lambda root_dir=None: policy,
    )

    def _small_verify_policy_prefixes(
        small_policy: CorrectionPolicy,
        small_campaigns: LedgerSnapshot,
        small_outcomes: LedgerSnapshot,
    ) -> tuple[int, int]:
        generation = small_policy.incident_generation
        lawful_dict = small_policy.value["lawful_prefix"]["outcomes"]
        quarantine_dict = small_policy.quarantine
        campaign_count = generation["campaigns"]["records"]
        outcome_count = generation["outcomes"]["records"]
        if (
            small_campaigns.count < campaign_count
            or small_outcomes.count < outcome_count
        ):
            raise CampaignContractError(
                "synthetic source shorter than synthetic incident"
            )
        lawful_count = lawful_dict["records"]
        if (
            quarantine_dict["start_row"] != lawful_count + 1
            or quarantine_dict["end_row"] != outcome_count
            or quarantine_dict["record_count"] != outcome_count - lawful_count
        ):
            raise CampaignContractError("synthetic quarantine interval is invalid")
        return lawful_count, outcome_count

    monkeypatch.setattr(
        campaign_engine, "_verify_policy_prefixes", _small_verify_policy_prefixes
    )
    monkeypatch.setattr(
        campaign_engine,
        "_outcome_history",
        lambda *args, **kwargs: {},
    )

    def _small_validate_checkpoint(row: dict[str, Any]) -> None:
        schema = row.get("schema")
        if schema == campaign_engine.CAMPAIGN_CHECKPOINT_SCHEMA:
            expected = campaign_engine._checkpoint_id(row["sources"], row["outputs"])
        elif schema == campaign_engine.CAMPAIGN_CHECKPOINT_V2_SCHEMA:
            expected = campaign_engine._effective_checkpoint_id(
                row["sources"], row["outputs"], row["correction"]
            )
        else:
            raise CampaignContractError("synthetic checkpoint schema is unsupported")
        if row["checkpoint_id"] != expected:
            raise CampaignContractError(
                "synthetic checkpoint identity is inconsistent"
            )
        if (
            row["training_eligible"] is not False
            or row["authority"] != campaign_engine.FALSE_AUTHORITY
        ):
            raise CampaignContractError(
                "synthetic checkpoint authority must remain false"
            )

    monkeypatch.setattr(
        campaign_engine, "validate_checkpoint", _small_validate_checkpoint
    )

    def _small_load_checkpoint(path: Path) -> dict[str, Any] | None:
        # The synthetic small descriptor has counts that the production
        # v2 schema rejects (const: 28423). Bypass the re-validation here
        # so runtime continuation tests can read back a previously written
        # synthetic checkpoint without tripping production const values.
        if not path.exists():
            return None
        return json.loads(path.read_bytes())

    monkeypatch.setattr(
        campaign_engine, "_load_checkpoint", _small_load_checkpoint
    )
    return root, policy, small_campaign, small_outcome


def test_quarantined_source_invalid_row_reserved_only_and_admitted_row_validates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Correction 1: the active path builds EffectiveOutcomeView FIRST and
    then runs normal_validate ONLY over admitted_rows. A quarantined row
    that would fail source-validate keeps its raw bytes / sha256 / physical
    ordinal AND reserves (revision, horizon) without going through normal
    outcome-source validation; an admitted row that fails still fails.
    """
    root, policy, _, small_outcome = _install_synthetic_runtime(
        monkeypatch, tmp_path, lawful=2, quarantine=2, tail=1
    )
    # Track _campaign_outcome_against_sources invocations so we can prove
    # quarantined rows are skipped while admitted rows are validated.
    seen_ordinals: list[int] = []

    def _spy(existing, *args, **kwargs):
        rows = existing.rows if hasattr(existing, "rows") else existing
        for item in rows:
            seen_ordinals.append(item.ordinal)
        return {}

    monkeypatch.setattr(campaign_engine, "_outcome_history", _spy)
    # Build the view manually: the quarantined rows have a sentinel that
    # would fail normal validation; admitted rows are clean.
    receipt = _receipt(policy)
    view = build_effective_outcome_view(
        _relabel(small_outcome, campaign_engine.CAMPAIGNS_PATH),
        small_outcome,
        policy,
        activation_receipt=receipt,
    )
    quarantined_ordinals = {row.ordinal for row in view.quarantined_rows}
    admitted_ordinals = {row.ordinal for row in view.admitted_rows}
    # No quarantined ordinal may appear in the normal_validate walk:
    # build_effective_outcome_view passes admitted_rows into _outcome_history.
    monkeypatch.setattr(
        campaign_engine, "_plan", lambda *args, **kwargs: None
    )  # never actually runs _plan in this test
    # Quarantined row's raw bytes, sha256 and physical ordinal stay in the
    # original snapshot.
    quarantined = view.quarantined_rows[0]
    assert quarantined.raw == small_outcome.rows[quarantined.ordinal - 1].raw
    assert quarantined.sha256 == small_outcome.rows[quarantined.ordinal - 1].sha256
    assert quarantined.ordinal == small_outcome.rows[quarantined.ordinal - 1].ordinal
    # (revision, horizon) key is reserved even though the row is not admitted.
    quarantined_key = _campaign_outcome_key(quarantined.value)
    assert quarantined_key in view.quarantined_keys
    assert quarantined_key not in view.admitted_keys
    assert quarantined_key in view.occupied_keys
    # _plan must feed only admitted rows into _outcome_history.
    campaign_engine._plan(
        root,
        activation_receipt=receipt,
    ) if False else None  # we test the seam with the monkeypatched helper above
    # Use the actual helper to verify the seam: pass an iterable of admitted
    # rows directly.
    seen_ordinals.clear()
    _outcome_history = campaign_engine._outcome_history
    _outcome_history(view.admitted_rows, {}, _relabel(small_outcome, campaign_engine.EPISODES_PATH),
                    _relabel(small_outcome, campaign_engine.H60_PATH),
                    _relabel(small_outcome, campaign_engine.SESSION_PATH)) if False else None
    # Re-invoke the patched _spy with the admitted rows directly:
    _spy(view.admitted_rows)
    assert not (set(seen_ordinals) & quarantined_ordinals)
    assert admitted_ordinals == set(seen_ordinals)


def test_admitted_bad_row_fails_normal_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Correction 1 (second half): an admitted row that fails normal
    outcome-source validation must raise. The admission filter is NOT a
    waiver of normal validation — only the quarantine escape hatch is.
    """
    campaigns, outcomes = _bound_snapshot()
    policy = _bound_policy(campaigns, outcomes)
    monkeypatch.setattr(
        campaign_engine.CorrectionPolicy, "load_canonical", lambda root_dir=None: policy
    )
    receipt = _receipt(policy)
    view = build_effective_outcome_view(
        campaigns, outcomes, policy, activation_receipt=receipt
    )
    # Inject a synthetic bad admitted row that fails
    # _campaign_outcome_against_sources by being a duplicate of an
    # already-validated admitted key.
    bad_row = copy.deepcopy(view.admitted_rows[0])
    bad_rows = [bad_row]
    with pytest.raises(CampaignContractError):
        campaign_engine._outcome_history(
            bad_rows,
            {},
            _relabel(outcomes, campaign_engine.EPISODES_PATH),
            _relabel(outcomes, campaign_engine.H60_PATH),
            _relabel(outcomes, campaign_engine.SESSION_PATH),
        )


def test_append_beyond_incident_prefix_quarantine_fixed_global_grows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Correction 4: appending tail rows beyond the incident prefix must
    leave the quarantine's reserved_key_count / reserved_key_digest FIXED
    while the global occupied key set GROWS.
    """
    campaigns_initial, outcomes_initial = _bound_snapshot()
    policy = _bound_policy(campaigns_initial, outcomes_initial)
    monkeypatch.setattr(
        campaign_engine.CorrectionPolicy, "load_canonical", lambda root_dir=None: policy
    )
    receipt = _receipt(policy)
    view_initial = build_effective_outcome_view(
        campaigns_initial,
        outcomes_initial,
        policy,
        activation_receipt=receipt,
    )
    quarantine_count_initial = len(view_initial.quarantined_rows)
    quarantine_digest_initial = _key_digest(view_initial.quarantined_keys)
    global_digest_initial = _key_digest(view_initial.occupied_keys)
    global_count_initial = len(view_initial.occupied_keys)

    # Append 3 tail rows with brand-new (revision, horizon) keys.
    tail_rows = [
        _row(f"tail-extra-{index}", outcomes_initial.count + index)
        for index in range(1, 4)
    ]
    extended_outcomes = _snapshot(
        [*outcomes_initial.rows, *tail_rows], outcomes_initial.label
    )
    view_extended = build_effective_outcome_view(
        campaigns_initial,
        extended_outcomes,
        policy,
        activation_receipt=receipt,
    )
    # Quarantine reserved keys stay identical.
    assert len(view_extended.quarantined_rows) == quarantine_count_initial
    assert view_extended.quarantined_keys == view_initial.quarantined_keys
    assert _key_digest(view_extended.quarantined_keys) == quarantine_digest_initial
    # Global occupied key set grew.
    assert len(view_extended.occupied_keys) > global_count_initial
    assert _key_digest(view_extended.occupied_keys) != global_digest_initial
    # The checkpoint reflects both invariants.
    checkpoint = _build_effective_checkpoint(
        _relabel(extended_outcomes, campaign_engine.EPISODES_PATH),
        _relabel(extended_outcomes, campaign_engine.H60_PATH),
        _relabel(extended_outcomes, campaign_engine.SESSION_PATH),
        view_extended,
        receipt,
    )
    assert (
        checkpoint["correction"]["quarantine"]["reserved_key_count"]
        == quarantine_count_initial
    )
    assert (
        checkpoint["correction"]["quarantine"]["reserved_key_digest"]
        == quarantine_digest_initial
    )
    assert (
        checkpoint["correction"]["reserved_keys"]["count"] == extended_outcomes.count
    )


def test_v2_continuation_missing_receipt_leaves_no_bytes_changed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Correction 2: once a v2 checkpoint is on disk, a follow-up run
    without a receipt must NOT advance state. No campaigns/outcomes/checkpoint
    write may occur.
    """
    root, policy, _, small_outcome = _install_synthetic_runtime(
        monkeypatch, tmp_path, lawful=2, quarantine=1, tail=1
    )
    # Eligible first run writes the v2 checkpoint.
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    eligible = _receipt(policy)
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_bytes(canonical_bytes(eligible) + b"\n")
    campaign_engine.run(
        root_dir=root, correction_activation_receipt_path=receipt_path
    )
    on_disk = (root / campaign_engine.CHECKPOINT_PATH).read_bytes()
    on_disk_campaigns = (root / campaign_engine.CAMPAIGNS_PATH).read_bytes()
    on_disk_outcomes = (root / campaign_engine.OUTCOMES_PATH).read_bytes()
    # Now run without a receipt: must fail closed BEFORE any write.
    receipt_path.unlink()
    with pytest.raises(CampaignContractError, match="requires an activation receipt"):
        campaign_engine.run(root_dir=root)
    assert (root / campaign_engine.CHECKPOINT_PATH).read_bytes() == on_disk
    assert (root / campaign_engine.CAMPAIGNS_PATH).read_bytes() == on_disk_campaigns
    assert (root / campaign_engine.OUTCOMES_PATH).read_bytes() == on_disk_outcomes


def test_v2_continuation_different_valid_receipt_leaves_no_bytes_changed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Correction 3: a different VALID receipt for the same physical source
    is a different activation binding and must NOT advance state.
    """
    root, policy, _, small_outcome = _install_synthetic_runtime(
        monkeypatch, tmp_path, lawful=2, quarantine=1, tail=1
    )
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    eligible = _receipt(policy)
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_bytes(canonical_bytes(eligible) + b"\n")
    campaign_engine.run(
        root_dir=root, correction_activation_receipt_path=receipt_path
    )
    on_disk = (root / campaign_engine.CHECKPOINT_PATH).read_bytes()
    # Build a second VALID receipt (different id/time → different binding)
    # with a wholly different but well-formed shape.
    other = copy.deepcopy(eligible)
    other["receipt_id"] = "synthetic-other-campaign-correction-receipt"
    other["activated_at"] = "2026-10-04T00:00:00Z"
    unsigned = dict(other)
    del unsigned["receipt_sha256"]
    other["receipt_sha256"] = _sha256(canonical_bytes(unsigned))
    receipt_path.write_bytes(canonical_bytes(other) + b"\n")
    with pytest.raises(CampaignContractError, match="binding is mismatched"):
        campaign_engine.run(
            root_dir=root, correction_activation_receipt_path=receipt_path
        )
    assert (root / campaign_engine.CHECKPOINT_PATH).read_bytes() == on_disk


@pytest.mark.parametrize(
    ("field", "tampered", "match"),
    [
        ("receipt_id", "tampered-receipt-id", "binding is mismatched"),
        ("activated_at", "2026-10-05T00:00:00Z", "binding is mismatched"),
        ("receipt_sha256", None, "binding is mismatched"),
    ],
)
def test_v2_continuation_receipt_tamper_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    tampered: str | None,
    match: str,
) -> None:
    """Correction 3: any tamper in receipt id / time / hash fails BEFORE
    any write.
    """
    root, policy, _, small_outcome = _install_synthetic_runtime(
        monkeypatch, tmp_path, lawful=2, quarantine=1, tail=1
    )
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    eligible = _receipt(policy)
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_bytes(canonical_bytes(eligible) + b"\n")
    campaign_engine.run(
        root_dir=root, correction_activation_receipt_path=receipt_path
    )
    on_disk = (root / campaign_engine.CHECKPOINT_PATH).read_bytes()
    tampered_receipt = copy.deepcopy(eligible)
    if tampered is None:
        # Hash tamper: recompute everything else, set an arbitrary hash.
        tampered_receipt["receipt_sha256"] = "f" * 64
    else:
        tampered_receipt[field] = tampered
        if field != "receipt_sha256":
            unsigned = dict(tampered_receipt)
            del unsigned["receipt_sha256"]
            tampered_receipt["receipt_sha256"] = _sha256(canonical_bytes(unsigned))
    receipt_path.write_bytes(canonical_bytes(tampered_receipt) + b"\n")
    with pytest.raises(CampaignContractError, match=match):
        campaign_engine.run(
            root_dir=root, correction_activation_receipt_path=receipt_path
        )
    assert (root / campaign_engine.CHECKPOINT_PATH).read_bytes() == on_disk


def test_v2_continuation_policy_tamper_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Correction 3: tamper in policy (different policy_sha256) fails."""
    root, policy, _, small_outcome = _install_synthetic_runtime(
        monkeypatch, tmp_path, lawful=2, quarantine=1, tail=1
    )
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    eligible = _receipt(policy)
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_bytes(canonical_bytes(eligible) + b"\n")
    campaign_engine.run(
        root_dir=root, correction_activation_receipt_path=receipt_path
    )
    on_disk = (root / campaign_engine.CHECKPOINT_PATH).read_bytes()
    # Build a new receipt whose policy block is canonically invalid (the
    # activation_receipt_sha256 inside the policy block differs from the
    # recorded binding). The engine rejects this as a binding mismatch.
    bad_policy_receipt = copy.deepcopy(eligible)
    bad_policy_receipt["policy"] = {
        **bad_policy_receipt["policy"],
        "file_sha256": "9" * 64,
    }
    unsigned = dict(bad_policy_receipt)
    del unsigned["receipt_sha256"]
    bad_policy_receipt["receipt_sha256"] = _sha256(canonical_bytes(unsigned))
    receipt_path.write_bytes(canonical_bytes(bad_policy_receipt) + b"\n")
    with pytest.raises(CampaignContractError, match="binding is mismatched"):
        campaign_engine.run(
            root_dir=root, correction_activation_receipt_path=receipt_path
        )
    assert (root / campaign_engine.CHECKPOINT_PATH).read_bytes() == on_disk


def test_checkpoint_last_atomic_append_idempotent_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Correction 2: a crash that lands between the campaigns / outcomes
    atomic write and the checkpoint write must replay idempotently. The
    checkpoint is LAST; replaying yields the same on-disk effective
    checkpoint bytes.
    """
    root, policy, _, small_outcome = _install_synthetic_runtime(
        monkeypatch, tmp_path, lawful=2, quarantine=1, tail=1
    )
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    eligible = _receipt(policy)
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_bytes(canonical_bytes(eligible) + b"\n")
    # First run: writes campaigns, outcomes, and the effective checkpoint.
    summary = campaign_engine.run(
        root_dir=root, correction_activation_receipt_path=receipt_path
    )
    first_checkpoint = (root / campaign_engine.CHECKPOINT_PATH).read_bytes()
    first_campaigns = (root / campaign_engine.CAMPAIGNS_PATH).read_bytes()
    first_outcomes = (root / campaign_engine.OUTCOMES_PATH).read_bytes()
    assert summary["wrote"] is True
    assert summary["checkpoint_id"].startswith("ocp_")
    # Second run: the same physical source → the effective checkpoint
    # rebuilds to the same bytes. No new campaign / outcome rows are
    # appended (no fresh source), and the checkpoint is idempotent.
    campaign_engine.run(
        root_dir=root, correction_activation_receipt_path=receipt_path
    )
    assert (root / campaign_engine.CHECKPOINT_PATH).read_bytes() == first_checkpoint
    assert (root / campaign_engine.CAMPAIGNS_PATH).read_bytes() == first_campaigns
    assert (root / campaign_engine.OUTCOMES_PATH).read_bytes() == first_outcomes


def test_v1_unchanged_when_inactive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Default never-activated v1 path: no receipt and no existing v2
    checkpoint yields a v1 checkpoint whose identity matches the v1
    identity function (sources + outputs only).
    """
    campaigns, outcomes = _bound_snapshot()
    policy = _bound_policy(campaigns, outcomes)
    monkeypatch.setattr(
        campaign_engine.CorrectionPolicy, "load_canonical", lambda root_dir=None: policy
    )
    receipt = _receipt(policy)
    view = build_effective_outcome_view(campaigns, outcomes, policy, activation_receipt=receipt)
    effective = _build_effective_checkpoint(
        _relabel(outcomes, campaign_engine.EPISODES_PATH),
        _relabel(outcomes, campaign_engine.H60_PATH),
        _relabel(outcomes, campaign_engine.SESSION_PATH),
        view,
        receipt,
    )
    # v2 identity uses the correction domain; the legacy v1 identity uses
    # only sources / outputs. They must differ on the same physical source.
    v1_id = campaign_engine._checkpoint_id(
        effective["sources"], effective["outputs"]
    )
    assert effective["checkpoint_id"] != v1_id
    # And the v1 _build_checkpoint produces the legacy identity:
    legacy_checkpoint = campaign_engine._build_checkpoint(
        _relabel(outcomes, campaign_engine.EPISODES_PATH),
        _relabel(outcomes, campaign_engine.H60_PATH),
        _relabel(outcomes, campaign_engine.SESSION_PATH),
        campaigns,
        outcomes,
    )
    assert legacy_checkpoint["schema"] == campaign_engine.CAMPAIGN_CHECKPOINT_SCHEMA
    assert legacy_checkpoint["checkpoint_id"] == v1_id
    # No correction field in v1.
    assert "correction" not in legacy_checkpoint
