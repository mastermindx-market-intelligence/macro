"""Immutable extension of an existing Market Memory study, not a new data plane.

Collection, scheduling and revision policy remain with their original owners.
Only explicit retained source references enter this composition. Original daily
state bytes/values never change; future outcomes mature in a new archive only.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterator

from lib.dataos.temporal import utc
from engine.neuralweb import market_memory_history_archive as archive
from engine.neuralweb.market_memory_history import HistoricalExperienceError

EXTENSION_SCHEMA = 'market_memory.history_extension.v1'
_FIXED_FIELDS = ('schema', 'mode', 'basis', 'benchmark', 'start', 'warmup_start',
                 'acknowledge_hindsight', 'selection')


def _next_request(parent: dict, request: dict) -> dict:
    next_request = archive._validate_request(request)
    old = parent['request']
    if any(next_request[k] != old[k] for k in _FIXED_FIELDS):
        raise HistoricalExperienceError('extension cannot change the original study')
    if (next_request['end'] < old['end']
            or utc(next_request['capture_cutoff']) < utc(old['capture_cutoff'])):
        raise HistoricalExperienceError('extension cannot regress end or capture cutoff')
    before = old['symbols']
    after = next_request['symbols']
    if [x['vendor_symbol'] for x in before] != [x['vendor_symbol'] for x in after]:
        raise HistoricalExperienceError('extension cannot change the selected source universe')
    for first, second in zip(before, after):
        if not {tuple(x) for x in first['refs']} <= {tuple(x) for x in second['refs']}:
            raise HistoricalExperienceError('extension cannot drop original capture references')
    if parent['feature_version'] != archive.FEATURE_VERSION:
        raise HistoricalExperienceError('different feature version requires a separate study')
    return next_request


def _state_rows(root: Path, manifest: dict) -> Iterator[dict]:
    """Read only bounded state partitions synchronously, never outcome files."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    total = 0
    previous = None
    symbols = {x['vendor_symbol'] for x in manifest['request']['symbols']}
    for record in sorted((x for x in manifest['files'] if x['kind'] == 'states'),
                         key=lambda x: x['year']):
        raw = archive._regular_file(root, record['name'], archive.MAX_FILE_BYTES)
        if len(raw) != record['bytes'] or archive._hash(raw) != record['sha256']:
            raise HistoricalExperienceError('parent historical data file digest mismatch')
        try:
            pf = pq.ParquetFile(pa.BufferReader(raw), pre_buffer=False)
            try:
                if pf.metadata.num_rows != record['rows']:
                    raise HistoricalExperienceError('parent historical row count mismatch')
                size = sum(pf.metadata.row_group(i).total_byte_size
                           for i in range(pf.metadata.num_row_groups))
                if size > archive.MAX_DATE_DECODE_BYTES:
                    raise HistoricalExperienceError('parent decoded state partition exceeds budget')
                table = pf.read(use_threads=False)
            finally:
                pf.close()
            if any(c.startswith(('forward_', 'outcome')) for c in table.column_names):
                raise HistoricalExperienceError('outcomes cannot enter the parent state stream')
            for row in table.to_pylist():
                row['missing'] = json.loads(row['missing'])
                day = archive._date(row['market_date'])
                symbol = row['vendor_symbol']
                if (symbol not in symbols or not day.startswith(record['year'] + '-')
                        or not manifest['request']['start'] <= day <= manifest['request']['end']
                        or type(row['missing']) is not dict):
                    raise HistoricalExperienceError('invalid parent historical state row')
                key = day, symbol
                if previous is not None and key <= previous:
                    raise HistoricalExperienceError('parent historical states are not unique and ordered')
                previous = key
                total += 1
                if total > archive.MAX_TOTAL_ROWS:
                    raise HistoricalExperienceError('parent historical total row budget exceeded')
                yield row
        except HistoricalExperienceError:
            raise
        except (ValueError, TypeError, KeyError, OSError) as exc:
            raise HistoricalExperienceError('invalid parent historical state partition') from exc


def extend_archive(parent_path: Path, request: dict, destination: Path, *,
                   expected_parent_manifest_sha256: str) -> dict:
    """Create one new archive only after every previous historical state agrees.

    Same request/captures with no new observations returns a no-write receipt.
    New data at a previously missing date before the parent's last observed day
    is a correction study, not an append. No retry, latest pointer or scheduler
    is installed. A partial filesystem write retains its original destination
    for reconciliation; this function never overwrites it on retry.
    """
    parent_path, destination = Path(parent_path), Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    # Path.resolve preserves spelling on case-insensitive APFS. Compare actual
    # directory identities as well; textual prefix checks alone admit PARENT/x.
    parent_stat = parent_path.stat()
    for ancestor in destination.parents:
        try:
            state = ancestor.stat()
        except FileNotFoundError:
            continue
        if (state.st_dev, state.st_ino) == (parent_stat.st_dev, parent_stat.st_ino):
            raise HistoricalExperienceError('extension destination cannot be inside the parent archive')
    if any(p.is_symlink() for p in destination.parents):
        raise HistoricalExperienceError('extension destination cannot traverse symlinks')
    parent = archive.read_manifest(parent_path,
        expected_manifest_sha256=expected_parent_manifest_sha256)
    next_request = _next_request(parent, request)
    packet = archive.assemble_history(next_request)
    candidate = packet['states']
    preserved = 0
    last = None
    digest = hashlib.sha256(b'[')
    for row in _state_rows(parent_path, parent):
        if preserved >= len(candidate) or row != candidate[preserved]:
            raise HistoricalExperienceError('extension would change or remove an old historical state')
        if preserved:
            digest.update(b',')
        digest.update(archive._bytes(row).rstrip(b'\n'))
        preserved += 1
        last = row['market_date']
    digest.update(b']\n')
    if digest.hexdigest() != parent['states_sha256']:
        raise HistoricalExperienceError('parent canonical state payload digest mismatch')
    coverage = parent.get('coverage', {})
    if (coverage.get('state_rows') != preserved
            or coverage.get('last_observed_date') != last):
        raise HistoricalExperienceError('parent declared coverage disagrees with retained observations')
    additions = candidate[preserved:]
    if any(last is not None and r['market_date'] <= last for r in additions):
        raise HistoricalExperienceError('extension would insert a retroactive historical state')
    # Recheck exact manifest after the source-read/comparison phase. Its identity
    # is evidence, not a promise that a writable directory never changes.
    archive.read_manifest(parent_path, expected_manifest_sha256=expected_parent_manifest_sha256)
    relation = {'schema': EXTENSION_SCHEMA, 'parent_artifact_id': parent['artifact_id'],
        'parent_manifest_sha256': expected_parent_manifest_sha256,
        'parent_states_sha256': parent['states_sha256'], 'preserved_state_rows': preserved,
        'added_state_rows': len(additions), 'parent_last_observed_date': last,
        'first_added_observed_date': additions[0]['market_date'] if additions else None,
        'outcomes_policy': 'separate_new_generation; original_outcome_files_not_read_or_changed'}
    if not additions:
        return {**relation, 'status': 'NO_NEW_OBSERVATIONS', 'output_created': False}
    manifest = packet['manifest']
    manifest['extension'] = relation
    manifest['artifact_id'] = archive._semantic_identity(manifest)
    result = archive.write_archive(packet, destination)
    return {**result, **relation, 'status': 'EXTENDED', 'output_created': True,
        'last_observed_date': manifest['coverage']['last_observed_date'],
        'mode': archive.MODE, 'pit_backtest_eligible': False}
