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


def test_label_price_cli_computes_outcomes_without_mutating_input(tmp_path):
    from datetime import datetime, timezone
    start = int(datetime(2026, 9, 18, 9, 55, tzinfo=timezone.utc).timestamp())
    bars = [[start+i*300, 100., 100.1, 99.9, 100., 1.] for i in range(7)]
    p = dict(t='SPY', tf='5m', session_date='2026-09-18', bars=bars,
             source_evidence=dict(schema='terminal.intraday_source_evidence.v1',
                 symbol='SPY', requested_timeframe='5m', session='regular',
                 timestamp_basis='market_local_display_epoch', source_counts=dict(live_tail=7),
                 response_scope=dict(requested_date='2026-09-18', returned_bars=7,
                     first_bar_time=bars[0][0], last_bar_time=bars[-1][0])))
    source = tmp_path/'response.json'; original = json.dumps(p)
    source.write_text(original)
    result = run('label-price', '--input', source, '--root', 'SPY',
                 '--session', '2026-09-18', '--origin', '2026-09-18T14:00:00Z',
                 '--as-of', '2026-09-18T21:00:00Z',
                 '--session-open', '2026-09-18T13:30:00Z',
                 '--session-close', '2026-09-18T20:00:00Z', '--calendar-ref', 'fixture:session')
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    assert out['outcomes'][0]['endpoint_status'] == 'observed'
    assert out['outcomes'][0]['endpoint_return_pct'] == 0.
    assert out['can_publish_forecast'] is False and len(out['input_sha256']) == 64
    assert source.read_text() == original
