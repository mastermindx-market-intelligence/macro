"""T005.S9 full listed-input admission; invented cohort, no acquisition or numeric promotion."""
from dataclasses import replace
from datetime import datetime, timedelta
import base64
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

from engine import ontology_scenario_runtime as runtime, transmission_chains as txi
from lib import store
from test_ontology_explorer_transport import published_wti, x2_inputs  # noqa: F401


def _evaluate(published, **kwargs):
    root, assumption, snapshot, sessions = published
    return runtime.evaluate_current_scenario(root, assumption, snapshot['source']['source_manifest_hash'],
                                            verified_wti_sessions=sessions, **kwargs)


def _unavailable(result):
    assert result['root_evaluation']['status'] == 'UNAVAILABLE'
    assert result['owner_receipt'] is None
    assert 'native_txi_input_cohort_unavailable' in result['root_evaluation']['missing_owner_inputs']


def test_coherent_listed_inputs_and_appended_ledger_remain_bounded(published_wti):
    root, _, _, _ = published_wti
    state = json.loads((root / 'data/transmission/chain_state.json').read_text())
    ledger = next(row for row in state['input_capture']['reads'] if row['path'].endswith('chain_episodes.jsonl'))
    assert len((root / ledger['path']).read_bytes()) > ledger['bytes']
    verdict = txi.verify_prospective_input_capture(root, state)
    assert verdict['status'] == 'listed_input_bytes_match'
    assert verdict['producer_execution_authenticity'] == 'unqualified'
    assert verdict['causal_read_completeness'] == 'unqualified'
    assert verdict['scientific_acceptance'] is False
    result = _evaluate(published_wti)
    assert result['root_evaluation']['status'] == 'ROOT_THRESHOLD_MET'
    assert result['combined_estimate'] is None


@pytest.mark.parametrize('change', ['regime_same_size', 'regime_missing', 'ledger_prefix', 'ledger_truncated',
                                   'producer', 'definition_population'])
def test_changed_listed_cohort_refuses_before_price_decode(monkeypatch, published_wti, change):
    root, _, _, _ = published_wti
    regime = root / 'data/regime/latest.json'
    if change == 'regime_same_size':
        before = regime.read_bytes()
        after = before.replace(b'original', b'modified')
        assert len(before) == len(after) and before != after
        regime.write_bytes(after)
    elif change == 'regime_missing':
        regime.unlink()
    elif change.startswith('ledger'):
        path = root / 'data/transmission/chain_episodes.jsonl'
        path.write_bytes(b'' if change == 'ledger_truncated' else path.read_bytes().replace(b'predecessor', b'changed-one'))
    elif change == 'producer':
        (root / 'engine/transmission_chains.py').write_text('changed producer')
    else:
        (root / 'knowledge/transmission/new.yaml').write_text('new: definition')
    decoded = []
    original = store._wti_parquet_image
    def decode(*args, **kwargs):
        decoded.append(True)
        return original(*args, **kwargs)
    monkeypatch.setattr(store, '_wti_parquet_image', decode)
    # Ledger and YAML changes also affect the X1 manifest. Test admission against
    # its newly selected snapshot; the older TXI capture must still be refused.
    snap = runtime.compose_snapshot(root, chain=published_wti[2]['source']['chain'])
    sessions = replace(published_wti[3], manifest_hash=snap['source']['source_manifest_hash'])
    _unavailable(_evaluate((root, published_wti[1], snap, sessions)))
    assert not decoded


@pytest.mark.parametrize('published_wti', ['v2'], indirect=True)
@pytest.mark.parametrize('moment', ['before_admission', 'inside_selector'])
def test_regime_change_blocks_independent_selector_or_decode(monkeypatch, published_wti, moment):
    root, assumption, snap, sessions = published_wti
    export = json.loads((root / 'data/yahoo/CL_F.observation.json').read_bytes())
    facts = json.loads(base64.b64decode(export['capture_receipt']['content_base64']))['native_sessions']
    subject = runtime.WTISessionSubject(sessions.observation_sha256, export['canonical_parquet']['sha256'],
        sessions.txi_generation, sessions.manifest_hash, sessions.knowledge_cutoff)
    grant = runtime.WTISessionAdmission(subject, hashlib.sha256(store._availability_json(facts)).hexdigest(),
                                         sessions.knowledge_cutoff)
    calls = []
    def change():
        (root / 'data/regime/latest.json').write_text('{"regime":"later-publication"}')
    def selector(observed):
        calls.append(observed)
        assert observed == subject
        if moment == 'inside_selector': change()
        return grant
    def forbidden(*args, **kwargs):
        raise AssertionError('unqualified cohort decoded prices')
    monkeypatch.setattr(store, '_wti_parquet_image', forbidden)
    if moment == 'before_admission': change()
    result = runtime.evaluate_current_scenario(root, assumption, snap['source']['source_manifest_hash'],
                                               wti_session_selector=selector)
    _unavailable(result)
    assert len(calls) == (1 if moment == 'inside_selector' else 0)


def test_regime_change_during_evaluation_cannot_return_numeric(monkeypatch, published_wti):
    root = published_wti[0]
    original = runtime.evaluate_scenario
    def evaluate(*args, **kwargs):
        result = original(*args, **kwargs)
        if kwargs.get('baseline') is not None:
            (root / 'data/regime/latest.json').write_text('{"regime":"later-publication"}')
        return result
    monkeypatch.setattr(runtime, 'evaluate_scenario', evaluate)
    _unavailable(_evaluate(published_wti))


def test_late_capture_cannot_be_rescued_by_later_publication(published_wti):
    root, assumption, old, sessions = published_wti
    path = root / 'data/transmission/chain_state.json'
    state = json.loads(path.read_text())
    capture = state['input_capture']
    capture['capture_completed_at'] = (datetime.fromisoformat(state['built'].replace('Z', '+00:00'))
                                       + timedelta(seconds=1)).isoformat()
    capture['generation_id'] = 'sha256:' + hashlib.sha256(txi._capture_json(
        {key: value for key, value in capture.items() if key != 'generation_id'})).hexdigest()
    path.write_text(json.dumps(state))
    # Observing publication later does not move the selected cutoff forward.
    later = datetime.fromisoformat(state['built'].replace('Z', '+00:00')) + timedelta(hours=1)
    snap = runtime.compose_snapshot(root, chain=old['source']['chain'], now=later)
    sessions = replace(sessions, manifest_hash=snap['source']['source_manifest_hash'], txi_generation=capture['generation_id'])
    result = _evaluate((root, assumption, snap, sessions), now=later)
    assert result['root_evaluation']['status'] == 'UNAVAILABLE'
    assert 'native_txi_generation_at_cutoff' in result['root_evaluation']['missing_owner_inputs']
