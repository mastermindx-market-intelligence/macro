"""Executable inspection over the real trusted owner, with synthetic source bytes."""
from datetime import datetime,timezone,timedelta
from pathlib import Path
import json,os,subprocess,sys
from engine.neuralweb import market_memory_trusted as trusted
from engine.neuralweb import market_memory_projection as projection
from engine.neuralweb import market_memory_identity as identity
from tests.test_market_navigator_memory import packet
ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts/research/market_navigator_memory_inspect.py'


def call(root,p,*extra):
    args=[sys.executable,str(SCRIPT),'--store-root',str(root),
        '--subject-id',p['subject']['subject_id'],'--instrument-id',p['subject']['instrument_id'],
        '--event-time',p['clocks']['event_time'],'--as-known-at',p['clocks']['as_known_at'],
        '--horizon','swing',*extra]
    env=dict(os.environ);env.pop('PYTHONPATH',None)
    return subprocess.run(args,cwd=root.parent,env=env,text=True,capture_output=True,timeout=20)


def create_synthetic_capture(tmp_path,monkeypatch):
    source=tmp_path/'latest.json'
    raw=(ROOT/'tests/fixtures/market_navigator/raw_regime.synthetic.json').read_bytes()
    source.write_bytes(raw)
    clock=datetime(2026,8,10,10,tzinfo=timezone.utc)
    monkeypatch.setattr(projection,'_utc_now',lambda:clock)
    snapshot=projection.build_macro_regime_snapshot(source)
    monkeypatch.setattr(identity,'_utc_now',lambda:clock+timedelta(seconds=1))
    evidence=identity.build_current_spy_identity()
    monkeypatch.setattr(trusted,'_utc_now',lambda:clock+timedelta(seconds=2))
    root=tmp_path/'trusted-store'
    stored=trusted.capture_trusted_regime_context(root,tmp_path/'private-evidence',
        snapshot=snapshot,identity_evidence=evidence,raw_source_body=raw,deployed_commit='a'*40)
    return root,stored.packet


def tree(root):
    return {str(x.relative_to(root)):x.read_bytes() if x.is_file() else None for x in root.rglob('*')}


def test_executable_trusted_owner_path_and_no_writes(tmp_path,monkeypatch):
    root,p=create_synthetic_capture(tmp_path,monkeypatch);before=tree(root)
    result=call(root,p,'--previous-context-id',p['context_id'])
    assert result.returncode==0,result.stderr
    data=json.loads(result.stdout)
    assert data['source_status']=='exact_owner_read' and data['changes']['changes']==[]
    assert data['evidence']['context_id']==p['context_id']
    row=next(r for r in data['evidence']['features'] if r['feature_id']=='macro.regime_state')
    assert row['status']=='observed' and row['value'] is None
    assert 'source_context' not in data and str(root) not in result.stdout
    assert before==tree(root)


def test_unavailable_store_is_not_created(tmp_path):
    root=tmp_path/'absent';result=call(root,packet())
    assert result.returncode==2 and not root.exists()
    assert json.loads(result.stdout)['source_status']=='source_unavailable'
    assert str(root) not in result.stdout


def test_future_query_not_current_fallback(tmp_path):
    root=tmp_path/'absent';p=packet();p['clocks']['as_known_at']='2999-01-01T00:00:00Z'
    result=call(root,p)
    assert result.returncode==2 and not root.exists()
    assert json.loads(result.stdout)['source_status']=='invalid_request_or_evidence'


def test_empty_trusted_generation_is_exact_absence_not_outage(tmp_path):
    root=tmp_path/'existing-empty';trusted.initialize_trusted_store(root)
    before=tree(root);result=call(root,packet())
    assert result.returncode==2 and json.loads(result.stdout)['source_status']=='exact_context_absent'
    assert before==tree(root)
