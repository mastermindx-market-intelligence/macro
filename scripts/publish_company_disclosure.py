"""Publish a protected disclosure generation, or explicitly append one SEC supplier.

Invoke as python -m scripts.publish_company_disclosure. A stable operation ID is
mandatory and reserved with O_EXCL before effects. Existing receipts prohibit a
second invocation; inspect/reconcile that same operation instead of changing ID.
The production root must already be provisioned by the incumbent deployment owner.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import errno
import json
import os
from pathlib import Path
import re
import sys

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.company_intelligence import issuer_disclosure_owner as owner
from engine.company_intelligence import issuer_disclosure_preflight as preflight
from engine.company_intelligence import issuer_disclosures as native
from engine.company_intelligence.issuer_disclosure_publication import (
    RetainedFileSource, prepare_publication, publish_generation,
)
from engine.research_vault.r2_store import LocalStore



def _append_sources(repo):
    from engine.company_intelligence.sec_supplier_adoption import SOURCE_PATHS
    return (owner.CommittedDisclosureSource(repo, sec_supplier_paths=SOURCE_PATHS),
            {native.FACT_SCHEMA: owner.CommittedDisclosureSource(repo)})


def _pinned_supplier_source(admitted):
    # This factory is called only after the exclusive operation reservation and
    # owner admission. Reuse the incumbent private Research store and native
    # pinned-source reader; never copy raw sources into a second local store.
    from engine.company_intelligence.sec_supplier_adoption import PinnedSupplierSource
    from engine.fundamental_forensics.filing_attestation import PinnedSourceAuthority
    from engine.research_vault import r2_store
    native._require(not os.environ.get('RESEARCH_LOCAL_STORE'), 'SEC_LOCAL_SOURCE_OVERRIDE_REFUSED')
    store = r2_store.build_store()
    native._require(type(store) is r2_store.R2Store and store.available,
                    'SEC_NATIVE_SOURCE_STORE_UNAVAILABLE')
    native._require(admitted.spec['edition']['schema'] == native.SEC_EDITION_SCHEMA,
                    'SEC_SOURCE_BINDING_MISMATCH')
    authority = PinnedSourceAuthority(store=store,
        snapshot_id=admitted.spec['edition']['sec_source']['snapshot_id'])
    return PinnedSupplierSource(admitted, authority)


def _directory(path):
    return preflight.open_directory(path)


def _reserve(directory_fd, name, value):
    try:
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=directory_fd)
    except FileExistsError:
        raise native.DisclosureError('RESERVATION_EXISTS') from None
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            raise native.DisclosureError('RESERVATION_EXISTS') from None
        raise
    try:
        raw = json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode() + b'\n'
        offset = 0
        while offset < len(raw):
            count = os.write(fd, raw[offset:])
            if count <= 0:
                raise OSError('journal short write')
            offset += count
        os.fsync(fd)
        os.fsync(directory_fd)
    except native.DisclosureError:
        raise
    except Exception:
        raise native.DisclosureError('RECONCILIATION_REQUIRED', effect_unknown=True) from None
    finally:
        try:
            os.close(fd)
        except Exception:
            raise native.DisclosureError('RECONCILIATION_REQUIRED', effect_unknown=True) from None


def _emit(payload, rc):
    print(json.dumps(payload, sort_keys=True))
    return rc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--root', type=Path, default=Path('/var/lib/macro-company-intelligence'))
    parser.add_argument('--operation-id', required=True)
    parser.add_argument('--append-sec-supplier', action='store_true',
        help='Append the protected SEC supplier member while preserving current component generations')
    parser.add_argument('--expected-deployment-json', type=Path, required=True)
    expected_group = parser.add_mutually_exclusive_group(required=True)
    expected_group.add_argument('--expect-empty', action='store_true')
    expected_group.add_argument('--expected-current-version')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        native._require(re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,100}', args.operation_id) is not None,
                        'OPERATION_ID_INVALID')
        expected = preflight.load_expected_deployment(args.expected_deployment_json)
        native._require(Path(os.path.abspath(args.root)) == Path(os.path.abspath(preflight.PRODUCTION_ROOT))
                        == Path(os.path.abspath(expected['root'])), 'PREFLIGHT_DEPLOYMENT_ROOT')
        native._require(os.path.abspath(args.repo) == os.path.abspath(expected['producer']['repo']),
                        'PREFLIGHT_PRODUCER_REPO')
        invoked = datetime.now(timezone.utc)
        process = preflight.read_process_identity('self')
        native._require(process['uid'] == expected['producer']['uid'], 'PREFLIGHT_PRODUCER_UID')
        native._require(process['mountnamespace'] != expected['api_census']['mountnamespace'],
                        'PREFLIGHT_NAMESPACE_SHARED')
        preflight.evaluate_census_time(expected, invoked.isoformat(), invoked.isoformat())
        mounts = preflight.read_mountinfo()
        roots = preflight.qualify_roots(args.root, expected['producer']['uid'], mounts)
        preflight.operation_names_absent(args.root, args.operation_id)
        if args.append_sec_supplier:
            native._require(not args.expect_empty and expected['mode'] == 'APPEND_CURRENT_MEMBER',
                            'PREFLIGHT_APPEND_MODE_REQUIRED')
            native._require(not os.environ.get('RESEARCH_LOCAL_STORE'), 'SEC_LOCAL_SOURCE_OVERRIDE_REFUSED')
            # Load append-only dependencies for same-process provenance. Import
            # does not construct a store, read a source or publish anything.
            from engine.fundamental_forensics import filing_attestation, source_sync  # noqa: F401
            source, preserved_sources = _append_sources(args.repo)
        else:
            native._require(expected['mode'] != 'APPEND_CURRENT_MEMBER', 'PREFLIGHT_APPEND_MODE_REQUIRED')
            source, preserved_sources = owner.CommittedDisclosureSource(args.repo), None
        native._require(os.path.abspath(source.git.repo) == os.path.abspath(args.repo),
                        'PREFLIGHT_PRODUCER_REPO')
        mode_kwargs = {'mode': 'APPEND_CURRENT_MEMBER'} if args.append_sec_supplier else {}
        provenance = preflight.collect_on_disk_provenance(source.git, sys.modules, **mode_kwargs)
        native._require(provenance['head'] == expected['code_version'], 'PREFLIGHT_PRODUCER_HEAD')
        capture = {'process': process, 'captured_at': invoked.isoformat(),
                   'provenance': provenance, 'roots': roots}
        publication_kwargs = ({'mode': 'APPEND_CURRENT_MEMBER', 'preserved_sources': preserved_sources}
                              if args.append_sec_supplier else {})
        intent = prepare_publication(
            source, owner.ReadOnlyLocalObjects(args.root / 'state'),
            expected_current_version=None if args.expect_empty else args.expected_current_version,
            **publication_kwargs)
        def same_manifest(snapshot, prepared):
            if not args.append_sec_supplier:
                return prepared['manifest'] == owner.make_manifest(snapshot, prepared['manifest']['computed_at'])
            from engine.company_intelligence.issuer_disclosure_publication import validate_publication_intent
            validated, _ = validate_publication_intent(source, owner.ReadOnlyLocalObjects(args.root / 'state'),
                prepared, preserved_sources=preserved_sources)
            return validated == snapshot
        evidence = preflight.finalize_gate(
            expected, capture, source, intent, mounts, modules=sys.modules,
            same_manifest=same_manifest)
        digest = preflight.evidence_digest(evidence)
        envelope = {'schema': 'company_intelligence.publication_operation/v1',
            'operation_id': args.operation_id, 'started_at': datetime.now(timezone.utc).isoformat(),
            'intent': intent, 'producer_preflight': evidence,
            'producer_preflight_sha256': digest, 'state': 'STARTED',
            'automatic_retry_permitted': False}
    except native.DisclosureError as exc:
        if exc.effect_unknown:
            return _emit(preflight.refuse_payload('RECONCILIATION_REQUIRED', effect_unknown=True), 2)
        return _emit(preflight.refuse_payload(exc.code), 1)
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return _emit(preflight.refuse_payload('PREFLIGHT_OBSERVATION_FAILED'), 1)
    try:
        directory_fd = _directory(args.root / 'publisher/operations')
    except OSError:
        return _emit(preflight.refuse_payload('PREFLIGHT_ROOT_CHANGED'), 1)
    try:
        try:
            actual = os.fstat(directory_fd)
            mount_id = preflight.descriptor_mount_id(directory_fd)
        except (OSError, native.DisclosureError):
            return _emit(preflight.refuse_payload('PREFLIGHT_ROOT_CHANGED'), 1)
        observed = evidence['roots']['publisher/operations']
        if mount_id != observed['mount_id']:
            return _emit(preflight.refuse_payload('PREFLIGHT_ROOT_CHANGED'), 1)
        if (actual.st_dev, actual.st_ino, actual.st_uid, actual.st_gid,
                actual.st_mode & 0o7777) != tuple(observed[k] for k in (
                    'device', 'inode', 'uid', 'gid', 'mode')):
            return _emit(preflight.refuse_payload('PREFLIGHT_ROOT_CHANGED'), 1)
        # Immutable intent survives crashes while saving the separate outcome.
        try:
            _reserve(directory_fd, args.operation_id + '.json', envelope)
        except native.DisclosureError as exc:
            if exc.code == 'RESERVATION_EXISTS':
                return _emit(preflight.refuse_payload('RESERVATION_EXISTS'), 1)
            if exc.effect_unknown:
                return _emit(preflight.refuse_payload('RESERVATION_EFFECT_UNKNOWN', effect_unknown=True), 2)
            return _emit(preflight.refuse_payload(exc.code), 1)
        except OSError:
            # O_EXCL failed before it returned a new file descriptor.
            return _emit(preflight.refuse_payload('RESERVATION_CREATE_FAILED'), 1)
        try:
            source_factory = (_pinned_supplier_source if args.append_sec_supplier else
                lambda admitted: RetainedFileSource(admitted, args.root / 'publisher/source',
                    admitted.spec['edition']['source_sha256'] + '.html'))
            result = publish_generation(source, LocalStore(args.root / 'state'),
                LocalStore(args.root / 'artifacts'), source_factory, intent=intent,
                **({'preserved_sources': preserved_sources} if args.append_sec_supplier else {}))
            outcome = {'state': result['status'], 'result': result, 'automatic_retry_permitted': False}
            rc = 0
        except Exception as exc:
            outcome = {'state': 'RECONCILIATION_REQUIRED', 'error_code': (exc.code
                if isinstance(exc, native.DisclosureError) else 'PUBLICATION_OPERATION_UNSETTLED'),
                'effect_unknown': True, 'automatic_retry_permitted': False}
            rc = 2
        try:
            _reserve(directory_fd, args.operation_id + '.result.json', outcome)
        except native.DisclosureError as exc:
            code = 'OUTCOME_RESERVATION_EXISTS' if exc.code == 'RESERVATION_EXISTS' else 'RESERVATION_EFFECT_UNKNOWN'
            return _emit(preflight.refuse_payload(code, effect_unknown=True), 2)
        except OSError:
            return _emit(preflight.refuse_payload('OUTCOME_RESERVATION_FAILED', effect_unknown=True), 2)
        result = outcome.get('result', outcome)
        print(json.dumps(result, sort_keys=True))
        return rc
    finally:
        os.close(directory_fd)


if __name__ == '__main__':
    raise SystemExit(main())
