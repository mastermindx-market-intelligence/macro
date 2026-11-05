"""Bounded canonical archive acquisition inside the existing sealed Macro capture.

The collector supplies its immutable captured tree/commit and the authorized
catalogue refs. This does not elect a Git revision, broaden catalogue membership,
write records, infer archive state, or grant a continuation target.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

SCHEMA = 'agentos.project_archive_sample.v1'
MAX_BYTES = 131072
MAX_WORKSTREAMS = 128
_REF = re.compile(r'WS:[A-Z0-9]+(?:-[A-Z0-9]+)*\Z')


def read_archive_sample(macro_root, *, captured_commit, qualified_work_refs, owner, programs):
    if (type(captured_commit) is not str or re.fullmatch(r'[0-9a-f]{40}', captured_commit) is None
            or type(qualified_work_refs) is not list or len(qualified_work_refs) > MAX_WORKSTREAMS
            or any(type(ref) is not str or _REF.fullmatch(ref) is None or not 2 <= len(ref[3:]) <= 64 for ref in qualified_work_refs)
            or len(set(qualified_work_refs)) != len(qualified_work_refs)
            or type(programs) is not set or not programs):
        raise ValueError('INVALID_SOURCE_SELECTION')
    root = Path(macro_root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('SOURCE_UNAVAILABLE')
    result = {'schema': SCHEMA, 'source_commit': captured_commit,
              'coverage': {'kind': 'QUALIFIED_CATALOGUE_SAMPLE', 'supplied_count': len(qualified_work_refs),
                           'observed_count': 0, 'company_total': None},
              'availability': 'AVAILABLE', 'reason': None, 'items': [], 'can_restore': False}
    try:
        for ref in sorted(qualified_work_refs):
            relative = 'agentos/workstreams/WS-' + ref[3:] + '.md'
            path = root / relative
            if any(parent.is_symlink() for parent in [path, path.parent, path.parent.parent]) or not path.is_file():
                raise ValueError('SOURCE_UNAVAILABLE')
            raw = path.read_bytes()
            if len(raw) > 131072:
                raise ValueError('SOURCE_OVER_BUDGET')
            rec, _ = owner.parse_record(path)
            if rec.get('key') != ref[3:] or any(p.hard for p in owner.check_workstream(rec, path, programs)):
                raise ValueError('INVALID_SOURCE')
            if path.read_bytes() != raw:
                raise ValueError('SOURCE_CHANGED')
            result['coverage']['observed_count'] += 1
            if 'archive' not in rec:
                continue
            archive = dict(rec['archive'])
            archive['archived_on'] = str(archive['archived_on'])
            result['items'].append({'work_ref': ref, 'title': rec['title'], 'objective': rec['objective'],
                                    'archive': archive, 'source': {'repository': 'macro', 'commit': captured_commit,
                                    'path': relative, 'content_sha256': hashlib.sha256(raw).hexdigest()}})
        if len(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()) + 1 > MAX_BYTES:
            raise ValueError('SOURCE_OVER_BUDGET')
    except (OSError, ValueError, TypeError, UnicodeError):
        # Partial acquisition cannot establish even sample-level absence. Do not
        # expose partial rows or coerce an unreadable source into empty history.
        result.update(availability='UNAVAILABLE', reason='SOURCE_UNAVAILABLE', items=[])
    return result
