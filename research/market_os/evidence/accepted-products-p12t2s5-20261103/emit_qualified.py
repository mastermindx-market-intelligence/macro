"""Use existing native emitters with exact retained real inputs; no collection."""
from pathlib import Path
import datetime
import hashlib
import json
import socket
import sys

repo, evidence = map(Path, sys.argv[1:3])
sys.path.insert(0, str(repo))
transport_attempts = []
def deny(*args, **kwargs):
    transport_attempts.append('transport refused before connection')
    raise AssertionError('Network forbidden in accepted-products native emission')
socket.socket.connect = deny
socket.socket.connect_ex = deny
socket.create_connection = deny
socket.getaddrinfo = deny

from scripts import build_macro_suite_pages as macro
from scripts import build_fundamental_forensics as forensics
from lib import macro_suite_view

retained = evidence / 'retained'
inputs = json.loads((evidence / 'retained-inputs.json').read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

# Exact public projection is the complete input to render_shell, never private rows.
summary_source = retained / 'data/fundamental_forensics/public_summary.json'
summary_target = repo / 'data/fundamental_forensics/public_summary.json'
summary_target.parent.mkdir(parents=True, exist_ok=True)
if summary_target.exists():
    assert summary_target.read_bytes() == summary_source.read_bytes()
else:
    summary_target.write_bytes(summary_source.read_bytes())
assert sha(summary_target) == inputs['data/fundamental_forensics/public_summary.json']['sha256']
counts = forensics.read_public_summary(repo)
assert counts, 'Real public summary is not usable; refuse a substitute empty projection'
summary_as_of = forensics.public_summary_as_of(repo)
assert summary_as_of
forensics_page = forensics.render_shell(repo)
assert (repo / 'site/fundamental_forensics.js').read_bytes() == (repo / 'templates/fundamental_forensics.js').read_bytes()
assert sha(summary_target) == sha(summary_source)

# Only this workspace has a complete retained snapshot. Do not run render() for
# the other manifest-listed workspaces, or publish refusal output for absent inputs.
page = next(p for p in macro.SUITE_PAGES if p.workspace_id == 'business_activity')
data_root = retained / 'business-macrodata'
snapshot, artifact = macro.read_workspace(data_root, page)
owner_before = json.dumps(snapshot, sort_keys=True)
page_built_at = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
view = macro_suite_view.build_view(snapshot, page_built_at=page_built_at,
    artifact=artifact, layout=macro._layout_for(page.workspace_id))
assert view['ok'] and len(view['metrics']) == 31
business_page, ok, entry = macro.build_page(repo, page, data_root=data_root,
    out_dir=repo / 'site', env=macro._environment(repo), page_built_at=page_built_at)
assert ok and entry['snapshot'] == snapshot
assert json.dumps(snapshot, sort_keys=True) == owner_before
for rel in ['workspaces/manifest.json', 'workspaces/business_activity/US/latest.json']:
    key = 'mockups/evidence/business-activity-depth-20261103/retained/macrodata/' + rel
    assert sha(data_root / rel) == inputs[key]['sha256']

record = {
    'scope': 'Actual incumbent native emissions in the isolated owned repository; exact retained real public inputs; no data/producer recompute or private entitlement claim',
    'forensics': {
        'interface': 'scripts.build_fundamental_forensics.render_shell(root), including normal write_page and _atomic_copy',
        'input': 'data/fundamental_forensics/public_summary.json',
        'input_sha256': sha(summary_target), 'summary_as_of': summary_as_of,
        'public_counts': counts, 'private_rows_loaded': False,
        'output': str(forensics_page.relative_to(repo)), 'output_sha256': sha(forensics_page),
        'paired_js_exact_template': True,
        'limits': 'Public shell and assets only; compose_state/publish_private were not called. Current-entitled source click and native new unavailable-state presentation remain unqualified.',
    },
    'business_activity': {
        'interface': 'read_workspace/build_view/build_page with normal render_page/write_page and actual analyst mountability',
        'input_artifact': artifact, 'all_input_bytes_unchanged': True,
        'metric_count': len(view['metrics']), 'view_metric_sha256': hashlib.sha256(json.dumps(view['metrics'], sort_keys=True).encode()).hexdigest(),
        'owner_definition_versions': sorted({m['definition_version'] for m in view['metrics'] if m['definition_version']}),
        'definition_release_clocks_invented': False,
        'page_built_at': page_built_at, 'page_built_clock_is_not_observation': True,
        'actual_analyst_mountability': macro._macro_command_analyst(repo),
        'output': str(business_page.relative_to(repo)), 'output_sha256': sha(business_page),
        'limits': 'Retained published Business snapshot, not current economic truth, raw source legs, complete other-workspace input or native/served proof.',
    },
    'Bonds': {
        'state': 'SOURCE_ONLY_NORMAL_FULL_BUILD_NOT_RUN',
        'reason': 'Accepted seven-country owner observations and component snapshots are not a complete full-page inputs/fr/credit/compass/chart/alert bundle. main also rewrites data/bonds output. No missing input was substituted or broader producer/data write run.',
    },
    'ChinaHub': {
        'state': 'PENDING_EXACT_RENDERER_REPLAY_ONLY',
        'reason': 'Complete real published briefing+command are retained, but the upstream bus read set is not qualified. build() would recompute and rewrite briefing/digest; no upstream build is implied by renderer input availability.',
    },
    'network_attempts': transport_attempts,
    'browser': 'HELD; no launch or alternate after explicit child-sandbox refusal',
    'effects': 'No PR/push/hostedCI/host/provider/serving; owned site outputs only; no input bytes altered',
}
assert not transport_attempts
(evidence / 'native-emission-report.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(record, ensure_ascii=False, indent=2))
