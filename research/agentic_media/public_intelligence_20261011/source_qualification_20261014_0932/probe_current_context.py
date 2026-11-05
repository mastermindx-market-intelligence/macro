"""Offline replay of the Oct14 source qualification. No production/provider effects."""
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(root))
from engine.press import desk_planner as planner
from engine.press.external_candidate import _reviewed_context

phase = Path(__file__).resolve().parent
observed = json.loads((phase / 'installed_candidate_read.json').read_text())
rev = observed['head']
manifest = json.loads((phase.parent / 'validator_integrity_phase/postlanding/mmx-current-expected-hashes.json').read_text())
for rel, digest in manifest.items():
    assert hashlib.sha256((root / rel).read_bytes()).hexdigest() == digest, rel
assert observed['stable_head'] and observed['inputs_unchanged']
assert not observed['own_current_events'] and not observed['committed_own_events']
assert observed['provider_calls'] == observed['staging_or_producer_writes'] == 0

paths = [rel for _, rel in planner._ENGINE_ARTIFACTS]
raw = {rel: subprocess.check_output(['git', 'show', rev + ':' + rel], cwd=root) for rel in paths}
for rel, data in raw.items():
    assert hashlib.sha256(data).hexdigest() == observed['input_hashes'][rel], rel
rows = [dict(id=f['id'], artifact=f['ref'][len('artifact:'):],
             sha256=observed['input_hashes'][f['ref'][len('artifact:'):]],
             relevance='Identity and date eligibility only; no story relevance or publication approval.')
        for f in observed['engine_facts']]
accepted, refused = [], []
with tempfile.TemporaryDirectory(prefix='mmx-current-context-') as tmp:
    fixture = Path(tmp).resolve()
    for rel, data in raw.items():
        path = fixture / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    for row in rows:
        try:
            facts, revisions = _reviewed_context([row], root=fixture, as_of=date(2026,10,14), window_days=3)
        except ValueError as exc:
            assert row['id'] == 'breadth_split' and 'outside the current Brief window' in str(exc)
            refused.append(dict(id=row['id'], reason=str(exc)))
        else:
            assert len(facts) == 1 and facts[0]['dated'] == '2026-10-13'
            assert len(revisions) == 1
            accepted.extend(facts)
    assert len(accepted) == 14 and len(refused) == 1
    broken = {**rows[0], 'sha256': '0' * 64}
    try:
        _reviewed_context([broken], root=fixture, as_of=date(2026,10,14), window_days=3)
    except ValueError as exc:
        assert 'hash' in str(exc)
        hash_refusal = str(exc)
    else:
        raise AssertionError('changed input hash accepted')
    for rel, data in raw.items():
        assert (fixture / rel).read_bytes() == data
radar = next(f for f in accepted if f['id'] == 'risk_radar')
assert 'SPY closing prices' in radar['text'] and 'at least 5%' in radar['text']
assert 'not precision-grade' in radar['text'] and 'not independent episodes' in radar['text']
assert radar['values'] == ['73.9', '0.19', '5']
market = json.loads(raw['data/market_state/latest.json'])
fear = json.loads(raw['site/basketdata/fear_greed.json'])
print(json.dumps({
    'source_commit': rev,
    'runtime_manifest_exact': len(manifest),
    'scope': 'Local unchanged reviewed consumer on actual installed input bytes; date/identity proof, not story admission.',
    'accepted_date_identity_count': len(accepted), 'stale_refusals': refused,
    'bad_hash_refused': hash_refusal, 'inputs_unchanged': True,
    'radar_local_only': radar,
    'market_input_vintages': market['input_vintages'],
    'market_stale_inputs': market['stale_inputs'],
    'sentiment_leg_vintages': [{k:leg.get(k) for k in ['key','last_date','freshness']} for leg in fear['legs_included']],
    'source_relevance_approved': False, 'provider_calls':0, 'staging_writes':0,
    'publication':False, 'cutover':False, 'd14_credit':'0/10'
}, indent=2))
