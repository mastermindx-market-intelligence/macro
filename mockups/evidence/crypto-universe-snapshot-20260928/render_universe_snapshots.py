"""Controlled Market Board render using the real builder; no collector writes."""
from pathlib import Path
import argparse, copy, hashlib, json, shutil, subprocess, sys
from datetime import datetime, timezone
from jinja2 import ChoiceLoader, DictLoader

parser = argparse.ArgumentParser()
parser.add_argument('--repo', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--combined-template', type=Path, required=True)
args = parser.parse_args()
repo = args.repo.resolve(); out = args.output.resolve()
if out == repo / 'site':
    raise SystemExit('Evidence may not overwrite the production site')
out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(repo))
from engine.crypto_universe import load_universe_snapshot
from scripts import build_crypto
from lib import config

def input_hashes():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((config.data_dir() / 'crypto_universe').glob('market_*.parquet'))}

before = input_hashes()
snapshot = load_universe_snapshot(50)
original_loader = build_crypto.load_universe_snapshot
original_environment = build_crypto.Environment
combined = args.combined_template.read_text()
receipts = []
try:
    for mode in ('stored', 'empty', 'returns-missing', 'combined'):
        fixture = copy.deepcopy(snapshot)
        if mode == 'empty':
            fixture.update(as_of=None, rows=[], excluded=[{
                'file': 'controlled-unavailable', 'symbol': '', 'id': None,
                'source': None, 'as_of': None, 'reason': 'UNREADABLE_HISTORY'}])
        elif mode == 'returns-missing':
            for row in fixture['rows']:
                row.update(change_30d=None, change_7d=None, state='Building', tone='neutral')
        build_crypto.load_universe_snapshot = lambda *a, current=fixture, **k: copy.deepcopy(current)
        if mode == 'combined':
            def environment(*a, **k):
                env = original_environment(*a, **k)
                env.loader = ChoiceLoader([DictLoader({'crypto.html.j2': combined}), env.loader])
                return env
            build_crypto.Environment = environment
        else:
            build_crypto.Environment = original_environment
        work = out / ('_work_' + mode)
        work.mkdir(exist_ok=True)
        page = build_crypto.build(work)
        destination = out / ('crypto-' + mode + '.html')
        shutil.copy2(page, destination)
        state = json.loads((work / 'crypto_class_state.json').read_text())
        receipts.append({'mode': mode, 'file': destination.name,
            'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
            'snapshot_as_of': fixture['as_of'], 'listed': len(fixture['rows']),
            'universe_coverage': state['universe_coverage']})
finally:
    build_crypto.load_universe_snapshot = original_loader
    build_crypto.Environment = original_environment

# Canonical repository assets, including the fonts missing from earlier fixtures.
assets = ['theme.css', 'illus.css', 'illus.js', 'theme.js', 'mm_brain.js',
          'navigation-refresh.css', 'logo_config.js', 'stock-logos.js', 'live_config.js',
          'live.js', 'product-nav-icons.css', 'account.js', 'terminal_overlay.js']
for name in assets:
    candidates = [repo / 'templates' / name, repo / 'site' / name]
    source = next((p for p in candidates if p.exists()), None)
    if source:
        shutil.copy2(source, out / name)
fonts = out / 'fonts'; fonts.mkdir(exist_ok=True)
for source in (repo / 'templates' / 'fonts').glob('*.woff2'):
    shutil.copy2(source, fonts / source.name)
assert before == input_hashes(), 'Source snapshot changed during evidence generation'
report = {'fixture_status': 'controlled_generated_pages_not_production',
          'created_at': datetime.now(timezone.utc).isoformat(),
          'source_head': subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip(),
          'source_sha256': {p: hashlib.sha256((repo / p).read_bytes()).hexdigest() for p in
              ['engine/crypto_universe.py', 'scripts/build_crypto.py', 'templates/crypto.html.j2']},
          'combined_template_sha256': hashlib.sha256(combined.encode()).hexdigest(),
          'input_sha256': before, 'inputs_unchanged': True, 'routes': receipts,
          'local_font_files': len(list(fonts.glob('*.woff2')))}
(out / 'scenario_receipts.json').write_text(json.dumps(report, indent=2, ensure_ascii=False))
print(json.dumps({'source_head': report['source_head'], 'routes': len(receipts),
                  'source_assets_unchanged': True, 'fonts': report['local_font_files'],
                  'listed': [(r['mode'], r['listed']) for r in receipts]}, indent=2), flush=True)
