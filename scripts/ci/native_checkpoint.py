"""Original engine checkpoints: pure integration fence and final receipt outputs.

Core authenticates the protected producer tuple before calling the fence. This
module cannot authorize admission, acquire data, enqueue or extend a budget.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import math
import os
from pathlib import Path
import re
import subprocess
import time

from scripts.ci import native_queue_push as native

AUTHORITY = ('data/prophet', 'data/prophet_arena', 'site/prophet')
PROFILES = {
    'leader': ('site/anticipationdata/us_leader_pullback.json',),
    'prophet': AUTHORITY,
    'shadow': AUTHORITY + ('data/prophet_stage_shadow',),
}
OWNED = {
    'leader': PROFILES['leader'],
    'shadow': ('data/prophet_stage_shadow/ledger.jsonl',
               'data/prophet_stage_shadow/revisions.jsonl',
               'data/prophet_stage_shadow/summary.json'),
    'prophet': ('site/prophet/index.json', 'site/prophet/showcase.json',
        'site/prophet/board_read_sparks.json', 'data/prophet/ledger.jsonl',
        'data/prophet/ledger_quarantine.json', 'data/prophet_arena/scoreboard.json',
        'data/prophet/origination_receipts/*.json', 'data/prophet/origination_sources/*.json.gz',
        'data/prophet/legacy_shadow/*/*.parquet', 'site/prophet/plans/*.json',
        'site/prophet/states/*.json') + tuple('data/prophet_arena/price_basis_trigger_v2/'+n+'.jsonl'
            for n in ('C0_champion_mirror', 'C1_buy_soon_first', 'C3_door_w_union',
                      'C4_dispersion_cap', 'C5_align2_gate', 'C6_time_stop_21', 'C7_buy_soon_admitted')),
}


def validate_native_group(root, candidate, group_base, group_commit, profile, *,
                          git_read=None, deadline=None):
    """Reject queued input movement; conserve the complete candidate projection.

    git_read has the SAME callable/absolute monotonic deadline contract as
    fms_persist.validate_native_group. Every read consumes core's original
    allowance. There is no fetch, workspace mutation or ambient Git fallback.
    """
    if profile not in PROFILES:
        raise native.PublicationHeld('checkpoint_profile_unqualified')
    for identity in (candidate, group_base, group_commit):
        if not isinstance(identity, str) or not re.fullmatch('[0-9a-f]{40}', identity):
            raise native.PublicationHeld('immutable_checkpoint_group_identity_required')
    if git_read is not None and deadline is None:
        raise native.PublicationHeld('original_group_deadline_required')
    if deadline is not None and (type(deadline) not in (int, float) or not math.isfinite(deadline)):
        raise native.PublicationHeld('original_group_deadline_invalid')

    def read(*args, allow_false=False):
        remaining = 30 if deadline is None else min(30, deadline-time.monotonic())
        if remaining <= 0:
            raise native.PublicationHeld('original_group_deadline_expired')
        if git_read is None:
            result = subprocess.run(['git', '-C', str(root), *args], capture_output=True,
                timeout=remaining, env={**os.environ, 'GIT_OPTIONAL_LOCKS':'0',
                    'GIT_NO_REPLACE_OBJECTS':'1', 'GIT_NO_LAZY_FETCH':'1'})
        else:
            result = git_read(root, *args, timeout=remaining)
        if deadline is not None and time.monotonic() >= deadline:
            raise native.PublicationHeld('original_group_deadline_expired')
        if type(result.returncode) is not int or not isinstance(result.stdout, bytes):
            raise native.PublicationHeld('checkpoint_git_read_result_unqualified')
        if result.returncode and not (allow_false and result.returncode == 1):
            raise native.PublicationHeld('checkpoint_git_read_unavailable')
        return result

    parents = read('rev-list', '--parents', '-n', '1', candidate).stdout.split()
    if len(parents) != 2 or parents[0].decode() != candidate:
        raise native.PublicationHeld('one_checkpoint_parent_required')
    base = parents[1].decode()
    if read('merge-base', '--is-ancestor', base, group_base, allow_false=True).returncode:
        raise native.PublicationHeld('checkpoint_base_not_in_selected_target')
    paths = [os.fsdecode(p) for p in read('diff', '--name-only', '-z', '--no-renames',
                                        base, candidate).stdout.split(b'\0') if p]
    roots = PROFILES[profile]
    allowed = roots if profile != 'shadow' else ('data/prophet_stage_shadow',)
    if not paths or any(not any(fnmatch.fnmatchcase(p, a) for a in OWNED[profile]) for p in paths):
        raise native.PublicationHeld('checkpoint_candidate_outside_owned_projection')
    if read('diff', '--quiet', base, group_base, '--', *roots, allow_false=True).returncode:
        raise native.PublicationHeld('checkpoint_inputs_advanced_while_queued')
    if read('diff', '--quiet', candidate, group_commit, '--', *roots, allow_false=True).returncode:
        raise native.PublicationHeld('native_group_changed_checkpoint_projection')
    # Modes/deletions belong to the original projection, not just text content.
    entries = read('ls-tree', '-r', '-z', candidate, '--', *paths).stdout.split(b'\0')
    present = {os.fsdecode(e.partition(b'\t')[2]) for e in entries if e}
    if present != set(paths) or any(e and not e.startswith(b'100644 blob ') for e in entries):
        raise native.PublicationHeld('checkpoint_nonregular_projection')
    return {'candidate':candidate, 'checkpoint_base':base, 'group_base':group_base,
            'group_commit':group_commit, 'profile':profile}


def prophet_outputs(api, root, receipt, index_sha256):
    """Arm only the ACTUAL protected squash and its current authority tree."""
    if not re.fullmatch('[0-9a-f]{64}', index_sha256 or ''):
        raise native.PublicationHeld('original_prophet_index_digest_required')
    merge = native.sha(receipt['merge_sha'])
    observed = native.sha(receipt['observed_target_sha'])
    # Server Git identities provide all authority roots without fetching data.
    if native.tree(api, merge, AUTHORITY)[0] != native.tree(api, observed, AUTHORITY)[0]:
        raise native.PublicationHeld('prophet_authority_superseded_after_checkpoint')
    blob = native.tree(api, merge, ('site/prophet/index.json',))[0].get('site/prophet/index.json')
    if not blob or blob.get('mode') != '100644':
        raise native.PublicationHeld('protected_prophet_index_missing')
    # The original digest is bound to the same original projection; obtain bytes
    # from the local immutable candidate, never a later workspace file.
    original = receipt['source_head']
    deadline = getattr(api, 'deadline', 0)
    remaining = min(30, deadline-time.time()) if deadline else 30
    if remaining <= 0:
        raise native.PublicationHeld('original_publication_budget_expired')
    result = subprocess.run(['git', '-C', str(root), 'show',
                             original+':site/prophet/index.json'], capture_output=True,
                            env={**os.environ, 'GIT_NO_REPLACE_OBJECTS':'1', 'GIT_NO_LAZY_FETCH':'1'}, timeout=remaining)
    if deadline and time.time() >= deadline:
        raise native.PublicationHeld('original_publication_budget_expired')
    if result.returncode or hashlib.sha256(result.stdout).hexdigest() != index_sha256:
        raise native.PublicationHeld('original_prophet_index_digest_changed')
    if native.tree(api, original, ('site/prophet/index.json',))[0].get('site/prophet/index.json') != blob:
        raise native.PublicationHeld('protected_prophet_index_projection_changed')
    return {'r2_ready':'true', 'checkpoint_sha':merge, 'index_sha256':index_sha256}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.')
    parser.add_argument('--record', required=True)
    parser.add_argument('--deadline', required=True, type=float)
    parser.add_argument('--index-sha256')
    args = parser.parse_args(argv)
    try:
        api = native.GitHub(Path(args.root), args.deadline)
        def confirmed(receipt):
            outputs = {'published':'true', 'source_sha':native.sha(receipt['merge_sha'])}
            if args.index_sha256:
                outputs.update(prophet_outputs(api, Path(args.root), receipt, args.index_sha256))
            with Path(os.environ['GITHUB_OUTPUT']).open('a') as out:
                out.write(''.join(k+'='+v+'\n' for k,v in outputs.items()))
        return native.settle(api, Path(args.root), args.record, args.deadline, on_published=confirmed)
    except native.EffectUnknown:
        return native.UNKNOWN
    except (native.PublicationHeld, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        return native.REFUSED


if __name__ == '__main__':
    raise SystemExit(main())
