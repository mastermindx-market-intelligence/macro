#!/usr/bin/env python3
"""Reclaim FINISHED macro session worktrees that live on the external SSD.

    ssd_worktree_reaper.py [--apply] [--dry-run] [--min-age-days N] [--max-remove N] [--json]

Why this exists (2026-09-14): the host storage helper (worktree_storage.py) plants
every session worktree under the policy root and LOCKS it with the reason
"mastermind-external-storage: removable volume protection" so an unplugged SSD
can never make `git worktree prune` drop the registration. The macro fleet GC
(scripts/worktree_gc.py) treats ANY lock as an operator hold and its roots are
repo-relative, so the 250+ trees on the SSD are never reclaimed: the volume was
at 81 % and the helper refuses new worktrees below its free-space floor — at
which point sessions cannot start at all (no internal fallback, by law).

What it does: imports the macro GC's own verdict ladder (classify / proc scan /
gh PR states / fetch) and runs it over the SSD-registered worktrees of the macro
clone with ONLY the storage-helper lock made transparent. Every other lock reason
stays LOCKED. SAFE_MERGED / SAFE_REMOTE trees (content provably on origin, older
than min_age_days, clean, no process inside) are unlocked, removed, their
`claude/ssd-*` branch deleted when merged, and the helper's receipt retired so the
same name can be minted again. Report-only unless --apply; --apply requires the
macro config's `armed: true` (operator ratification 2026-08-13).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
import ssd_retire_guard as guard

HERE = Path(__file__).resolve().parent
POLICY = Path.home() / '.config/mastermind/worktree-storage.json'
# The GC module is imported from a macro checkout. Hardcoding the Studio's primary
# made this tool DEAD on m1, where that path does not exist: the launchd job exited 1
# on every scheduled run since install (2026-09-23) with FileNotFoundError, so m1's
# SSD was never reaped while its agent reported as installed and loaded. Search the
# known checkout shapes instead and take the first that actually carries the tool.
_CANDIDATES = [
    Path.home() / 'Documents/Cluade/Macro Dashboard',
    Path.home() / 'Documents/GitHub/macro',
    Path.home() / 'Documents/Cluade/macro-main',
]


def _find_primary() -> Path:
    env = os.environ.get('MACRO_PRIMARY')
    if env and (Path(env) / 'scripts/worktree_gc.py').is_file():
        return Path(env)
    for c in _CANDIDATES:
        if (c / 'scripts/worktree_gc.py').is_file():
            return c
    # Fail loudly and namefully rather than raising a bare FileNotFoundError on a path
    # the operator never configured.
    raise SystemExit('ssd_worktree_reaper: no macro checkout carrying scripts/worktree_gc.py '
                     'among ' + ', '.join(str(c) for c in _CANDIDATES) + ' (set MACRO_PRIMARY)')


PRIMARY = _find_primary()
STATE_DIR = Path.home() / '.local/state/mastermind/storage-cleanup'
STORAGE_LOCK_REASON = 'mastermind-external-storage: removable volume protection'


def load_gc(primary: Path):
    # Protected release: do not import an old, parked, possibly unprotected checkout.
    mod, config = guard.load_pinned_gc()
    return mod, config


def git(repo: Path, *args, timeout=600) -> subprocess.CompletedProcess:
    return subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], capture_output=True, text=True, timeout=timeout)


def other_repo_coverage(members: list[dict]) -> dict:
    """Read-only cross-repo census; never classify or delete other repos."""
    sources = {
        'terminal': Path.home() / 'Documents/Cluade/charting-app',
        'mastermind': Path.home() / 'Documents/GitHub/Mastermind',
    }
    report = {}
    for name, source in sources.items():
        if not source.is_dir():
            report[name] = {'state': 'SOURCE_UNAVAILABLE'}
            continue
        try:
            probe = git(source, 'worktree', 'list', '--porcelain', timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            report[name] = {'state': 'CENSUS_UNAVAILABLE'}
            continue
        if probe.returncode:
            report[name] = {'state': 'CENSUS_FAILED', 'rc': probe.returncode}
            continue
        paths = [line[9:] for line in probe.stdout.splitlines()
                 if line.startswith('worktree ')]
        counts = {}
        for member in members:
            root = str(Path(member['root']))
            counts[member['mount_point']] = sum(
                path.startswith(root + os.sep) for path in paths
            )
        report[name] = {
            'state': 'READ_ONLY',
            'registered_total': len(paths),
            'under_verified_pool_by_volume': counts,
            'gc_proven_safe': False,
        }
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--dry-run', action='store_true', help='with --apply: log actions without removing')
    ap.add_argument('--primary', type=Path, default=PRIMARY)
    ap.add_argument('--min-age-days', type=float, default=None)
    ap.add_argument('--max-remove', type=int, default=None)
    ap.add_argument('--no-sizes', action='store_true')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--receipts', type=Path, default=None)
    args = ap.parse_args()

    pol = json.loads(POLICY.read_text())
    all_members = [pol] + pol.get('overflow_volumes', [])
    available_members, unavailable_members = [], {}
    if pol.get('overflow_volumes'):
        # A missing original disk must never prevent reclamation on the new one.
        # Validate each UUID before touching any registered path on that disk.
        sys.path.insert(0, str(Path.home() / '.local/lib/mastermind/worktree-storage'))
        try:
            from worktree_storage import check_storage
        except ImportError:
            print(json.dumps({'fatal': 'pool worktree validator unavailable'})); return 2
        for member in all_members:
            try:
                check_storage(member, check_space=False)
                available_members.append(member)
            except (OSError, RuntimeError, KeyError, TypeError, ValueError) as exc:
                unavailable_members[member['mount_point']] = str(exc)[:140]
    else:
        # Leave legacy single-volume behavior intact on M1.
        mount = Path(pol['mount_point'])
        if os.path.ismount(mount):
            available_members.append(pol)
        else:
            unavailable_members[str(mount)] = 'not mounted'
    if not available_members:
        print(json.dumps({'fatal': 'no qualified external SSD available',
                          'unavailable_members': unavailable_members})); return 2
    mount, root = Path(available_members[0]['mount_point']), Path(available_members[0]['root'])
    managed_roots = [Path(member['root']) for member in available_members]
    primary = args.primary.resolve()
    try:
        gc, cfg = load_gc(primary)
    except Exception as exc:
        print(json.dumps({'fatal': 'canonical GC pin unavailable', 'error': str(exc)[:220]}))
        return 2
    if args.min_age_days is not None:
        if args.min_age_days < float(cfg['min_age_days']):
            print(json.dumps({'fatal': 'retention override below ratified policy'}))
            return 2
        cfg['min_age_days'] = args.min_age_days
    # The host-local reaper is an adapter, not an alternate policy authority.
    protected = gc.human_driven_protection([primary], cfg)
    # Manual checkouts may be resumable by a human despite having no process.
    protected.extend(r / "manual" for r in managed_roots)
    if not guard.REQUIRED_HUMAN_ROOTS.issubset(set(map(str, protected))):
        print(json.dumps({'fatal': 'human-driven protection missing'}))
        return 2
    if args.apply and not args.dry_run and guard.unresolved_effects():
        print(json.dumps({'fatal': 'unreconciled prior SSD deletion effect'}))
        return 3
    cap = args.max_remove if args.max_remove is not None else int(cfg.get('max_delete_per_run', 200))

    rc = git(primary, 'worktree', 'list', '--porcelain')
    if rc.returncode:
        print(json.dumps({'fatal': 'worktree list failed', 'stderr': rc.stderr[-300:]})); return 2
    registered = gc.parse_worktree_list(rc.stdout)
    # scope = the helper's managed client roots under the policy root, matched on the
    # REGISTERED path (no symlink resolution): worktrees that merely resolve onto the
    # SSD because their parent estate was offloaded (~/.mastermind/sol-runs/... ->
    # Offloaded/...) are evidence, not session churn, and stay out of scope
    client_roots = [r / c for r in managed_roots for c in ('claude', 'codex', 'manual')]
    on_ssd = [w for w in registered if any(str(w.path).startswith(str(c) + '/') for c in client_roots)]
    roots = sorted({w.path.parent for w in on_ssd})
    transparent = 0
    for w in on_ssd:
        if w.locked and (w.lock_reason or '') == STORAGE_LOCK_REASON:
            w.locked, transparent = False, transparent + 1  # the helper's own lock, not an operator hold

    now = time.time()
    fetch_ok = gc.fetch_origin(primary)
    pr_states = gc.gh_pr_states(primary, int(cfg['pr_limit']))
    procs = gc.proc_cwd_map(roots)
    self_cwd = Path.cwd()
    for w in on_ssd:
        gc.classify(w, primary, cfg, procs, pr_states, fetch_ok, self_cwd, now, protected=protected)
    safe = [w for w in on_ssd if w.verdict in gc.SAFE_VERDICTS]
    if not args.no_sizes:
        for w in safe:
            try:
                w.size_kb = gc.du_kb(w.path)
            except Exception:  # noqa: BLE001
                w.size_kb = None
    counts: dict[str, int] = {}
    for w in on_ssd:
        counts[w.verdict] = counts.get(w.verdict, 0) + 1
    report = {
        'time': now, 'primary': str(primary), 'mount': str(mount),
        'verified_mounts': [m['mount_point'] for m in available_members],
        'unavailable_mounts': unavailable_members,
        'registered_total': len(registered),
        'on_ssd': len(on_ssd), 'storage_locks_made_transparent': transparent, 'fetch_ok': fetch_ok,
        'pr_states': None if pr_states is None else len(pr_states), 'proc_scan': procs is not None,
        'other_repo_coverage': other_repo_coverage(available_members),
        'verdicts': counts, 'safe': len(safe), 'safe_kb': sum(w.size_kb or 0 for w in safe),
        'min_age_days': cfg['min_age_days'], 'armed': bool(cfg.get('armed')), 'applied': False,
        'source_pin': guard.PINNED_COMMIT, 'human_roots_protected': list(map(str, protected)),
        'branch_deletion': 'DISABLED_FOR_SSD_REAPER', 'removal_mode': 'git_nonforce_only',
    }
    rows = [{'path': str(w.path), 'branch': w.branch, 'head': w.head, 'verdict': w.verdict, 'proof': w.proof,
             'reasons': w.reasons, 'age_days': w.age_days, 'size_kb': w.size_kb, 'lock_reason': w.lock_reason}
            for w in on_ssd]

    actions = []
    if args.apply:
        if not cfg.get('armed'):
            print(json.dumps({'refused': 'macro worktree_gc.json is not armed'})); return 2
        if procs is None:
            print(json.dumps({'refused': 'process scan unavailable'})); return 2
        receipts = {}
        for receipts_dir in [r / '.storage-receipts' for r in managed_roots]:
            if not receipts_dir.is_dir():
                continue
            for r in receipts_dir.glob('*.json'):
                try:
                    receipts[json.loads(r.read_text()).get('path')] = r
                except (OSError, ValueError):
                    pass
        for w in safe[:cap]:
            act = {'path': str(w.path), 'branch': w.branch, 'head': w.head,
                   'verdict': w.verdict, 'proof': w.proof, 'size_kb': w.size_kb,
                   'time': time.time(), 'branch_preserved': True}
            if args.dry_run:
                act['dry_run'] = True
                actions.append(act)
                continue
            member = next((m for m in available_members
                           if any(str(w.path).startswith(str(Path(m['root']) / c) + os.sep)
                                  for c in ('claude', 'codex', 'manual'))), None)
            if member is None:
                act['skipped'] = 'not under a verified managed client root'
                actions.append(act)
                continue
            result = guard.remove_candidate(
                gc=gc, primary=primary, w=w, cfg=cfg, procs=procs,
                pr_states=pr_states, fetch_ok=fetch_ok,
                protected=protected, check_volume=check_storage, member=member)
            act.update(result)
            if act.get('remove_rc') == 0:
                rec = receipts.get(str(w.path))
                if rec is not None:
                    try:
                        rec.unlink()
                        act['receipt_retired'] = str(rec)
                    except OSError as exc:
                        act['receipt_retire_error'] = str(exc)
            actions.append(act)
            if guard.unresolved_effects():
                # A Git tool timeout may have executed remotely: freeze this carrier.
                report['effect_unknown'] = True
                break
        report['applied'] = not args.dry_run
        report['removed'] = sum(1 for a in actions if a.get('remove_rc') == 0)
        report['removed_kb'] = sum(a.get('size_kb') or 0 for a in actions if a.get('remove_rc') == 0)
        report['free_ssd_after'] = shutil.disk_usage(mount).free
        report['free_ssd_after_by_volume'] = {
            member['mount_point']: shutil.disk_usage(member['mount_point']).free
            for member in available_members
        }

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    out = {'report': report, 'rows': rows, 'actions': actions}
    path = STATE_DIR / f'ssd-reaper-{int(now)}.json'
    path.write_text(json.dumps(out, indent=1))
    if actions:
        with (STATE_DIR / 'ssd-reaper-ledger.jsonl').open('a') as f:
            for a in actions:
                f.write(json.dumps(a) + '\n')
    if args.receipts:
        try:
            Path(args.receipts).mkdir(parents=True, exist_ok=True)
            (Path(args.receipts) / path.name).write_text(json.dumps(out, indent=1))
        except OSError:
            pass
    if args.json:
        print(json.dumps(report))
    else:
        print(json.dumps(report, indent=1))
        for w in safe[:40]:
            print(f"  {w.verdict:12} {(w.size_kb or 0)/1048576:5.1f}G age={w.age_days!s:>6} {w.path.name[:50]:50} {w.proof or ''}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
