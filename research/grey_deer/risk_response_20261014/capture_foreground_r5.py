"""Capture the R5 candidate with the existing canonical browser evidence tool.

The data is an explicitly synthetic partial-warning fixture, not a production
observation. Render the real Macro template, keep its styles and real dialog
runtime, and remove unrelated network consumers. The canonical capture tool owns
all manifest cells, image hashes, theme/locale checks and interaction captures.
No credentials, market writes, policy changes, or hand-authored capture receipts.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
OUT = ROOT / 'mockups/evidence/macro-risk-response-r5-20261015'


def main() -> int:
    from scripts import capture_page_evidence as capture
    from tests.test_risk_envelope_radar_integration import source_envelope, _foreground_render

    if (OUT / 'manifest.json').exists():
        raise RuntimeError('An original R5 manifest already exists; inspect it before recapturing.')
    fixture = source_envelope()
    fixture['source_session'] = '2026-10-14'
    fixture['market'] = 'US'
    fixture['measured_state'].update(verdict='MIXED', score=50, as_of='2026-10-14')
    fixture['hazard_summary'].update(stage=None, stage_reason='required_coverage_unavailable')
    for source in fixture['provenance']['sources']:
        source['as_of'] = '2026-10-14'
    fixture['provenance']['sources'][1]['coverage'] = 'MISSING'
    rendered = _foreground_render(fixture)
    rendered = re.sub(r'<script\b([^>]*)>(.*?)</script>',
                      lambda match: match.group(0) if ('type="application/json"' in match[1]
                      or 'window.mx5OpenDlg = function' in match[2]) else '',
                      rendered, flags=re.S | re.I)
    # Match the production permanent grid view without running unrelated scripts.
    def body_classes(match: re.Match[str]) -> str:
        attrs = match[1]
        cls = re.search(r'\bclass="([^"]*)"', attrs)
        values = (cls[1].split() if cls else [])
        values += [value for value in ('page-macro', 'mx4-grid') if value not in values]
        replacement = 'class="' + ' '.join(values) + '"'
        attrs = attrs[:cls.start()] + replacement + attrs[cls.end():] if cls else attrs + ' ' + replacement
        return '<body' + attrs + '>'
    rendered, count = re.subn(r'<body\b([^>]*)>', body_classes, rendered, count=1)
    assert count == 1
    site = OUT / 'fixture'
    site.mkdir(parents=True, exist_ok=True)
    (site / 'macro.html').write_text(rendered, encoding='utf-8')
    for name in ('theme.css', 'tier_preview.css', 'navigation-refresh.css'):
        (site / name).write_bytes((ROOT / 'templates' / name).read_bytes())
    source_paths = ('templates/dashboard.html.j2', 'templates/_risk_envelope_band.html.j2',
                    'templates/_risk_envelope_band.css.j2', 'templates/risk_envelope_live.js',
                    'site/risk_envelope_live.js')
    provenance = {'kind': 'synthetic_candidate_template_fixture', 'production': False,
                  'network_consumers_removed': True, 'credentials': False,
                  'fixture_sha256': hashlib.sha256(rendered.encode()).hexdigest(),
                  'source_sha256': {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                                    for path in source_paths}}
    (OUT / 'fixture-provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    return capture.main([
        '--site-dir', str(site), '--routes', 'macro.html', '--max-pages', '1',
        '--output-dir', str(OUT / 'evidence'), '--manifest', str(OUT / 'manifest.json'),
        '--smells', str(OUT / 'smells.json'), '--emit-md', str(OUT / 'capture.md'),
        '--themes', 'dark,light', '--locales', 'en,zh', '--viewports', 'desktop,mobile',
        '--settle-ms', '150', '--timeout-s', '25',
        '--force-state', 'risk-details-hover:hover(#risk-response-summary .rr-open)',
        '--force-state', 'risk-details-focus:focus(#risk-response-summary .rr-open)',
    ])


if __name__ == '__main__':
    raise SystemExit(main())
