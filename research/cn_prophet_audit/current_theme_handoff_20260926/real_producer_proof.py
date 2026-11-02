"""Actual China producer on immutable Git inputs; not investment or live proof."""
from pathlib import Path
from datetime import datetime, timezone
from copy import deepcopy
from unittest.mock import patch
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import types

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from lib import config
from engine import theme_scoring
from scripts import build_china

SOURCE = '978a5209eb0710d87a2d750982ae907c735fdf27'
CONSUMERS = {'mature': '9c8ff7315347eb8b6d00875603c55b1bd63ad8b5',
             'emerging': '0fab873d85decf6ce72d08e9d4df6b7668e5626f'}
SNAPSHOTS = [('2026-09-23', 'bf93a8dbd5f245444ef7b4286d1b5f4bd1aa356f'),
             ('2026-09-24', '4f2d6fdeb0ad2a8df1dc55a604297da4e8d61070')]
INPUTS = ['config.yml', 'data/china/000001.SS.parquet', 'data/china_search/closes.parquet',
          'data/baskets_china/membership.json', 'data/china/510300.SS.parquet',
          'data/china_regime/latest.json', 'data/forex/latest.json',
          'data/vol_regime/basket_overlay_gate.json', 'data/regime/latest.json',
          'data/strategies/baskets_calibration.json', 'data/earnings/earnings.parquet',
          'site/sectordata/sector_central.json', 'site/vol/regime.json',
          'site/chinabasketdata/baskets.json', 'data/breadth_divergence/forward_log.parquet']
SOURCE_PATHS = ['scripts/build_china.py', 'engine/theme_scoring.py',
                'engine/narrative_rotation.py', 'engine/baskets_china.py',
                'engine/group_flow.py', 'engine/vol_regime.py',
                'engine/basket_breadth_divergence.py', 'lib/closes_panel.py',
                'lib/cn_calendar.py', 'lib/config.py', 'lib/store.py', 'config.yml']

def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], timeout=90)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

for rel in SOURCE_PATHS:
    assert (ROOT / rel).read_bytes() == git('show', f'{SOURCE}:{rel}'), rel
modules = {}
for label, rev in CONSUMERS.items():
    assert git('show', f'{rev}:lib/cn_calendar.py') == (ROOT / 'lib/cn_calendar.py').read_bytes()
    mod = types.ModuleType('proof_consumer_' + label)
    mod.__file__ = str(ROOT / 'engine/china_act_now.py')
    exec(compile(git('show', f'{rev}:engine/china_act_now.py'), mod.__file__, 'exec'), mod.__dict__)
    modules[label] = mod
audit_state = {'active': False, 'root': None, 'writes': [], 'network_attempts': []}
def audit(event, args):
    if not audit_state['active']:
        return
    if event in ('socket.connect', 'socket.getaddrinfo'):
        audit_state['network_attempts'].append(event)
        raise RuntimeError('network forbidden during recorded-input compute')
    writing = (event == 'open' and isinstance(args[0], (str, bytes, os.PathLike))
               and ((isinstance(args[1], str) and any(c in args[1] for c in 'wax+'))
                    or isinstance(args[2], int) and args[2] & (os.O_WRONLY | os.O_RDWR)))
    if writing or event in ('os.mkdir', 'os.remove', 'os.rename'):
        p = Path(os.fsdecode(args[0])).resolve()
        if not p.is_relative_to(audit_state['root']):
            raise RuntimeError(f'proof refused write outside isolated input root: {p.name}')
        audit_state['writes'].append({'event': event, 'path': str(p.relative_to(audit_state['root']))})
    if event == 'os.rename':
        dest = Path(os.fsdecode(args[1])).resolve()
        if not dest.is_relative_to(audit_state['root']):
            raise RuntimeError('proof refused rename destination outside isolated input root')
    if event == 'subprocess.Popen':
        raise RuntimeError('child process forbidden during compute')
sys.addaudithook(audit)
report = {'source': SOURCE, 'consumers': CONSUMERS,
          'proof_kind': 'current code on immutable recorded inputs; not point-in-time or live proof',
          'observed_at_utc': datetime.now(timezone.utc).isoformat(),
          'source_sha256': {p: sha((ROOT / p).read_bytes()) for p in SOURCE_PATHS},
          'cases': [], 'all_passed': False,
          'limits': ['Assembler qualification clock is injected, not historical availability.',
                     'Producer date.today checks use execution date; no historical-return claim.',
                     'No live data, trade, ranking or publication authority.']}
INPUTS += ['site/chinabasketdata/act_now_cn.json', 'data/china_sector_cycles/forward_log.parquet']
if '--snapshot' not in sys.argv:
    raise SystemExit('Use --snapshot YYYY-MM-DD: one fresh Python process per immutable snapshot.')
selected_day = sys.argv[sys.argv.index('--snapshot') + 1]
SNAPSHOTS = [x for x in SNAPSHOTS if x[0] == selected_day]
assert len(SNAPSHOTS) == 1
for day, rev in SNAPSHOTS:
    print('CAPTURE', day, rev, flush=True)
    with tempfile.TemporaryDirectory(prefix='producer-input-', dir=OUT) as tmp:
        root = Path(tmp).resolve()
        inventory = {}
        mem = json.loads(git('show', rev + ':data/baskets_china/membership.json'))
        tickers = {m['ticker'] for b in mem['baskets'].values() for m in b.get('members', [])}
        prefixes = ('data/baskets/ohlcv', 'data/stocks', 'data/china_stocks', 'data/yahoo')
        wanted = {f'{pre}/{ticker}.parquet' for pre in prefixes for ticker in tickers}
        entries = {line.split('\t', 1)[1]: line for line in
                   git('ls-tree', '-r', rev, '--', *prefixes, *INPUTS).decode().splitlines()}
        member_paths = sorted(wanted & entries.keys())
        assert member_paths, 'missing real constituent OHLCV'
        for rel in INPUTS + member_paths:
            entry = entries.get(rel, '')
            if not entry:
                inventory[rel] = {'absent_in_snapshot': True}
                continue
            blob = entry.split()[2]
            raw = git('cat-file', 'blob', blob)
            dest = root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
            inventory[rel] = {'git_blob': blob, 'sha256': sha(raw), 'bytes': len(raw)}
        assert (root / 'config.yml').read_bytes() == (ROOT / 'config.yml').read_bytes()
        assert (root / 'data/china/000001.SS.parquet').is_file(), 'missing canonical CN session anchor'
        persisted = root / 'site/chinabasketdata/baskets.json'
        original = json.loads(persisted.read_text())['theme_intel']
        assert original['as_of'] == day
        before = {str(p.relative_to(root)): sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}
        produced = []
        real_compute = theme_scoring.compute_theme_intel
        def observed_compute(region):
            result = real_compute(region)
            produced.append(result)
            return result
        audit_state.update(active=True, root=root, writes=[], network_attempts=[])
        try:
            with patch.object(config, 'ROOT', root):
                with patch.object(theme_scoring, 'compute_theme_intel', side_effect=observed_compute) as producer:
                    intel = build_china._theme_intel_for_act_now(persisted, refresh=True)
                    assert producer.call_count == 1
        finally:
            audit_state['active'] = False
        assert len(produced) == 1 and intel is produced[0], 'caller fell back instead of real producer'
        assert isinstance(intel, dict) and intel.get('themes'), 'producer unavailable'
        assert intel['as_of'] == day
        assert all(t.get('mtf') is not None for t in intel['themes']), 'incomplete native MTF computation'
        assert not audit_state['network_attempts']
        after = {str(p.relative_to(root)): sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}
        changed = sorted(p for p in set(before) | set(after) if before.get(p) != after.get(p))
        assert set(changed) <= {'data/breadth_divergence/forward_log.parquet'}, changed
        case = {'day': day, 'input_commit': rev, 'input_inventory': inventory,
                'native_member_files': len(member_paths), 'configured_unique_members': len(tickers),
                'theme_count': len(intel['themes']), 'recorded_theme_count': len(original['themes']),
                'producer_file_changes_inside_temporary_root': changed,
                'producer_write_attempts_inside_temporary_root': audit_state['writes'],
                'network_attempts': audit_state['network_attempts'], 'consumers': {}}
        sf = root / 'site/chinabasketdata/act_now_cn.json'
        sectors = list(json.loads(sf.read_text())['sectors_by_ticker'].values()) if sf.exists() else []
        cycle_path = root / 'data/china_sector_cycles/forward_log.parquet'
        cycle = modules['emerging'].load_cycle_rows(str(cycle_path)) if cycle_path.exists() else None
        names = modules['emerging'].load_member_names(str(persisted))
        clock = datetime.fromisoformat(day + 'T10:00:00+00:00')
        pristine = deepcopy(intel)
        raw_lanes = None
        for label, mod in modules.items():
            board = mod.assemble_act_now(sectors, intel, cycle, member_names=names, observed_at=clock)
            assert intel == pristine
            assert all(row.get('theme_decision', {}).get('stock_entry_permission') is not True
                       for rows in board['display_lanes'].values() for row in rows)
            if raw_lanes is not None:
                assert board['lanes'] == raw_lanes
            raw_lanes = board['lanes']
            rows_by_id = {r['id']: {'lane': lane, 'reco': r.get('reco'),
                                    'route': r.get('entry_route'),
                                    'decision': r.get('theme_decision')}
                          for lane, rows in board['display_lanes'].items() for r in rows}
            case['consumers'][label] = {k: rows_by_id.get(k) for k in ('cn_semis', 'cn_ai_compute')}
            case['consumers'][label]['theme_availability'] = board.get('theme_availability')
            case['consumers'][label]['sector_count'] = len(sectors)
            case['consumers'][label]['cycle_count'] = len(cycle or [])
        th = {t['id']: t for t in intel['themes']}
        old = {t['id']: t for t in original['themes']}
        case['themes'] = {}
        for tid in ('cn_semis', 'cn_ai_compute'):
            t = th.get(tid, {})
            case['themes'][tid] = {k: t.get(k) for k in ('score', 'label', 'reco', 'observation', 'accel_z', 'ext_abs', 'components', 'mtf', 'tape', 'perf')}
            case['themes'][tid]['clean_entry'] = t.get('textures', {}).get('clean_entry')
            case['themes'][tid]['recorded'] = {k: old.get(tid, {}).get(k) for k in ('score', 'label', 'reco')}
            assert t.get('mtf', {}).get('source') == 'member_ohlcv', tid
            assert (t['label'], t['reco']) == (old[tid]['label'], old[tid]['reco']), (day, tid, t['label'], t['reco'])
            actual = case['consumers']['emerging'][tid]
            assert actual is not None, (day, tid)
            expected_lane = 'buy_now' if day == '2026-09-23' else 'reduce_avoid'
            assert actual['lane'] == expected_lane, (day, tid, actual)
            if expected_lane == 'buy_now':
                assert actual['route'] == 'theme_enter', (day, tid)
        report['cases'].append(case)
        print('CASE', day, json.dumps(case['consumers'], ensure_ascii=False), flush=True)
for p, digest in report['source_sha256'].items():
    assert sha((ROOT / p).read_bytes()) == digest, p
report['all_passed'] = True
out = OUT / f'real_producer_proof_{selected_day}.json'
out.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
print('RESULT', len(report['cases']), 'recorded snapshots;', len(CONSUMERS),
      'real consumers each; receipt_sha256', sha(out.read_bytes()), flush=True)
