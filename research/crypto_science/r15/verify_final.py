"""Read-only final desk evidence reconciliation; not independent user/reviewer proof."""
from pathlib import Path
from urllib.parse import urlsplit
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from lib import config
HERE=Path(__file__).resolve().parent;FINAL=HERE/'completion'
SITE=Path('/Volumes/Mastermind/research/crypto-vector-r2-20260926-sol-001/r15_actual')
CANON=ROOT/'mockups/evidence/crypto-desk-r15-completion'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    d=json.loads((FINAL/'browser_proof.json').read_text());data=Path(config.data_dir())
    for k,v in d['sources'].items():assert sha(ROOT/k)==v,k
    for k,v in d['inputs'].items():assert (sha(data/k) if (data/k).exists() else None)==v,k
    for k,v in d['gates'].items():assert sha(data/k)==v,k
    for k,v in d['prior_evidence'].items():assert sha(ROOT/k)==v,k
    for k,v in d['screenshots'].items():assert sha(ROOT/k)==v,k
    for e in d['expected'].values():assert sha(SITE/e['filename'])==e['html_sha256']
    prior=json.loads((HERE/'browser_proof.json').read_text())
    for k,v in prior['screenshots'].items():assert sha(ROOT/k)==v,k
    for k in ['inputs','gates','prior_evidence']:assert d[k]==prior[k],k
    current=(ROOT/'templates/crypto.html.j2').read_text()
    before=subprocess.check_output(['git','show','c4e939f49ffc13ef705b4110dc0ad48bb08f0fa2:templates/crypto.html.j2'],cwd=ROOT,text=True)
    expected_source=before.replace('.desk-brain-entry{font-family:inherit;', '.desk-brain-entry{font-family:var(--font-ui);')
    expected_source=expected_source.replace('#crypto-overview .desk-tape .ilx{margin:0}', '#crypto-overview .desk-tape .ilx{margin:0}\n/* A viewBox-length dash can clip a non-scaling stroke on a widened SVG. */\n#crypto-overview .desk-tape .ilx-path{stroke-dasharray:none}')
    assert current==expected_source
    assert len(d['cases'])==112 and not d['failures'] and d['unchanged']
    keys={(x['scenario'],x['width'],x['theme'],x['lang']) for x in d['cases']}
    expected={(s,w,t,l) for s in d['expected'] for w in [320,390,768,1440] for t in ['dark','light'] for l in ['en','zh']}
    assert keys==expected
    for x in d['cases']:
        e=d['expected'][x['scenario']];assert x['status']==200 and not x['issues'] and not x['page_errors']
        assert not x['geometry']['pageOverflow'] and not x['geometry']['innerOverflow']
        assert x['geometry']['proseMin']>=12.5 and x['link_min_height']>=44
        assert x['readings']['budget_state']==e['state']
        assert x['readings']['budget_value']==('—' if e['budget'] is None else str(e['budget'])+'%')
        assert x['readings']['decision_date']==e['decision_date']
        assert x['source_disclosure'] and x['keyboard_jumps']==['money-flows','leverage-heat','allocation']
        if e['history']:
            chart=x['chart_seen'];assert chart['revealed'] and chart['pathCount']>0
            assert chart['dashOffsets'] and all(abs(v)<.1 for v in chart['dashOffsets'])
            assert all(chart['paintedEnds']) and all(v=='none' for v in chart['dashArrays'])
        else:assert x['chart_seen'] is None
        if x['scenario'] in ['known','combined']:assert all(x['assistant_check'].values())
    fail=json.loads((FINAL/'assistant_failure.json').read_text())
    assert fail['html_sha256']==d['expected']['known']['html_sha256'] and len(fail['cases'])==4
    assert {(x['width'],x['language']) for x in fail['cases']}=={(w,l) for w in [390,1440] for l in ['en','zh']}
    assert all(x['button_reenabled'] and x['budget_preserved'] and x['allocation_link_works'] and x['blocked_script_requests']>=1 for x in fail['cases'])
    capture=json.loads((FINAL/'capture_run_receipt.json').read_text())
    assert capture['html_sha256']==d['expected']['known']['html_sha256'] and capture['exit_code'] in [0,None]
    assert capture['owner_source']==sha(ROOT/'scripts/capture_page_evidence.py')
    assert capture['wrapper_source']==sha(HERE/'capture_canonical.py')
    manifest=json.loads((CANON/'manifest.json').read_text());states=[s for p in manifest['pages'] for s in p['states']]
    captured=[s for s in states if s.get('captured')]
    assert len(captured)==32 and len(states)==32
    rest=[s for s in captured if not s.get('force_state')];assert len(rest)==8
    assert {(s['viewport'],s['theme'],s['locale']) for s in rest}=={(v,t,l) for v in ['desktop','mobile'] for t in ['dark','light'] for l in ['en','zh']}
    for name in ['brain-hover','brain-focus','chart-review']:
        f=[s for s in captured if s.get('force_state')==name];assert len(f)==8
        assert all(s.get('applied_force_state')==name for s in f)
    for s in captured:
        p=ROOT/s['file']
        if not p.exists():p=CANON/s['file']
        assert p.exists() and sha(p)==s['sha256'],s['file']
    assert 'blocking=0' in (FINAL/'design_gate.txt').read_text()
    checks=(FINAL/'verification_host.txt').read_text();assert '448 passed' in checks and 'EXIT 1' not in checks
    for k,v in d['assets']['assets'].items():assert sha(SITE/k)==v,k
    integrated=json.loads((FINAL/'main_integration.json').read_text());assert integrated['exit']==0 and not integrated['conflicts']
    assert all(x['same'] for x in integrated['runtime_blobs'].values())
    sibling=json.loads((FINAL/'integration.json').read_text());assert sibling['exit']==0 and sibling['conflict_markers']==0
    assert sha(FINAL/'combined_crypto.html.j2')==sibling['combined_sha256']
    print('R15_FINAL_RECEIPTS_VERIFIED:112 complete browser cells;4 assistant failure cells;32 canonical states and their image identities; original evidence preserved.')
    print(f"UNCHANGED:{len(d['inputs'])} input identities,{len(d['gates'])} gates,{len(d['prior_evidence'])} prior artifacts; canonical fonts verified but not published.")
    print('Exact current runtime/source, completed chart animations, seven budget/history states, five main-integration runtime blobs and sibling table integration verified. Same-session evidence, not independent review or deployment.')

if __name__=='__main__':main()
