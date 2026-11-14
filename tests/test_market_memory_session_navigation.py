"""Genuine synthetic native catalog -> exact saved reader; no installed data."""
import json
import os
import subprocess
from pathlib import Path
import pytest
from fastapi import HTTPException
from app import market_memory as api
from engine.neuralweb import market_memory_retained_catalog as catalog
from engine.neuralweb import market_memory_retained_saved as saved
from engine.neuralweb import market_memory_retained_use as use
from tests.test_market_memory_retained_consumer import original
from tests.test_market_memory_retained_context_cohort import capture, owner, CUTOFF


def _pair(original, monkeypatch):
    root, reader, _, _, captures = original
    b = capture(root, monkeypatch, session='2026-08-13', growth=0.7, seconds=60)
    reader, pin = owner(root)
    a = captures[3]
    def page(record):
        return catalog.read_catalog(root, user_id='member', mode='historical_hypothetical', offset=0,
            generation_id=pin.generation_id, generation_sha256=pin.generation_sha256,
            query_id=record.capture_receipt['query_id'], context_id=record.packet['context_id'], limit=1)
    return root, a, b, page(a), page(b)


def _saved(root, page, row, cutoff=CUTOFF):
    return api.retained_saved_for_user(root, 'member', {
        **{key: page['generation'][key] for key in ('generation_id','generation_sha256')},
        **{key: row[key] for key in ('query_id','context_id','capture_id','subject_id')},
        'query_cutoff': cutoff})


def test_native_cross_page_session_refs_reopen_their_own_originals(original, monkeypatch):
    root, a, b, ap, bp = _pair(original, monkeypatch)
    ar, br = ap['entries'][0], bp['entries'][0]
    assert ap['selection']['offset'] != bp['selection']['offset']
    relation = ar['same_session_observations']
    assert relation['relationship'] == 'same_source_session_not_certified_correction.v1'
    assert relation['total'] == 1 and relation['omitted'] == 0
    ref = relation['observations'][0]
    assert ref['context_id'] == br['context_id']
    for key in ('query_id','capture_id','packet_sha256','subject_id','instrument_id','source_session','earliest_supported_cutoff'):
        assert ref[key] == br[key]
    av, bv = _saved(root, ap, ar), _saved(root, bp, br)
    assert av['context']['context_id'] == a.packet['context_id']
    assert bv['context']['context_id'] == b.packet['context_id']
    assert av['feature_projection']['state']['growth_score'] != bv['feature_projection']['state']['growth_score']
    assert ar['same_session_observations']['family_sha256'] == br['same_session_observations']['family_sha256']
    wire = json.dumps({'a_page':ap,'b_page':bp,'a_saved':av,'b_saved':bv,'cutoff':CUTOFF},sort_keys=True)
    wire_path = root / 'synthetic-session-navigation-wire.json'
    wire_path.write_text(wire)
    source = Path(__file__).resolve().parents[1]
    result = subprocess.run(['node', str(source/'tests/js/market_memory_session_navigation.test.cjs'),
        str(source/'templates/market_memory_retained.js'),
        str(source/'tests/fixtures/market_memory_retained_owner_wire.json'), str(wire_path)],
        capture_output=True, text=True, timeout=30, cwd=source)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.count('PASS ') == 19
    if os.environ.get('MM_SESSION_WIRE'):
        Path(os.environ['MM_SESSION_WIRE']).write_text(wire)
        Path(os.environ['MM_SESSION_WIRE']+'.js.log').write_text(result.stdout + result.stderr)


def test_native_earlier_cutoff_never_shifts_to_target(original, monkeypatch):
    root, _, _, ap, bp = _pair(original, monkeypatch)
    cutoff = ap['entries'][0]['earliest_supported_cutoff']
    assert cutoff < bp['entries'][0]['earliest_supported_cutoff']
    with pytest.raises(HTTPException) as failure:
        _saved(root, bp, bp['entries'][0], cutoff)
    assert failure.value.status_code == 422


def test_revocation_precedes_target_reader(original, monkeypatch):
    root, _, _, ap, bp = _pair(original, monkeypatch)
    def revoked(_): raise HTTPException(403)
    monkeypatch.setattr(use, '_enforce_current_site_user', revoked)
    monkeypatch.setattr(saved.trusted, 'TrustedFileAsKnownAtReader', lambda *a, **k: pytest.fail('reader after revocation'))
    with pytest.raises(HTTPException) as failure: _saved(root, bp, bp['entries'][0])
    assert failure.value.status_code == 403


def test_other_source_sessions_have_no_relation(original):
    root, _, _, _, _ = original
    page = catalog.read_catalog(root,user_id='member',mode='historical_hypothetical', offset=0,limit=8)
    assert all(row['same_session_observations']['observations'] == [] for row in page['entries'])


def test_native_session_reference_count_and_response_bytes_bounded(original, monkeypatch):
    root = original[0]
    for i in range(10):
        capture(root, monkeypatch, session='2026-08-13', growth=0.1 + i * 0.01, seconds=60 + i)
    page = catalog.read_catalog(root, user_id='member',mode='historical_hypothetical',offset=0,limit=20)
    grouped = [row['same_session_observations'] for row in page['entries'] if row['source_session']=='2026-08-13']
    assert grouped
    assert all(item['total']==10 and len(item['observations'])==4 and item['omitted']==6 for item in grouped)
    assert len(catalog.cohort.canonical(page)) <= catalog.MAX_RESPONSE_BYTES


@pytest.mark.parametrize('denied_action', ['read_retained_macro_capture_metadata', 'disclose_retained_macro_capture'])
def test_off_page_sibling_requires_its_own_current_authorization(original, monkeypatch, denied_action):
    root, _, _, ap, bp = _pair(original, monkeypatch)
    target = bp['entries'][0]['context_id']
    original_check = use.RetainedHouseUsePolicy.check
    checks = []
    def check(self, action, resource):
        original_check(self, action, resource)
        checks.append((action, resource.get('context_id')))
        if action == denied_action and resource.get('context_id') == target:
            raise use.RetainedUseError('synthetic_target_revoked')
    monkeypatch.setattr(use.RetainedHouseUsePolicy, 'check', check)
    with pytest.raises(use.RetainedUseError, match='synthetic_target_revoked'):
        catalog.read_catalog(root,user_id='member',mode='historical_hypothetical',offset=ap['selection']['offset'],limit=1,
            generation_id=ap['generation']['generation_id'],generation_sha256=ap['generation']['generation_sha256'])
    assert (denied_action, target) in checks
