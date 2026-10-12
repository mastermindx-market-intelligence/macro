"""Read-only verification of saved R11 proof identities; not a collector run."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from lib import config
HERE=Path(__file__).resolve().parent


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    r=json.loads((HERE/'pipeline_proof.json').read_text())
    old=json.loads((HERE/'pipeline_before_type_hardening.json').read_text())
    data=Path(config.data_dir())
    assert r['implementation_head']=='b53636f05b6374dafabcbc9c5d8085773d88fdf0'
    for key in ['inputs','old_live_observation_files']:
        assert all((sha(data/p) if (data/p).exists() else None)==h for p,h in r[key].items()),key
    assert all(sha(data/p)==h for p,h in r['gates'].items())
    assert all(sha(ROOT/p)==h for p,h in r['prior_evidence'].items())
    assert all(sha(ROOT/p)==h for p,h in r['sources'].items())
    assert len(r['capture_digests'])==9
    assert len({x['capture_id'] for x in r['capture_digests']})==9
    assert [x['capture_count'] for x in r['okx_runs']]==[1,2,3,3]
    for key in ['okx_runs','asof_cases','capture_digests','request_count','request_signature',
                'bgeo_public_fetch_requests','failure_retains_numerics_and_reports_stale',
                'elapsed_cases','stored_snapshot_check','stored_snapshot_clock_staleness']:
        assert r[key]==old[key],key
    assert len(r['elapsed_cases'])==54 and len(r['asof_cases'])==4
    assert r['stored_snapshot_clock_staleness']['hours_behind_ref']==0
    assert r['stored_snapshot_clock_staleness']['hours_behind_clock']==71
    archive=HERE.parent/'r10/initial/test_btc_impulse_falsifier.py.txt'
    assert sha(archive)=='c65254c4903b7e343ab370c3d1d9c7b6bc6f55aed01ee90e17c4974a7bd5cd37'
    assert not archive.with_suffix('').exists()
    assert sha(HERE.parent/'r10/reference_btc_intraday_cvd.py.txt')=='36921a561b7750b37b7aabe8b8901d5f101d09a0c705248270a9d44b673130b4'
    manifest=json.loads((HERE.parent/'r10/MANIFEST.json').read_text())
    for path,entry in manifest['artifacts'].items():assert sha(ROOT/path)==entry['sha256'],path
    assert sha(HERE.parent/'r10/results.json')=='43b08a48e59ca66cc367d7effbc2e65a18aa0921900d52573debc64b3395a173'
    log=(HERE/'verification_final.txt').read_text()
    assert '368 passed, 49 warnings' in log and '\nEXIT 1' not in log
    assert 'R11_PIPELINE_VERIFIED:' in (HERE/'pipeline_log.txt').read_text()
    current=HERE/'MANIFEST.json'
    if current.exists():
        m=json.loads(current.read_text())
        for path,v in m['artifacts'].items():
            assert sha(ROOT/path)==v['sha256'] and (ROOT/path).stat().st_size==v['bytes'],path
    print('R11_RECEIPTS_VERIFIED: 57 input identities,18 gates,137 prior artifacts,8 candidate source files; original R10 results/reference lineage retained.')
    print('R11_COMPATIBILITY_VERIFIED: before/after type hardening same synthetic semantics; no real response-observation files created; 368-test receipt present.')
    print('Independent external review and live production proof remain outstanding.')


if __name__=='__main__':main()
