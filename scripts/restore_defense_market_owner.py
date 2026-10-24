"""Bounded canonical R2 hydration of the existing Massive quartet before build.

No vendor acquisition or upstream writes. Preserve tracked collector _manifest.json.
The same-owner .defense_read receipt activates only after all four bytes validate.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from hashlib import md5, sha256
import json
import os
from pathlib import Path
import sys
import tempfile

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

TICKERS = ('LMT', 'RTX', 'NOC', 'LHX')
PREFIX = 'massive_stock_day/'
MAX_BYTES = 16 * 1024 * 1024


def _stamp():
    return datetime.now(timezone.utc).isoformat()


def _read(client, bucket, key, *, etag=None):
    arguments = {'Bucket': bucket, 'Key': key}
    if etag is not None:
        arguments['IfMatch'] = '"' + etag + '"'
    result = client.get_object(**arguments)
    stream = result['Body']
    try:
        body = stream.read(MAX_BYTES + 1)
    finally:
        stream.close()
    if len(body) > MAX_BYTES:
        raise ValueError('canonical_object_size_limit')
    size = result['ContentLength']
    tag = result['ETag'].strip('"')
    if isinstance(size, bool) or not isinstance(size, int) or size != len(body):
        raise ValueError('canonical_object_content_length_mismatch')
    if etag is not None and tag != etag:
        raise ValueError('canonical_object_etag_changed')
    if '-' not in tag and md5(body).hexdigest() != tag:
        raise ValueError('canonical_object_etag_body_mismatch')
    return body, {'key': key, 'etag': tag, 'last_modified': result['LastModified'].isoformat(),
        'content_length': size, 'observed_at': _stamp(), 'sha256': sha256(body).hexdigest()}


def _version(receipt):
    return tuple(receipt[k] for k in ('sha256', 'etag', 'last_modified', 'content_length'))


def _atomic_write(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix='.restore-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as output:
            output.write(body)
            output.flush()
            os.fsync(output.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _assert_local_owner_paths(root, targets):
    # The configured root is the trusted boundary; no descendant may redirect
    # exact owner bytes through an existing or dangling symlink. Check the
    # whole candidate set before the first local write, including marker.
    anchor=Path(root).absolute()
    for target in targets:
        target=Path(target).absolute()
        try:relative=target.relative_to(anchor)
        except ValueError:raise ValueError('local_owner_destination_outside_root')
        current=anchor
        if current.is_symlink():raise ValueError('local_owner_symlink_destination')
        if current.exists() and not current.is_dir():raise ValueError('local_owner_root_not_directory')
        for index,part in enumerate(relative.parts):
            current=current/part
            if current.is_symlink():raise ValueError('local_owner_symlink_destination')
            if index<len(relative.parts)-1 and current.exists() and not current.is_dir():
                raise ValueError('local_owner_ancestor_not_directory')
        if current.exists() and not current.is_file():raise ValueError('local_owner_leaf_not_file')


def restore_defense_market_owner(root, *, client, bucket, list_objects=None):
    """Freeze four existing canonical objects, then activate a receipt locally.

    Remote refusal/change/shape failure has no local effect. A local interrupted
    commit cannot qualify because the pure consumer verifies receipt/body hashes.
    Independently recorded before/after retrieval times are never equated.
    """
    if list_objects is None:
        from scripts.publish_r2 import _remote_etags
        list_objects = _remote_etags
    manifest_key = PREFIX + '_manifest.json'
    raw, before = _read(client, bucket, manifest_key)
    manifest = json.loads(raw)
    files = manifest.get('files')
    count = manifest.get('count')
    if (manifest.get('dir') != 'massive_stock_day' or not isinstance(files, list)
        or any(not isinstance(v, str) for v in files)
        or len(set(files)) != len(files) or isinstance(count, bool)
        or not isinstance(count, int) or count != len(files)
        or not isinstance(manifest.get('store'), dict)):
        raise ValueError('canonical_manifest_shape_unqualified')
    frozen = {}
    receipts = {}
    for ticker in TICKERS:
        name = ticker + '.parquet'
        key = PREFIX + name
        if name not in files:
            raise ValueError('quartet_object_not_in_canonical_manifest')
        listed = list_objects(client, bucket, key)
        if key not in listed:
            raise ValueError('canonical_manifest_member_not_listed')
        etag, size = listed[key]
        if isinstance(size, bool) or not isinstance(size, int) or not 0 < size <= MAX_BYTES:
            raise ValueError('canonical_listed_size_unqualified')
        body, receipt = _read(client, bucket, key, etag=etag)
        if receipt['content_length'] != size:
            raise ValueError('canonical_listed_object_size_changed')
        if list_objects(client, bucket, key).get(key) != (etag, size):
            raise ValueError('canonical_object_changed_after_read')
        receipt['state'] = 'STABLE_BYTE_READ'
        frozen[name] = body
        receipts[ticker] = receipt
    after_raw, after = _read(client, bucket, manifest_key, etag=before['etag'])
    if after_raw != raw or _version(after) != _version(before):
        raise ValueError('canonical_manifest_changed_during_read')
    record = {'state': 'STABLE_CANONICAL_SNAPSHOT_READ', 'source_store': 'massive_stock_day',
        'source_owner': 'collectors/massive_stock_day.py -> scripts/publish_r2.py',
        'manifest_before': before, 'manifest_after': after, 'objects': receipts,
        'completed_at': _stamp(), 'vendor_acquisition': False, 'source_written': False,
        'upstream_effect': 'read_only', 'preserved_tracked_collector_manifest': True}
    store = Path(root) / 'data/massive_stock_day'
    _assert_local_owner_paths(root,[store/name for name in frozen]+[store/'.defense_read/manifest.json',store/'.defense_read/read_receipt.json'])
    for name, body in frozen.items():
        _atomic_write(store / name, body)
    _atomic_write(store / '.defense_read/manifest.json', raw)
    _atomic_write(store / '.defense_read/read_receipt.json',
        (json.dumps(record, sort_keys=True, indent=2) + '\n').encode())
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    args = parser.parse_args(argv)
    from scripts.publish_r2 import _client
    client = _client(1)
    bucket = os.environ.get('R2_BUCKET')
    if client is None or not bucket:
        raise ValueError('existing_owner_r2_client_not_provisioned')
    record = restore_defense_market_owner(args.root, client=client, bucket=bucket)
    print(json.dumps({'state': record['state'], 'manifest_sha256': record['manifest_before']['sha256'],
        'tickers': list(TICKERS), 'upstream_effect': 'read_only'}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
