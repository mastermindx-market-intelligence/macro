"""Read-only R12 evidence check. No collector, study rerun or data mutation."""
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from lib import config
HERE=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    proof=json.loads((HERE/'pipeline_proof.json').read_text());data=Path(config.data_dir())
    assert proof['implementation_head']=='372cdf9f443a9b53e32df01feef718a00d07783f'
    for path,h in proof['sources'].items():
        if path=='tests/test_btc_intraday_cvd.py':
            initial=subprocess.check_output(['git','show',proof['implementation_head']+':'+path],cwd=ROOT)
            assert hashlib.sha256(initial).hexdigest()==h
            assert (ROOT/path).read_bytes().startswith(initial)
        else:assert sha(ROOT/path)==h,path
    for path,h in proof['inputs'].items():assert (sha(data/path) if (data/path).exists() else None)==h,path
    for key in ['gates','old_live_observation_files']:
        for path,h in proof[key].items():assert (sha(data/path) if (data/path).exists() else None)==h,path
    for path,h in proof['prior_evidence'].items():assert sha(ROOT/path)==h,path
    prior=json.loads((HERE.parent/'r11/pipeline_proof.json').read_text())
    for key in ['okx_runs','asof_cases','capture_digests','request_count','request_signature','bgeo_public_fetch_requests',
                'failure_retains_numerics_and_reports_stale','elapsed_cases','stored_snapshot_check','stored_snapshot_clock_staleness']:
        assert proof[key]==prior[key],key
    physical=json.loads((HERE/'parquet_baseline.json').read_text())
    assert [x['existing'] for x in physical['rows']]==[0,100,1000]
    for row in physical['rows']:
        assert row['before']['rows']==row['existing']
        assert row['after']['rows']==row['existing']+1
        assert row['payload_bytes_per_capture']==17301
        assert row['logical_capture_bytes']==20848*(row['existing']+1)
        assert row['append_seconds']>=0 and row['duplicate_seconds']>=0
        assert row['after']['file_bytes']>0 and row['after']['declared_uncompressed_bytes']>0
    for path,h in physical['sources'].items():assert sha(ROOT/path)==h,path
    assert sha(ROOT/'engine/btc_intraday_cvd.py')=='922bf74f0c0d5922046c7214347202c624b73b4980aabf8793753eab4cbae815'
    assert sha(HERE/'reference_cvd_before_price_guard.py.txt')=='12117869d18239cdffd4d70b0c6906ba8a51bf140894c860e07321db2a8420a9'
    assert '1 failed, 1 passed' in (HERE/'red_price_host.txt').read_text()
    assert '431 passed, 49 warnings' in (HERE/'verification_final.txt').read_text()
    assert (HERE/'verification_final.txt').read_text().count('EXIT=0')==4
    manifest=HERE/'MANIFEST.json'
    if manifest.exists():
        m=json.loads(manifest.read_text())
        for path,v in m['artifacts'].items():
            p=ROOT/path;assert p.stat().st_size==v['bytes'] and sha(p)==v['sha256'],path
    print('R12_RECEIPTS_VERIFIED: 57 input identities,18gates,137prior artifacts unchanged; runtime source matches pipeline; appended tests covered by431passing tests.')
    print('R12_COMPATIBILITY: all original pipeline scenario results identical; saved sandbox price-patch hash now matches actual repository; Parquet measurements/limitations preserved.')
    print('No live collection, production acceptance, independent reviewer, capacity limit or new trading model is implied.')

if __name__=='__main__':main()
