"""Synthetic source composition only; no natural lifecycle/source admission."""
from __future__ import annotations

import copy
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256

import pytest

from engine import options_signal_campaign as campaigns
from engine import options_alpha_expression_outcome as expressions
from engine import options_alpha_expression_publication as publication
from engine import options_nbbo_cohort as cohort
import test_options_alpha_exact_option_outcome as ruler_tests
import test_publish_options_alpha_candidate_r2 as publisher_tests


class SessionS3(publisher_tests.MetadataS3):
    def _time(self):
        return datetime(2026, 8, 14, 14, tzinfo=timezone.utc) + timedelta(seconds=self.n)


def _fixture(tmp_path, monkeypatch):
    root = tmp_path / 'source'
    feeds = publisher_tests._feeds(root, monkeypatch)
    intent = publisher_tests._expression_intent(feeds, root)
    provider = SessionS3()
    publisher_tests._publish_expression(provider, tmp_path, feeds[0], [intent])
    pair = publisher_tests._read_expression(provider, tmp_path)
    availability = publication.resolve_intent_availability(pair, intent['expression_id'])
    assert availability['status'] == 'available'
    available = datetime.fromisoformat(availability['available_at'].replace('Z', '+00:00'))
    contract = intent['contract']
    receipt = ruler_tests._expression_receipt(
        **contract, expression_id=intent['expression_id'],
        source_candidate_id=intent['candidate_id'],
        decision_receipt_sha256=sha256(cohort.canonical_json_bytes(intent)).hexdigest(),
        source_rule_digest_sha256=intent['selection_policy_sha256'],
        decision_at=intent['decision_at'], available_at=availability['available_at'],
        selection_fence_at=intent['decision_at'],
        multiplier=intent['terms_observation']['multiplier'],
        standard_deliverable=intent['terms_observation']['standard_deliverable'])
    entry_at = available + timedelta(seconds=1)
    exit_at = entry_at + timedelta(minutes=60)
    evidence = []
    for role, boundary, event in (
        (ruler_tests.oa3.ROLE_ENTRY, available, entry_at),
        (ruler_tests.oa3.ROLE_EXIT, exit_at, exit_at)):
        request = boundary + timedelta(seconds=61)
        row = ruler_tests._row_at(
            event, symbol=contract['root'], expiration=contract['expiration'],
            strike=float(contract['strike']), bid='2.00', ask='2.10')
        row['right'] = contract['right']
        evidence.append(ruler_tests._evidence(
            role=role, contract=contract, boundary_at=boundary,
            request_started_at=request, response_observed_at=request + timedelta(seconds=1),
            retrieval_observed_at=request + timedelta(seconds=2),
            computed_at=request + timedelta(seconds=3), rows=[row]))
    wrapped = expressions.ExpressionOutcomeEvidence(
        publication_pair=pair, expression=receipt, entry=evidence[0], exit=evidence[1],
        observed_at='2026-08-14T17:00:00Z')
    return root, intent, wrapped, provider


def _bytes(root):
    return {path: (root / path).read_bytes() for path in (
        campaigns.CAMPAIGNS_PATH, campaigns.OUTCOMES_PATH, campaigns.CHECKPOINT_PATH)}


def test_native_append_v3_noop_and_legacy_option_blocks_unchanged(tmp_path, monkeypatch):
    root, intent, evidence, provider = _fixture(tmp_path, monkeypatch)
    before = _bytes(root)
    provider_writes = len(provider.puts)
    summary = campaigns.run(root_dir=root, expression_evidence=[evidence])
    assert summary['expression_outcomes_appended'] == 1
    rows = campaigns.load_ledger(root / campaigns.OUTCOMES_PATH, campaigns.OUTCOMES_PATH)
    expression = rows.rows[-1].value
    assert expression['schema'] == campaigns.EXPRESSION_OUTCOME_SCHEMA
    assert expression['expression_id'] == intent['expression_id']
    assert expression['evaluation']['status'] == 'complete'
    assert expression['training_eligible'] is False
    assert all(value is False for value in expression['authority'].values())
    assert (root / campaigns.OUTCOMES_PATH).read_bytes().startswith(before[campaigns.OUTCOMES_PATH])
    checkpoint = json.loads((root / campaigns.CHECKPOINT_PATH).read_bytes())
    assert checkpoint['schema'] == campaigns.CAMPAIGN_CHECKPOINT_V3_SCHEMA
    assert checkpoint['correction'] is None
    assert checkpoint['populations']['expression_rows'] == 1
    campaigns.validate_checkpoint(checkpoint)
    after = _bytes(root)
    replay = campaigns.run(root_dir=root, expression_evidence=[evidence])
    assert replay['expression_outcomes_appended'] == 0
    assert _bytes(root) == after
    assert len(provider.puts) == provider_writes


@pytest.mark.parametrize('prior_expression', [False, True])
def test_checkpoint_last_interruption_retains_exact_physical_append(tmp_path, monkeypatch, prior_expression):
    root, intent, evidence, _ = _fixture(tmp_path, monkeypatch)
    if prior_expression:
        campaigns.run(root_dir=root, expression_evidence=[evidence])
        # A genuinely distinct versioned intent, never a changed existing key.
        feeds = publisher_tests._feeds(tmp_path / 'second-source', monkeypatch)
        second = publisher_tests._expression_intent(feeds, tmp_path / 'second-source',
                                                   decision='2026-08-13T14:32:02Z')
        # The second expression has the same campaign but its own frozen decision.
        provider = SessionS3()
        publisher_tests._publish_expression(provider, tmp_path / 'second', feeds[0], [second])
        pair = publisher_tests._read_expression(provider, tmp_path / 'second')
        payload = dict(evidence.expression.parsed_payload)
        payload.update(expression_id=second['expression_id'], decision_at=second['decision_at'],
                       selection_fence_at=second['decision_at'],
                       decision_receipt_sha256=sha256(cohort.canonical_json_bytes(second)).hexdigest())
        evidence = replace(evidence, publication_pair=pair,
                           expression=ruler_tests._expression_receipt(**payload))
    checkpoint_before = (root / campaigns.CHECKPOINT_PATH).read_bytes()
    def interrupted():
        raise RuntimeError('checkpoint-last interruption')
    with pytest.raises(RuntimeError, match='checkpoint-last interruption'):
        campaigns.run(root_dir=root, expression_evidence=[evidence], before_checkpoint=interrupted)
    assert (root / campaigns.CHECKPOINT_PATH).read_bytes() == checkpoint_before
    physical = (root / campaigns.OUTCOMES_PATH).read_bytes()
    result = campaigns.run(root_dir=root, expression_evidence=[evidence])
    assert result['expression_outcomes_appended'] == 0
    assert (root / campaigns.OUTCOMES_PATH).read_bytes() == physical
    final = _bytes(root)
    campaigns.run(root_dir=root, expression_evidence=[evidence])
    assert _bytes(root) == final


def test_dry_run_and_invalid_inputs_never_append(tmp_path, monkeypatch):
    root, _, evidence, _ = _fixture(tmp_path, monkeypatch)
    original = _bytes(root)
    planned = campaigns.run(root_dir=root, dry_run=True, expression_evidence=[evidence])
    assert planned['wrote'] is False and _bytes(root) == original
    monkeypatch.setenv('COLLECT_LANE', 'intraday')
    assert campaigns.run(root_dir=root, expression_evidence=[evidence])['wrote'] is False
    assert _bytes(root) == original
    monkeypatch.setenv('COLLECT_LANE', 'nightly')
    for value in (object(), replace(evidence, observed_at='2026-08-13T00:00:00Z'),
                  replace(evidence, publication_pair=None)):
        with pytest.raises(campaigns.CampaignContractError):
            campaigns.run(root_dir=root, expression_evidence=[value])
        assert _bytes(root) == original
    with pytest.raises(campaigns.CampaignContractError, match='occupied'):
        campaigns.run(root_dir=root, expression_evidence=[evidence, evidence])
    assert _bytes(root) == original


def test_existing_expression_is_immutable_and_namespace_does_not_alias_underlying(tmp_path, monkeypatch):
    root, _, evidence, _ = _fixture(tmp_path, monkeypatch)
    campaigns.run(root_dir=root, expression_evidence=[evidence])
    original = _bytes(root)
    with pytest.raises(campaigns.CampaignContractError, match='immutable'):
        campaigns.run(root_dir=root, expression_evidence=[replace(evidence, observed_at='2026-08-14T18:00:00Z')])
    assert _bytes(root) == original
    expression = campaigns.load_ledger(root / campaigns.OUTCOMES_PATH, campaigns.OUTCOMES_PATH).rows[-1].value
    key = campaigns._campaign_outcome_key(expression)
    assert len(key) == 4 and key[0] == 'exact_option_expression'
    assert key != (expression['campaign_revision_id'], 'h60')


def _corrected_runtime(root, evidence, monkeypatch, tmp_path):
    """Private synthetic policy; real native prefix and receipt validation."""
    import test_options_signal_campaign_effective_view as correction_tests
    original = campaigns.load_ledger(root / campaigns.OUTCOMES_PATH, campaigns.OUTCOMES_PATH)
    assert original.count == 0
    source = campaigns.load_ledger(root / campaigns.CAMPAIGNS_PATH, campaigns.CAMPAIGNS_PATH)
    rows = [correction_tests._row(f'quarantined-{n}', n + 1,
                                  computed_at=correction_tests.COMPUTED_AT).value
            for n in range(3845)]
    candidate_id = evidence.expression.parsed_payload['source_candidate_id']
    candidate = next(value for value in evidence.publication_pair.feed['formed_candidates']
                     if value['candidate_id'] == candidate_id)
    rows[0]['campaign_revision_id'] = candidate['frozen_formation']['campaign_revision_id']
    physical = b''.join(campaigns.canonical_bytes(row) + b'\n' for row in rows)
    (root / campaigns.OUTCOMES_PATH).write_bytes(physical)
    outcomes = campaigns.load_ledger(root / campaigns.OUTCOMES_PATH, campaigns.OUTCOMES_PATH)
    policy = correction_tests._small_policy(
        campaign_count=source.count, lawful_count=0, incident_count=3845,
        quarantine_count=3845, computed_at=correction_tests.COMPUTED_AT,
        campaign_snapshot=source, outcome_snapshot=outcomes)
    monkeypatch.setattr(campaigns.CorrectionPolicy, 'load_canonical', lambda root_dir=None: policy)
    receipt = correction_tests._receipt(policy)
    path = tmp_path / 'correction-receipt.json'
    path.write_bytes(campaigns.canonical_bytes(receipt) + b'\n')
    campaigns.run(root_dir=root, correction_activation_receipt_path=path)
    assert json.loads((root / campaigns.CHECKPOINT_PATH).read_bytes())['schema'] == campaigns.CAMPAIGN_CHECKPOINT_V2_SCHEMA
    return path, receipt, policy, physical


def test_corrected_v2_to_v3_crash_recovery_and_private_reader(tmp_path, monkeypatch):
    root, intent, evidence, _ = _fixture(tmp_path, monkeypatch)
    path, receipt, policy, original_raw = _corrected_runtime(root, evidence, monkeypatch, tmp_path)
    before_checkpoint = (root / campaigns.CHECKPOINT_PATH).read_bytes()
    from engine.options_alpha_candidate_outcome_enrichment import enrich_candidate_outcomes
    source_before = campaigns.load_ledger(root / campaigns.CAMPAIGNS_PATH, campaigns.CAMPAIGNS_PATH)
    outcomes_before = campaigns.load_ledger(root / campaigns.OUTCOMES_PATH, campaigns.OUTCOMES_PATH)
    original_view = campaigns.build_effective_outcome_view(
        source_before, outcomes_before, policy, activation_receipt=receipt)
    legacy_before = enrich_candidate_outcomes(
        evidence.publication_pair.feed, effective_outcomes=original_view,
        correction_activation_receipt=receipt)
    def crash():
        raise RuntimeError('crash before v3 checkpoint')
    with pytest.raises(RuntimeError, match='crash before v3'):
        campaigns.run(root_dir=root, correction_activation_receipt_path=path,
                      expression_evidence=[evidence], before_checkpoint=crash)
    physical = (root / campaigns.OUTCOMES_PATH).read_bytes()
    assert physical.startswith(original_raw)
    assert (root / campaigns.CHECKPOINT_PATH).read_bytes() == before_checkpoint
    result = campaigns.run(root_dir=root, correction_activation_receipt_path=path,
                           expression_evidence=[evidence])
    assert result['expression_outcomes_appended'] == 0
    assert (root / campaigns.OUTCOMES_PATH).read_bytes() == physical
    checkpoint = json.loads((root / campaigns.CHECKPOINT_PATH).read_bytes())
    assert checkpoint['schema'] == campaigns.CAMPAIGN_CHECKPOINT_V3_SCHEMA
    assert checkpoint['populations']['quarantined_underlying_rows'] == 3845
    assert checkpoint['populations']['expression_rows'] == 1
    assert checkpoint['correction']['quarantine']['reserved_key_count'] == 3845
    assert checkpoint['correction']['reserved_keys']['count'] == 3846
    source = campaigns.load_ledger(root / campaigns.CAMPAIGNS_PATH, campaigns.CAMPAIGNS_PATH)
    outcomes = campaigns.load_ledger(root / campaigns.OUTCOMES_PATH, campaigns.OUTCOMES_PATH)
    view = campaigns.build_effective_outcome_view(source, outcomes, policy,
                                                 activation_receipt=receipt)
    legacy_after = enrich_candidate_outcomes(
        evidence.publication_pair.feed, effective_outcomes=view,
        correction_activation_receipt=receipt)
    assert legacy_after == legacy_before
    assert 'expression_id' not in json.dumps(legacy_after)
    selected = campaigns.read_expression_outcomes(
        effective_outcomes=view, correction_activation_receipt=receipt,
        expression_id=intent['expression_id'], observation_at='2026-08-14T17:00:00Z')
    assert len(selected) == 1
    assert campaigns.read_expression_outcomes(
        effective_outcomes=view, correction_activation_receipt=receipt,
        expression_id=intent['expression_id'], observation_at='2026-08-14T16:59:59Z') == ()
    assert selected[0].ordinal == 3846
    assert selected[0].raw == outcomes.rows[-1].raw
    assert selected[0].sha256 == outcomes.rows[-1].sha256
    selected[0].value['authority']['may_trade'] = True
    assert outcomes.rows[-1].value['authority']['may_trade'] is False
    assert campaigns.read_expression_outcomes(
        effective_outcomes=view, correction_activation_receipt=receipt,
        expression_id='unknown', observation_at='2026-08-14T17:00:00Z') == ()
    before = _bytes(root)
    with pytest.raises(campaigns.CampaignContractError, match='activation receipt'):
        campaigns.run(root_dir=root, expression_evidence=[evidence])
    tampered = copy.deepcopy(receipt)
    tampered['receipt_id'] = 'different-original-receipt'
    path.write_bytes(campaigns.canonical_bytes(tampered) + b'\n')
    with pytest.raises(campaigns.CampaignContractError, match='binding is mismatched'):
        campaigns.run(root_dir=root, correction_activation_receipt_path=path)
    with pytest.raises(campaigns.CampaignContractError):
        campaigns.read_expression_outcomes(
            effective_outcomes=view, correction_activation_receipt=tampered,
            expression_id=intent['expression_id'], observation_at='2026-08-14T17:00:00Z')
    assert _bytes(root) == before
