#!/usr/bin/env python3
"""Render the real Alerts builder into a non-production directory for browser QA.

Run from the repository root after materializing the committed alert inputs.
No source polling, alert firing, notification dispatch or deployment occurs.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if out == ROOT or out == (ROOT / 'site').resolve() or (ROOT / 'site').resolve() in out.parents:
        parser.error('Use an isolated proof directory, never the production publication tree.')
    paths = ['data/regime/latest.json', 'data/alerts/alerts_log.parquet',
             'data/alerts/rule_scorecard.json', 'data/alerts/watchlist_alerts.jsonl',
             'data/spine/predictions.parquet']
    paths += [f'data/{name}/alerts.jsonl' for name in
              ('bonds', 'forex', 'vector', 'commodity', 'themes', 'emergence',
               'altdata', 'demand_chain', 'subsector_rotation')]
    paths.append('data/oracle/oracle_alerts.jsonl')
    source_paths = ['engine/alert_triage.py', 'engine/alert_center_view.py',
        'engine/alert_time.py', 'scripts/build_site.py', 'scripts/prove_alert_center_v2.py',
        'templates/alerts.html.j2', 'templates/alert_center.css', 'templates/alert_center.js',
        'templates/theme.css', 'templates/_site_nav.html.j2', 'templates/_navlinks.html.j2',
        'engine/i18n.py', 'lib/site_assets.py', 'scripts/build_live_overlay.py',
        'templates/live.js', 'templates/nav_market.js']
    def fingerprints(names):
        return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                if (ROOT / name).is_file() else None for name in names}
    source_before = fingerprints(source_paths)
    inputs_before = fingerprints(paths)
    from jinja2 import Environment, FileSystemLoader
    from engine import i18n
    from scripts.build_site import build_alerts_page
    out.mkdir(parents=True, exist_ok=True)
    env = Environment(loader=FileSystemLoader(ROOT / 'templates'), autoescape=True)
    env.globals.update(td=i18n.td, tr=i18n.tr, t_pctile=i18n.t_pctile, zip=zip)
    env.filters['min'] = min
    generated = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')
    build_alerts_page(env, out, generated)
    from lib.site_assets import copy_asset
    for name in ('theme.css', 'theme.js', 'navigation-refresh.css', 'product-nav-icons.css',
                 'dashboard-icons.css', 'dashboard-icons.js', 'account.js', 'mm_brain.js',
                 'logo_config.js', 'stock-logos.js', 'auth.js', 'watchstore.js',
                 'live.js', 'nav_market.js'):
        if (ROOT / 'templates' / name).is_file():
            copy_asset(name, ROOT / 'templates' / name, out)
    from scripts.build_live_overlay import write_live_config
    write_live_config(out)
    if (ROOT / 'templates/fonts').is_dir():
        shutil.copytree(ROOT / 'templates/fonts', out / 'fonts', dirs_exist_ok=True)
    payload = json.loads((out / 'factordata/alerts_triage.json').read_text())
    manifest = {'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'generated_utc': generated, 'proof_kind': 'local_real_builder_committed_inputs',
                'production_acceptance': False, 'inputs': []}
    for name in paths:
        p = ROOT / name
        manifest['inputs'].append({'path': name, 'present': p.exists(),
            'sha256': hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None})
    manifest['candidate_sources'] = source_before
    manifest['source_commit_note'] = ('HEAD identifies ancestry; candidate_sources binds the executed '
        'working-tree bytes. The named set is not a transitive dependency attestation.')
    manifest['sources_unchanged_during_build'] = source_before == fingerprints(source_paths)
    manifest['inputs_unchanged_during_build'] = inputs_before == fingerprints(paths)
    manifest['outputs'] = {name: hashlib.sha256((out / name).read_bytes()).hexdigest()
        for name in ['alerts.html', 'factordata/alerts_triage.json', 'alertsdata/feed.json']}
    manifest['populations'] = {'legacy_ranked': len(payload['alerts']),
        'shared_signals': payload['explorer']['total_signals'],
        'specific_subject_bundles': len(payload['explorer']['situations']),
        'published_firings': len(payload['explorer']['history']),
        'total_matched_firings': payload['explorer']['history_total']}
    (out / 'input-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    if not (manifest['sources_unchanged_during_build'] and manifest['inputs_unchanged_during_build']):
        raise RuntimeError('Proof inputs or source changed during rendering; do not use this result')
    print(json.dumps(manifest['populations'], indent=2))
    print('OUTPUT', out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
