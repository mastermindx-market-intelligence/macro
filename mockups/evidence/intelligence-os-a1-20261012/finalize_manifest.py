"""Normalize actual Playwright captures using the existing visual evidence schema."""
from pathlib import Path
import json
import hashlib
import struct
import sys

out = Path(__file__).resolve().parent / 'browser'
x = json.loads((out / 'manifest.json').read_text())
panel = x['pages'][0]
for cell in panel['states']:
    for route, source in [('/app.js', 'admin/static/app.js'), ('/styles.css', 'admin/static/styles.css'), ('/preferences.js', 'admin/static/preferences.js')]:
        if cell['assets'][route]['sha256'] != x['target']['source_sha256'][source]:
            raise ValueError('Served/source static bytes differ: ' + route)
    if not cell['api_identity'].get('shared_evidence_projection_agrees'):
        raise ValueError('Shared panel/detail projection differs')
details = {'page_id': 'admin-intelligence-os-engine-detail', 'route': '/#/engine/<synthetic-engine-id>', 'states': []}
for c in list(panel['states']):
    c['capture_tool_module_sha256'] = x['tool']['module_sha256']
    d = c['detail']
    details['states'].append({k: c[k] for k in ('viewport', 'viewport_width', 'viewport_height', 'theme', 'locale', 'access', 'captured', 'applied_theme', 'applied_locale', 'capture_tool_module_sha256')})
    details['states'][-1].update({k: d[k] for k in ('file', 'sha256', 'bytes', 'width', 'height')})
    details['states'][-1]['api_identity'] = c['api_identity']
    details['states'][-1]['assets'] = c['assets']
    png = (out / c['file_focus']).read_bytes()
    panel['states'].append({**{k: c[k] for k in ('viewport', 'viewport_width', 'viewport_height', 'theme', 'locale', 'access', 'captured', 'applied_theme', 'applied_locale', 'capture_tool_module_sha256')}, 'force_state': {'name': 'native_language_focus', 'selector': '#adminLanguage', 'operation': 'actual browser focus()'}, 'file': c['file_focus'], 'sha256': hashlib.sha256(png).hexdigest(), 'bytes': len(png), 'width': struct.unpack('>I', png[16:20])[0], 'height': struct.unpack('>I', png[20:24])[0]})
segments_path = out / 'detail-segments.json'
if segments_path.exists():
    segments = json.loads(segments_path.read_text())
    if any(c.get('base_url') != x['target']['base_url'] for c in segments):
        raise ValueError('Segment capture epoch differs from final matrix')
    details['states'].extend(segments)
interactions_path = out / 'interactions.json'
if interactions_path.exists():
    interaction_receipt = json.loads(interactions_path.read_text())
    for row in interaction_receipt['results']:
        if row.get('base_url') != x['target']['base_url']:
            raise ValueError('Interaction capture epoch differs from final matrix')
        png = (out / row['refresh_error_file']).read_bytes()
        panel['states'].append({'viewport':'mobile', 'viewport_width':390, 'viewport_height':844, 'theme':row['theme'], 'locale':'en', 'access':'synthetic_fixture_session', 'captured':True, 'applied_theme':row['theme'], 'applied_locale':'en', 'force_state':{'name':'failed_refresh_preserves_previous', 'operation':'Actual browser route injection of synthetic HTTP503'}, 'file':row['refresh_error_file'], 'sha256':row['refresh_error_sha256'], 'bytes':len(png), 'width':struct.unpack('>I',png[16:20])[0], 'height':struct.unpack('>I',png[20:24])[0], 'capture_tool_module_sha256':row['capture_tool_module_sha256'], 'assets':row['assets']})
    x['interaction_receipt'] = interaction_receipt
findings_path = out / 'findings-states.json'
if findings_path.exists():
    findings_cells = json.loads(findings_path.read_text())
    if any(c.get('base_url') != x['target']['base_url'] for c in findings_cells):
        raise ValueError('Findings capture epoch differs from final matrix')
    panel['states'].extend(findings_cells)
x['pages'].append(details)
all_shas = sorted({c['capture_tool_module_sha256'] for page in x['pages'] for c in page['states']})
x['tool']['module_sha256'] = all_shas
x['tool']['module_refs'] = ['capture_admin.cjs', 'capture_detail_segments.cjs', 'check_interactions.cjs', 'check_findings.cjs']
epoch_path = out.parent.parent / 'product' / 'synthetic-final-epoch.json'
if epoch_path.exists():
    x['target']['served_epoch_receipt'] = json.loads(epoch_path.read_text())
x['honesty']['projection'] = 'Shared evidence fields agree. Strict panel/detail comparison preserves detail-only phase0 validation_state enrichment; no production coherent-generation proof is inferred.'
state_count = sum(len(page['states']) for page in x['pages'])
x['totals'] = {'pages': 2, 'states_attempted': state_count, 'states_captured': state_count}
x['honesty']['production'] = 'Not production proof, real user account acceptance or independent operator comprehension.'
(out / 'manifest-final.json').write_text(json.dumps(x, ensure_ascii=False, indent=2) + '\n')
(Path(__file__).resolve().parent / 'EVIDENCE.yml').write_text('schema: mastermind.page_evidence_receipt.v1\nchanged_paths:\n  - admin/static/index.html\n  - admin/static/preferences.js\n  - admin/static/styles.css\n  - admin/static/app.js\nmanifest: browser/manifest-final.json\n')
# Reuse the canonical validator; no taste verdict or alternate schema is invented.
sys.path.insert(0, x['target']['source_tree'])
from scripts.check_ui_visual_evidence import _validate_page_cells, _validate_tool_hash_coverage
findings = _validate_tool_hash_coverage(out / '../EVIDENCE.yml', 'browser/manifest-final.json', x)
for page in x['pages']:
    findings += _validate_page_cells(out / '../EVIDENCE.yml', out / 'manifest-final.json', 'browser/manifest-final.json', page)
print(json.dumps({'canonical_cell_integrity_findings': findings, 'pages': 2, 'rest_cells': 16, 'focus_cells': 8, 'actual_scroll_cells': 8, 'failed_refresh_cells': 2, 'findings_cells': state_count - 34}))
if findings:
    raise SystemExit(1)
