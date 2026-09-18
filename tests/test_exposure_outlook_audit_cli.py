import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run(*args):
    return subprocess.run([sys.executable, '-m', 'engine.exposure_outlook_research', *map(str,args)],
                          cwd=ROOT, env=dict(os.environ, PYTHONPATH=str(ROOT)),
                          capture_output=True,text=True,timeout=15)


def test_command_outputs_missing_source_without_claiming_health(tmp_path):
    result=run('audit-surface','--surface-dir',tmp_path,'--root','SPY','--session','2026-09-18',
               '--as-of','2026-09-18T21:00:00Z')
    assert result.returncode==0,result.stderr
    doc=json.loads(result.stdout)
    assert 'MISSING_INDEX' in doc['reason_codes']
    assert not doc['forecast_eligible']


def test_command_invalid_date_returns_typed_error(tmp_path):
    result=run('audit-surface','--surface-dir',tmp_path,'--root','SPY','--session','2026-02-30',
               '--as-of','2026-09-18T21:00:00Z')
    assert result.returncode==2
    assert json.loads(result.stdout)['error']=='INVALID_RESEARCH_INPUT'


def test_help_does_not_advertise_uninstalled_baseline():
    result=run('--help')
    assert result.returncode==0
    assert 'audit-surface' in result.stdout
    assert '{baseline' not in result.stdout
    assert '{audit-surface,baseline' not in result.stdout


def test_price_audit_consumes_a_response_file_not_another_network_client(tmp_path):
    source=tmp_path/'response.json'
    source.write_text(json.dumps({'t':'SPY','tf':'5m','session_date':'2026-09-17','bars':[]}))
    result=run('audit-price','--input',source,'--root','SPY','--session','2026-09-17',
               '--as-of','2026-09-18T21:00:00Z')
    assert result.returncode==0,result.stderr
    doc=json.loads(result.stdout)
    assert doc['reason_codes']==['INTRADAY_TRAINING_CORPUS_NOT_QUALIFIED','PRICE_BARS_UNAVAILABLE']
    assert len(doc['input_sha256'])==64
