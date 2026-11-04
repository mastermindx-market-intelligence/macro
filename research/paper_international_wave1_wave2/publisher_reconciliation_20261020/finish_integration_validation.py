from __future__ import annotations
import concurrent.futures, datetime, gzip, hashlib, json, pathlib, re, subprocess
W = pathlib.Path('/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018')
R = W/'research/paper_international_wave1_wave2/publisher_reconciliation_20261020'
SOURCE = 'ec1277e909ffed27f58f9f4b107b81f5985fb7b8'
MAIN = '13e098071ab2799c41a170d21ad522f751dfb15a'
PY = '/tmp/intl-country-cockpit-testenv-20261018/bin/python'
def git(*args):
    return subprocess.check_output(['git', *args], cwd=W, text=True).strip()
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name, value):
    (R/name).write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')
assert git('rev-parse','HEAD') == SOURCE
assert git('rev-parse','MERGE_HEAD') == MAIN
assert git('branch','--show-current') == 'sol/web-intl-country-cockpit-20261018'
expected = {
    '.github/ci/legacy-jobs.yml':'62e68a7145bd3dc8760ca704b07cee8ab2870c522f0709e642b0e6842175c7e7',
    'app/deploy/Caddyfile':'0cbe288bf37b66ff899714496c5984bbd096225f86664775fe76a1711c454e4d',
    'tests/test_site_access_boundary.py':'55724269e662af26a3a0d7a6c76b1538943d0073d4f1e598952b52c84f64d104',
}
for path, value in expected.items():
    assert digest(W/path) == value, path
browser=json.loads((R/'browser_verification.json').read_text())
proof=json.loads((R/'current_integration_proof.json').read_text())
assert browser['country_checks']==browser['passed']==84
assert len(browser['focus_checks'])==12 and all(x['passed'] for x in browser['focus_checks'])
assert browser['ageing_passed']==8 and not browser['page_errors']
assert proof['passed'] and proof['inputs_unchanged']
raw=gzip.decompress((R/'paper_edge_correction_native.json.gz').read_bytes())
assert hashlib.sha256(raw).hexdigest()=='11f826d608456d9d3488ed861a76f5200d96d0955b2d016c63c42c4efa69f847'
write('paper_edge_correction_summary.json', {
    'schema':'mastermind.intl_paper_edge_correction.v1',
    'file_id':'01M3P1TW5Y3XWQC37ADDS8K5AG','page_id':'p-G-0',
    'boards':['DMX-0','DW7-0','E4D-0','EC2-0'],
    'operation_key':'intl-country-no-edge-20261020-01',
    'finish_operation_key':'intl-country-no-edge-20261020-finish',
    'edit_effect':'APPLIED_RESPONSE_OBSERVED','finish_effect':'APPLIED_RESPONSE_OBSERVED',
    'change':'Remove the four selected-country colored bottom edges and strengthen their text to weight 600; retain selected material fill.',
    'updated_nodes':8,'visually_inspected_selection_rails':4,
    'native_receipts':'paper_edge_correction_native.json.gz',
    'native_receipts_sha256':digest(R/'paper_edge_correction_native.json.gz'),
    'uncompressed_sha256':hashlib.sha256(raw).hexdigest(),
    'source_css_sha256':digest(W/'templates/intl_country_cockpit.css'),
    'scope_limit':'Selection styling readback and bounded visual inspection; independent complete-candidate review remains pending.'
})
tracker=W/'agentos/workstreams/WS-PAPER-INTERNATIONAL-WAVES.md'
t=tracker.read_text()
heading='## 2026-10-20 current-main integration and fresh visual evidence'
assert heading not in t
t += '\n'+heading+'\n\n'+(
    'The complete country policy, fiscal and currency source increment was committed and pushed as '
    '`ec1277e909ffed27f58f9f4b107b81f5985fb7b8` with native APPLIED commit and push receipts. '
    'The original historical uncertain push was separately reconciled NOT_APPLIED by its original owner; its native uncertainty receipt remains historical evidence.\n\n'
    'Current main `13e098071ab2799c41a170d21ad522f751dfb15a` is integrated through a proper two-parent merge. '
    'The three conflict resolutions preserve both CI path additions, the exact intended nine-asset Caddy delta per matcher, and the full current-main access-test module plus the original international test. '
    '327 integrated tests pass. Import closure has zero findings, no gated suites are unenrolled, and Caddy adaptation preserves every other semantic field.\n\n'
    'The current no-colored-container-edge doctrine is applied to four CSS selectors and the matching four Paper overview boards. '
    'The new integrated browser receipt records 84/84 country views, 12/12 complete keyboard-focus checks, 8/8 ageing controls, both history journeys, and zero page exceptions. '
    'The canonical capture records 12 anonymous theme/language/viewport states; its isolated missing live_config asset and blocked analytics response are retained as capture limitations. '
    'These previews do not prove served adoption.\n\n'
    'Review responsibility remains substantive and independent. Current protected law permits a genuinely needed native principal audit; no exclusive Opus or SessionBridge-only requirement has been established. '
    'The failed SessionBridge discovery does not waive review or invent a mandatory missing API. Earlier bounded principal advice is not complete-candidate acceptance. '
    'The integrated source still needs its current hosted CI and independent complete review, applicable holding-authority release, the normal render/updater path, and actual served verification.\n\n'
    'Evidence: `research/paper_international_wave1_wave2/publisher_reconciliation_20261020/` and '
    '`mockups/evidence/intl-integration-20261020/`. No Ready/merge-to-main, runtime restart, migration or watcher is implied.\n'
)
tracker.write_text(t)
paths=list(expected)+['templates/intl_country_cockpit.css',
    'agentos/workstreams/WS-PAPER-INTERNATIONAL-WAVES.md',
    'research/paper_international_wave1_wave2/publisher_reconciliation_20261020',
    'mockups/evidence/intl-integration-20261020']
subprocess.run(['git','add','--',*paths],cwd=W,check=True)
assert not git('ls-files','-u')
diff=pathlib.Path('/tmp/intl-integration-final-20261020.diff')
with diff.open('wb') as out:
    subprocess.run(['git','diff','--cached','--unified=0',MAIN],cwd=W,stdout=out,check=True)
commands={
 'design_system':[PY,'scripts/check_design_system.py','--mode','enforce-added','--diff-file',str(diff)],
 'runtime_style':[PY,'scripts/check_runtime_style_injection.py'],
 'visual_evidence':[PY,'scripts/check_ui_visual_evidence.py','--diff-file',str(diff)]
}
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
def run(item):
    key,cmd=item
    with (R/f'integration_{key}.log').open('w') as out:
        result=subprocess.run(cmd,cwd=W,stdout=out,stderr=subprocess.STDOUT)
    return key,{'command':cmd,'exit_code':result.returncode,'log':f'integration_{key}.log'}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    results=dict(pool.map(run,commands.items()))
write('integration_design_guards.json',{'schema':'mastermind.intl_integration_design_guards.v1','started_at':started,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_parent':SOURCE,'main_parent':MAIN,'diff_sha256':digest(diff),'results':results,'passed':all(v['exit_code']==0 for v in results.values())})
print(json.dumps({'guards':results,'passed':all(v['exit_code']==0 for v in results.values()),'source_css_sha256':digest(W/'templates/intl_country_cockpit.css'),'merge_conflicts_remaining':git('ls-files','-u')},ensure_ascii=False))
for key,result in results.items():
    if result['exit_code']:
        print(json.dumps({'failure':key,'tail':(R/result['log']).read_text().splitlines()[-24:]}))
raise SystemExit(0 if all(v['exit_code']==0 for v in results.values()) else 1)
