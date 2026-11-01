"""Read-only coherence/custody check for the original native GEX archive.

No fetch, reconstruction, staging or ledger write. This verifies a producer's
derived summary, not observable dealer ownership or a data-rights grant.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ARCHIVE = 'data/gex/latest.json'
MANIFEST = 'site/gex/index.json'


def _json(raw):
    def reject(value):
        raise ValueError('nonfinite JSON quantity: ' + value)
    return json.loads(raw, parse_constant=reject)


def _read(root, rel):
    path = root / rel
    if any(p.is_symlink() for p in [path, *path.parents] if p != root):
        raise ValueError('unbound symlink: ' + rel)
    if not path.is_file():
        raise ValueError('missing original producer file: ' + rel)
    return path.read_bytes()


def _blob(root, ref, rel=ARCHIVE):
    if not ref or ref.startswith('-'):
        raise ValueError('explicit accepted Git reference required')
    r = subprocess.run(['git', '-C', str(root), 'show', f'{ref}:{rel}'],
                       capture_output=True, env={**os.environ, 'GIT_NO_LAZY_FETCH': '1'})
    if r.returncode:
        raise ValueError('unreadable archive binding at Git reference')
    return r.stdout


def check(root, *, session, base_ref, accepted_ref=None, candidate_ref=None):
    # The producer owns the index/ETF set and projection; never retype its
    # numeric field semantics or broaden to fragile single-name estimates.
    from scripts.build_gex_board import ARCHIVE_KEYS, _ARCHIVE_FIELDS

    root = Path(root).resolve()
    session_date = date.fromisoformat(session)
    raw, site_raw = _read(root, ARCHIVE), _read(root, MANIFEST)
    snap, manifest = _json(raw), _json(site_raw)
    if (not isinstance(snap, dict) or set(snap) != {'asof', 'source', 'indices', 'market'}
            or snap['source'] != 'cboe_delayed' or snap['asof'] != session_date.isoformat()
            or not isinstance(snap['market'], dict) or not isinstance(manifest, list)):
        raise ValueError('archive source/schema/session mismatch')
    core = {}
    for row in manifest:
        if not isinstance(row, dict):
            raise ValueError('malformed site manifest row')
        key = row.get('key')
        if key not in ARCHIVE_KEYS:
            continue
        if key in core or row.get('asof') != session:
            raise ValueError('duplicate core key or site session mismatch')
        core[key] = {field: row.get(field) for field in _ARCHIVE_FIELDS}
    if not core or snap['indices'] != core:
        raise ValueError('archive differs from original site core projection')
    for values in core.values():
        for field, value in values.items():
            if value is None:
                continue
            expected = (str,) if field in {'regime', 'tier'} else (int, float)
            if type(value) not in expected:
                raise ValueError('producer field type/unit shape changed')
    # The existing producer emits these dated aggregates, never option chains.
    if set(snap['market']) - {'skew', 'skew_asof', 'index_pc_ratio',
                             'equity_pc_ratio', 'put_call_asof'}:
        raise ValueError('unexpected auxiliary context payload')
    for key in ('skew', 'index_pc_ratio', 'equity_pc_ratio'):
        if key in snap['market'] and type(snap['market'][key]) not in (int, float):
            raise ValueError('auxiliary context quantity malformed')
    for key in ('skew_asof', 'put_call_asof'):
        if key in snap['market'] and date.fromisoformat(snap['market'][key]) > session_date:
            raise ValueError('future auxiliary context vintage')

    base = _blob(root, base_ref)
    if date.fromisoformat(_json(base)['asof']) > session_date:
        raise ValueError('archive would regress the accepted session')
    if accepted_ref:
        accepted = _blob(root, accepted_ref)
        if accepted not in (base, raw):
            raise ValueError('concurrent accepted archive changed; publication held')
    if candidate_ref and (raw != _blob(root, candidate_ref)
                          or site_raw != _blob(root, candidate_ref, MANIFEST)):
        raise ValueError('candidate commit differs from verified producer pair')
    # Read stability is separate from the post-rebase Git custody fence.
    if _read(root, ARCHIVE) != raw or _read(root, MANIFEST) != site_raw:
        raise ValueError('producer files changed during verification')
    return {'archive_sha256': hashlib.sha256(raw).hexdigest(),
            'site_manifest_sha256': hashlib.sha256(site_raw).hexdigest(),
            'asof': session, 'indices': sorted(core), 'source': snap['source']}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', default='.')
    ap.add_argument('--session', required=True)
    ap.add_argument('--base-ref', required=True)
    ap.add_argument('--accepted-ref')
    ap.add_argument('--candidate-ref')
    args = ap.parse_args(argv)
    try:
        result = check(args.root, session=args.session, base_ref=args.base_ref,
                       accepted_ref=args.accepted_ref, candidate_ref=args.candidate_ref)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print('GEX archive publication held: ' + str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
