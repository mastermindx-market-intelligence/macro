"""Verify the single calendar delivery bridge using local bytes only.

The actual feed must already have been built by scripts.build_feeds. This command
never fetches, deploys, starts refresh jobs, alters vendoring or stages source.
Temporary copies model the existing Git/rsync/sparse-checkout paths; they do not
claim those paths have been deployed or that an entitled HTTP read succeeded.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from engine import treasury_auction_lifecycle as lifecycle


def sha(value):
    return hashlib.sha256(value).hexdigest()


def git(*args, cwd=ROOT, check=True):
    return subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True, check=check)


def verify(mastermind_root=None, source_commit=None):
    workflow = ROOT / '.github/workflows/daily.yml'
    text = workflow.read_text()
    obj = yaml.safe_load(text)
    base = yaml.safe_load(git('show', 'd2eec4732abee359ebb578b245fa7359b3c01a7d:.github/workflows/daily.yml').stdout)
    # PyYAML YAML 1.1 treats the unquoted GitHub 'on' key as True.
    assert obj.get('on', obj.get(True)) == base.get('on', base.get(True))
    matches = []
    for job, value in obj['jobs'].items():
        steps = value.get('steps', [])
        indices = [i for i, step in enumerate(steps) if step.get('name') == 'assemble machine-consumable feeds (site/feeds -> R2)']
        for index in indices:
            assert steps[index + 1]['name'] == 'commit engine outputs'
            assert steps[index]['if'] == 'always()'
            assert steps[index]['run'] == 'python -m scripts.build_feeds || echo "::warning::build_feeds failed (non-fatal)"'
            assert 'publish heavy per-ticker stores to R2' in steps[index + 2]['name']
            matches.append({'job': job, 'feed_index': index, 'commit_index': index + 1, 'r2_index': index + 2})
    assert len(matches) == 1
    assert len(workflow.read_bytes()) < 512 * 1024
    calendar = ROOT / 'site/feeds/event_calendar.json'
    raw = calendar.read_bytes()
    wrapper = json.loads(raw)
    context = wrapper['sovereign_auction_context']
    assert wrapper['horizon_days'] == 21 and context['coverage']['horizon_days'] == 30
    assert all(isinstance(wrapper[name], list) for name in ('us_macro', 'high_impact', 'commodity'))
    assert context['is_context_only'] is True and context['forecast_authority'] == 'RESEARCH_ONLY'
    assert context['probabilities'] is None and context['status'] == 'available'
    assert context == lifecycle.snapshot(ROOT / 'data', as_of=context['decision_cutoff_utc'], horizon_days=30)
    source = ROOT / 'research/sovereign_auction_pressure/source_audit/forward_capture_primary/treasury_auctions/observations'
    installed = ROOT / 'data/treasury_auctions/observations'
    receipts = []
    for path in sorted(source.glob('*.json')):
        target = installed / path.name
        assert path.read_bytes() == target.read_bytes()
        receipts.append({'path': str(target.relative_to(ROOT)), 'sha256': sha(target.read_bytes())})
    assert len(receipts) == 4
    source_sha = sha(raw)
    committed_sha = None
    if source_commit:
        committed = subprocess.check_output(['git', 'show', f'{source_commit}:site/feeds/event_calendar.json'], cwd=ROOT)
        assert committed == raw
        committed_sha = sha(committed)
    with tempfile.TemporaryDirectory(prefix='auction-publication-bridge-') as tmp:
        temp = Path(tmp)
        git('init', '-q', cwd=temp)
        shutil.copyfile(ROOT / '.gitignore', temp / '.gitignore')
        feeds = temp / 'site/feeds'; feeds.mkdir(parents=True)
        probes = ['event_calendar.json', 'risk_radar.json', '_manifest.json', 'nested/arbitrary.json']
        for name in probes:
            path = feeds / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('{}\n')
        ignored = {}
        for name in probes:
            result = git('check-ignore', '--quiet', f'site/feeds/{name}', cwd=temp, check=False)
            assert result.returncode in (0, 1)
            ignored[name] = result.returncode == 0
        assert ignored == {name: name != 'event_calendar.json' for name in probes}
        selected = git('add', '--dry-run', '--', 'site/', cwd=temp).stdout.strip().splitlines()
        assert selected == ["add 'site/feeds/event_calendar.json'"]
        served = temp / 'site.served/feeds/event_calendar.json'
        vendor = temp / 'vendor/macro/site/feeds/event_calendar.json'
        copies = {}
        for name, path in [('served_simulation', served), ('mastermind_input_simulation', vendor)]:
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(calendar, path)
            copies[name] = sha(path.read_bytes())
            assert copies[name] == source_sha
        consumer = None
        if mastermind_root:
            module_path = Path(mastermind_root) / 'brain/sovereign_auction_context.py'
            spec = importlib.util.spec_from_file_location('auction_bridge_mm_consumer', module_path)
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            now = datetime.now(timezone.utc)
            projected = module.read_context(vendor, now=now)
            assert projected['status'] == 'available'
            assert projected['source_observed_at'] == context['source_observed_at']
            assert projected == module.validate_context(context, now=now)
            assert len(projected['events']) == len(context['events'])
            consumer = {'reader_sha256': sha(module_path.read_bytes()), 'status': projected['status'], 'event_count': len(projected['events']), 'transport': 'explicit_temporary_input_path'}
    return {
        'schema': 'sovereign_auction_publication_bridge_verification_v1',
        'verified_at': datetime.now(timezone.utc).isoformat(),
        'source_head': git('rev-parse', 'HEAD').stdout.strip(), 'source_commit_checked': source_commit,
        'artifact': 'site/feeds/event_calendar.json', 'artifact_sha256': source_sha,
        'committed_artifact_sha256': committed_sha, **copies,
        'workflow_sha256': sha(workflow.read_bytes()), 'workflow_order': matches,
        'existing_schedule_unchanged': True, 'ignore_probe': ignored, 'dry_run_selected': selected,
        'receipt_sources': receipts, 'source_observed_at': context['source_observed_at'],
        'decision_cutoff_utc': context['decision_cutoff_utc'], 'event_count': len(context['events']),
        'legacy_array_counts': {name: len(wrapper[name]) for name in ('us_macro', 'high_impact', 'commodity')},
        'actual_snapshot_equals_published_context': True, 'mastermind_reader': consumer,
        'capture_schedule_started': False, 'production_deployed': False,
        'real_entitled_http_read_verified': False, 'existing_vendor_refresh_executed': False,
        'limitations': ['Temporary byte-copy proof is not deployment or runtime refresh acceptance.', 'Attended source capture only; no source freshness SLA or prospective statistical clock has started.'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mastermind-root', type=Path)
    parser.add_argument('--source-commit')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    receipt = verify(args.mastermind_root, args.source_commit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
