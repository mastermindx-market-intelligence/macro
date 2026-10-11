"""Publish one protected, owner-admitted generation from the retained C01 input.

Invoke as python -m scripts.publish_company_disclosure. A stable operation ID is
mandatory and reserved with O_EXCL before effects. Existing receipts prohibit a
second invocation; inspect/reconcile that same operation instead of changing ID.
The production root must already be provisioned by the incumbent deployment owner.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.company_intelligence import issuer_disclosure_owner as owner
from engine.company_intelligence import issuer_disclosures as native
from engine.company_intelligence.issuer_disclosure_publication import (
    RetainedFileSource, prepare_publication, publish_generation,
)
from engine.research_vault.r2_store import LocalStore


def _directory(path):
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open('/', flags)
    try:
        for part in Path(os.path.abspath(path)).parts[1:]:
            next_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd); fd = next_fd
        return fd
    except BaseException:
        os.close(fd)
        raise


def _reserve(directory_fd, name, value):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o600, dir_fd=directory_fd)
    try:
        raw = json.dumps(value, sort_keys=True, indent=2).encode() + b'\n'
        offset = 0
        while offset < len(raw):
            count = os.write(fd, raw[offset:])
            if count <= 0:
                raise OSError('journal short write')
            offset += count
        os.fsync(fd)
        os.fsync(directory_fd)
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--root', type=Path, default=Path('/var/lib/macro-company-intelligence'))
    parser.add_argument('--operation-id', required=True)
    expected = parser.add_mutually_exclusive_group(required=True)
    expected.add_argument('--expect-empty', action='store_true')
    expected.add_argument('--expected-current-version')
    args = parser.parse_args()
    native._require(re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,100}', args.operation_id) is not None,
                    'OPERATION_ID_INVALID')
    os.umask(0o077)
    source = owner.CommittedDisclosureSource(args.repo)
    # Existing roots only; a descriptor walk rejects any symlink before journal
    # creation or LocalStore's constructor can perform a mkdir.
    for key in ['state', 'artifacts', 'publisher/source', 'publisher/operations']:
        os.close(_directory(args.root / key))
    intent = prepare_publication(source, owner.ReadOnlyLocalObjects(args.root / 'state'),
        expected_current_version=None if args.expect_empty else args.expected_current_version)
    envelope = {'schema': 'company_intelligence.publication_operation/v1',
        'operation_id': args.operation_id, 'started_at': datetime.now(timezone.utc).isoformat(),
        'intent': intent, 'state': 'STARTED', 'automatic_retry_permitted': False}
    directory_fd = _directory(args.root / 'publisher/operations')
    try:
        # Immutable intent survives crashes while saving the separate outcome.
        _reserve(directory_fd, args.operation_id + '.json', envelope)
        try:
            result = publish_generation(source, LocalStore(args.root / 'state'),
                LocalStore(args.root / 'artifacts'),
                lambda admitted: RetainedFileSource(admitted, args.root / 'publisher/source',
                    admitted.spec['edition']['source_sha256'] + '.html'), intent=intent)
            outcome = {'state': result['status'], 'result': result, 'automatic_retry_permitted': False}
            rc = 0
        except Exception as exc:
            outcome = {'state': 'RECONCILIATION_REQUIRED', 'error_code': (exc.code
                if isinstance(exc, native.DisclosureError) else 'PUBLICATION_OPERATION_UNSETTLED'),
                'effect_unknown': True, 'automatic_retry_permitted': False}
            rc = 2
        _reserve(directory_fd, args.operation_id + '.result.json', outcome)
        result = outcome.get('result', outcome)
        print(json.dumps(result, sort_keys=True))
        return rc
    finally:
        os.close(directory_fd)


if __name__ == '__main__':
    raise SystemExit(main())
