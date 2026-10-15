"""Receipt-bound historical experience artifacts, not another data authority.

Reuses the Data OS Tiingo research reader and Market Memory display authority.
Only retrospective exploration is supported. A valid hash proves retained bytes,
not contemporaneous availability, canonical identity, or redistribution rights.
The manifest commits an immutable derived artifact. State reads deliberately do
not touch outcome files. No source archive, live ledger, registry, or timer writes.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from lib.dataos.temporal import utc
from lib.dataos.tiingo_reader import read_research_history
from engine.neuralweb.market_memory import AUTHORITY
from engine.neuralweb.market_memory_history import (
    BASES, FEATURE_VERSION, HISTORY_SCHEMA, HistoricalExperienceError,
    build_daily_rows, build_outcome_rows, select_day,
)

INPUT_SCHEMA = 'market_memory.history_inputs.v1'
ARCHIVE_SCHEMA = 'market_memory.history_archive.v2'
LEGACY_ARCHIVE_SCHEMA = 'market_memory.history_archive.v1'
MODE = 'RETROSPECTIVE_EXPLORATORY'
MAX_MANIFEST_BYTES = 2 * 1024 * 1024
MAX_FILE_BYTES = 256 * 1024 * 1024
MAX_DATE_DECODE_BYTES = 64 * 1024 * 1024
MAX_TOTAL_ROWS = 1_000_000
MAX_SYMBOLS = 64
_HEX = re.compile(r'[a-f0-9]{64}\Z')
_SYMBOL = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,95}\Z')
_FILE = re.compile(r'(states|outcomes)-([0-9]{4})\.parquet\Z')
_FIELDS = frozenset({'schema', 'mode', 'basis', 'benchmark', 'start', 'end',
    'warmup_start', 'capture_cutoff', 'acknowledge_hindsight', 'symbols', 'selection'})


def _bytes(value: Any) -> bytes:
    try:
        return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                           allow_nan=False, ensure_ascii=False) + '\n').encode('utf-8')
    except (ValueError, TypeError, OverflowError) as exc:
        raise HistoricalExperienceError('finite canonical JSON required') from exc


def _hash(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _date(value: Any) -> str:
    if type(value) is not str:
        raise HistoricalExperienceError('canonical ISO market date required')
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError('noncanonical')
    except ValueError as exc:
        raise HistoricalExperienceError('canonical ISO market date required') from exc
    return value


def _validate_request(request: Any) -> dict:
    if type(request) is not dict or set(request) != _FIELDS:
        raise HistoricalExperienceError('exact historical request fields required')
    if len(_bytes(request)) > 128 * 1024:
        raise HistoricalExperienceError('historical request exceeds byte budget')
    if (request['schema'] != INPUT_SCHEMA or request['mode'] != MODE
            or request['acknowledge_hindsight'] is not True):
        raise HistoricalExperienceError('only acknowledged retrospective exploration is admitted')
    if type(request['basis']) is not str or request['basis'] not in BASES:
        raise HistoricalExperienceError('explicit raw or tradj basis required')
    if not (_date(request['warmup_start']) <= _date(request['start']) <= _date(request['end'])):
        raise HistoricalExperienceError('warmup/start/end dates are reversed')
    try:
        cutoff = utc(request['capture_cutoff'])
    except (TypeError, ValueError) as exc:
        raise HistoricalExperienceError('timezone-aware source capture cutoff required') from exc
    if request['end'] > cutoff.date().isoformat():
        raise HistoricalExperienceError('requested market end is after capture cutoff')
    selection = request['selection']
    if type(selection) is not str or not 1 <= len(selection) <= 2000:
        raise HistoricalExperienceError('explicit bounded universe selection description required')
    symbols = request['symbols']
    if type(symbols) is not list or not 1 <= len(symbols) <= MAX_SYMBOLS:
        raise HistoricalExperienceError('one to 64 explicit proxy source selections required')
    names = []
    for item in symbols:
        if type(item) is not dict or set(item) != {'vendor_symbol', 'refs'}:
            raise HistoricalExperienceError('exact vendor-symbol and source-reference fields required')
        symbol = item['vendor_symbol']
        if type(symbol) is not str or not _SYMBOL.fullmatch(symbol) or symbol in names:
            raise HistoricalExperienceError('invalid or duplicate vendor symbol')
        names.append(symbol)
        refs = item['refs']
        if type(refs) is not list or not 1 <= len(refs) <= 32:
            raise HistoricalExperienceError('one to 32 exact source references per proxy required')
        seen = set()
        for ref in refs:
            if (type(ref) is not list or len(ref) != 2 or type(ref[1]) is not str
                    or not _HEX.fullmatch(ref[1])):
                raise HistoricalExperienceError('invalid source date/digest reference')
            _date(ref[0])
            if ref[0] > cutoff.date().isoformat() or tuple(ref) in seen:
                raise HistoricalExperienceError('future or duplicate source reference')
            seen.add(tuple(ref))
    if type(request['benchmark']) is not str or request['benchmark'] not in names:
        raise HistoricalExperienceError('benchmark must be an explicitly selected proxy')
    # Detach before passing to a consumer. Callers cannot alter the retained request.
    return json.loads(_bytes(request))


def _coverage(data: Mapping, request: dict, states: list[dict]) -> dict:
    start, end = request['start'], request['end']
    benchmark_days = {r['market_date'] for r in data[request['benchmark']]
                      if start <= r['market_date'] <= end}
    all_days = sorted({r['market_date'] for r in states})
    by_symbol = {}
    for symbol, rows in data.items():
        days = [r['market_date'] for r in rows if start <= r['market_date'] <= end]
        own = set(days)
        missing = sorted(benchmark_days - own)
        by_symbol[symbol] = {
            'input_observations_including_warmup': len(rows), 'observations': len(days),
            'first_observed_date': days[0] if days else None,
            'last_observed_date': days[-1] if days else None,
            'absent_on_benchmark_observed_dates': len(missing),
            'absent_date_sample': missing[:20], 'absent_sample_truncated': len(missing) > 20,
            'dates_outside_benchmark_observations': len(own - benchmark_days),
            'identity_basis': 'exact_vendor_symbol_not_canonical_historical_identity',
        }
    last = all_days[-1] if all_days else None
    return {'first_observed_date': all_days[0] if all_days else None,
            'last_observed_date': last, 'observed_dates': len(all_days),
            'state_rows': len(states), 'selected_proxy_count': len(data),
            'benchmark_observed_dates': len(benchmark_days),
            'requested_end_after_last_observation': last is None or end > last,
            'market_session_completeness_proven': False,
            'absence_interpretation': 'not an exchange-calendar or listing-inception proof',
            'by_symbol': by_symbol}


def assemble_history(request: dict) -> dict:
    """Read exact existing receipts, then derive a bounded retrospective corpus.

    This accepts no path, provider, network option, source-admission flag, or
    calendar guess. The Data OS reader retains its own archive/mount guard.
    One refused dependency refuses the bundle; no unqualified fallback.
    """
    request = _validate_request(request)
    data, sources = {}, {}
    total = 0
    for item in request['symbols']:
        symbol = item['vendor_symbol']
        remaining = MAX_TOTAL_ROWS - total
        if remaining <= 0:
            raise HistoricalExperienceError('historical input total row budget exceeded')
        history = read_research_history(
            'eod-bars', symbol, item['refs'], request['warmup_start'], request['end'],
            request['capture_cutoff'], acknowledge_hindsight=True,
            max_partitions=32, max_rows=min(100_000, remaining),
        )
        rows = list(history.rows)
        total += len(rows)
        if total > MAX_TOTAL_ROWS:
            raise HistoricalExperienceError('historical input total row budget exceeded')
        data[symbol] = rows
        sources[symbol] = {'reader_metadata': history.metadata(),
                           'source_partitions': [list(ref) for ref in history.source_partitions],
                           'input_rows_sha256': _hash(_bytes(rows)), 'input_rows': len(rows)}
    states = build_daily_rows(data, start=request['start'], end=request['end'],
                              benchmark=request['benchmark'], basis=request['basis'])
    outcomes = build_outcome_rows(data, start=request['start'], end=request['end'],
                                 basis=request['basis'])
    from engine.neuralweb import market_memory_history as features
    source_hashes = {Path(features.__file__).name: _hash(Path(features.__file__).read_bytes()),
                     Path(__file__).name: _hash(Path(__file__).read_bytes())}
    identity = {'request': request, 'sources': sources, 'feature_version': FEATURE_VERSION,
                'source_code_sha256': source_hashes,
                'states_sha256': _hash(_bytes(states)), 'outcomes_sha256': _hash(_bytes(outcomes))}
    manifest = {
        'schema': ARCHIVE_SCHEMA, 'state_schema': HISTORY_SCHEMA,
        'artifact_id': 'mmhist_' + _hash(_bytes(identity)), 'mode': MODE,
        'feature_version': FEATURE_VERSION, 'source_code_sha256': source_hashes,
        'request': request, 'sources': sources, 'scope': 'explicit_vendor_proxy_panel',
        'basis': request['basis'], 'horizon_unit': 'observed_bars_not_exchange_sessions',
        'authority': dict(AUTHORITY), 'pit_backtest_eligible': False,
        'redistribution_admitted': False, 'historical_identity_admitted': False,
        'coverage': _coverage(data, request, states),
        'calculations': {
            'return': 'simple_percent_endpoint_ratio_on_one_declared_price_basis',
            'volatility': 'sample_stddev_21_simple_percent_returns_22_prices_unannualized',
            'drawdown': 'current_close_vs_maximum_of_last_252_observed_closes',
            'forward_max_drawdown': 'minimum_future_close_vs_entry_close_not_peak_to_trough',
            'volume_ratio': 'current_raw_volume_vs_mean_of_previous_20_raw_volume_observations',
            'relative_return': 'own_21_observation_return_minus_benchmark_same_endpoint_dates',
        },
        'states_sha256': identity['states_sha256'], 'outcomes_sha256': identity['outcomes_sha256'],
        'limitations': [
            'Historical source values were captured later; not what Mastermind emitted then.',
            'Corporate-action and correction vintages are those of the selected captures.',
            'Proxy selection is not whole-market breadth or a survivorship-safe universe.',
            'No original consensus, catalysts, macro release times, quotes or options are inferred.',
            'Missing observations are not forward-filled; unobserved sessions are not invented.',
            'No signal validation, probability calibration, position sizing or trade authority.',
        ],
    }
    manifest['artifact_id'] = _semantic_identity(manifest)
    return {'manifest': manifest, 'states': states, 'outcomes': outcomes}


def _semantic_identity(manifest: dict) -> str:
    if manifest.get('schema') == LEGACY_ARCHIVE_SCHEMA:
        # Retain compatibility with the exact first build, not a retroactive
        # assertion that its metadata used the stronger v2 identity closure.
        keys = ('request', 'sources', 'feature_version', 'source_code_sha256',
                'states_sha256', 'outcomes_sha256')
        if not all(k in manifest for k in keys):
            raise HistoricalExperienceError('legacy historical identity fields missing')
        semantic = {k: manifest[k] for k in keys}
    else:
        semantic = {k: v for k, v in manifest.items()
                    if k not in {'artifact_id', 'files', 'storage'}}
    return 'mmhist_' + _hash(_bytes(semantic))


def _validate_semantics(manifest: dict, *, allow_legacy: bool) -> None:
    schemas = {ARCHIVE_SCHEMA, LEGACY_ARCHIVE_SCHEMA} if allow_legacy else {ARCHIVE_SCHEMA}
    if (type(manifest) is not dict or manifest.get('schema') not in schemas
            or manifest.get('mode') != MODE
            or any(manifest.get(k) is not False for k in (
                'pit_backtest_eligible', 'redistribution_admitted', 'historical_identity_admitted'))
            or manifest.get('scope') != 'explicit_vendor_proxy_panel'
            or manifest.get('horizon_unit') != 'observed_bars_not_exchange_sessions'
            or manifest.get('authority') != dict(AUTHORITY)):
        raise HistoricalExperienceError('historical manifest cannot grant admission')
    request = _validate_request(manifest.get('request'))
    feature = manifest.get('feature_version')
    code = manifest.get('source_code_sha256')
    if (manifest.get('state_schema') != HISTORY_SCHEMA
            or type(feature) is not str or not 1 <= len(feature) <= 128
            or type(code) is not dict or not 1 <= len(code) <= 16
            or any(type(k) is not str or not 1 <= len(k) <= 120
                   or type(v) is not str or not _HEX.fullmatch(v) for k, v in code.items())
            or any(type(manifest.get(k)) is not str or not _HEX.fullmatch(manifest[k])
                   for k in ('states_sha256', 'outcomes_sha256'))):
        raise HistoricalExperienceError('historical calculation vintage or read contract invalid')
    sources = manifest.get('sources')
    if (type(sources) is not dict
            or set(sources) != {item['vendor_symbol'] for item in request['symbols']}):
        raise HistoricalExperienceError('historical source provenance missing or inconsistent')
    for source in sources.values():
        if (type(source) is not dict or type(source.get('reader_metadata')) is not dict
                or type(source.get('input_rows')) is not int
                or not 0 <= source['input_rows'] <= MAX_TOTAL_ROWS
                or type(source.get('input_rows_sha256')) is not str
                or not _HEX.fullmatch(source['input_rows_sha256'])
                or type(source.get('source_partitions')) is not list
                or not 1 <= len(source['source_partitions']) <= 32):
            raise HistoricalExperienceError('historical source provenance invalid')
        for ref in source['source_partitions']:
            if (type(ref) is not list or len(ref) != 2 or type(ref[1]) is not str
                    or not _HEX.fullmatch(ref[1])):
                raise HistoricalExperienceError('historical source partition invalid')
            _date(ref[0])
    if manifest.get('basis') != request['basis']:
        raise HistoricalExperienceError('historical manifest price basis disagrees with source selection')
    if manifest.get('artifact_id') != _semantic_identity(manifest):
        raise HistoricalExperienceError('historical semantic identity mismatch')


def _regular_file(root: Path, name: str, limit: int) -> bytes:
    if type(name) is not str or Path(name).name != name:
        raise HistoricalExperienceError('artifact path must be a single local filename')
    path = root / name
    try:
        if root.is_symlink() or path.is_symlink() or not path.is_file():
            raise HistoricalExperienceError('artifact must be a regular non-symlink file')
        before = path.stat()
        if before.st_nlink != 1 or before.st_size > limit:
            raise HistoricalExperienceError('artifact file exceeds budget or aliases another file')
        with path.open('rb') as handle:
            payload = handle.read(limit + 1)
        after = path.stat()
    except OSError as exc:
        raise HistoricalExperienceError('artifact unavailable') from exc
    if (len(payload) > limit or len(payload) != before.st_size
            or (before.st_ino, before.st_dev, before.st_mtime_ns, before.st_ctime_ns)
            != (after.st_ino, after.st_dev, after.st_mtime_ns, after.st_ctime_ns)):
        raise HistoricalExperienceError('artifact changed during read')
    return payload


def _write_exclusive(path: Path, payload: bytes) -> None:
    import os
    with path.open('xb') as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def write_archive(packet: dict, destination: Path) -> dict:
    """Write a new immutable derived artifact. Manifest-last is its commit marker.

    An interrupted destination stays inspectable but not readable as a committed
    artifact. Never overwrite, remove or blindly resume an existing destination.
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    if type(packet) is not dict or set(packet) != {'manifest', 'states', 'outcomes'}:
        raise HistoricalExperienceError('exact assembled history packet required')
    manifest = json.loads(_bytes(packet['manifest']))
    _validate_semantics(manifest, allow_legacy=False)
    for kind in ('states', 'outcomes'):
        rows = packet[kind]
        if type(rows) is not list or len(rows) > MAX_TOTAL_ROWS:
            raise HistoricalExperienceError('historical artifact row budget exceeded')
        if _hash(_bytes(rows)) != manifest.get(kind + '_sha256'):
            raise HistoricalExperienceError('assembled historical payload changed')
    destination = Path(destination)
    if destination.is_symlink() or any(p.is_symlink() for p in destination.parents):
        raise HistoricalExperienceError('artifact destination cannot traverse symlinks')
    destination.mkdir(mode=0o700, parents=False, exist_ok=False)
    files = []
    for kind in ('states', 'outcomes'):
        rows = packet[kind]
        for year in sorted({r['market_date'][:4] for r in rows}):
            selected = [r for r in rows if r['market_date'].startswith(year + '-')]
            columns = sorted(set().union(*(r.keys() for r in selected)))
            fields = [pa.field(k, pa.string() if k in ('market_date', 'vendor_symbol', 'missing')
                               else pa.int64() if k == 'volume_raw' else pa.float64()) for k in columns]
            normalized = [{**r, 'missing': _bytes(r['missing']).decode().strip()} for r in selected]
            table = pa.Table.from_pylist(normalized, schema=pa.schema(fields))
            sink = pa.BufferOutputStream()
            pq.write_table(table, sink, compression='zstd', use_dictionary=['vendor_symbol'],
                           row_group_size=65536, write_statistics=True)
            content = sink.getvalue().to_pybytes()
            if len(content) > MAX_FILE_BYTES:
                raise HistoricalExperienceError('derived yearly file exceeds byte budget')
            name = f'{kind}-{year}.parquet'
            _write_exclusive(destination / name, content)
            files.append({'name': name, 'kind': kind, 'year': year, 'rows': len(selected),
                          'bytes': len(content), 'sha256': _hash(content)})
    manifest['files'] = files
    manifest['storage'] = {'format': 'parquet', 'compression': 'zstd',
                           'partition': 'kind/year', 'data_bytes': sum(f['bytes'] for f in files)}
    payload = _bytes(manifest)
    if len(payload) > MAX_MANIFEST_BYTES:
        raise HistoricalExperienceError('historical manifest exceeds byte budget')
    _write_exclusive(destination / 'manifest.json', payload)
    return {'artifact_id': manifest['artifact_id'], 'manifest_sha256': _hash(payload),
            'data_bytes': manifest['storage']['data_bytes'], 'manifest_bytes': len(payload),
            'files': len(files), 'state_rows': len(packet['states']),
            'outcome_rows': len(packet['outcomes'])}


def read_manifest(root: Path, *, expected_manifest_sha256: str) -> dict:
    if type(expected_manifest_sha256) is not str or not _HEX.fullmatch(expected_manifest_sha256):
        raise HistoricalExperienceError('exact retained manifest SHA-256 required')
    payload = _regular_file(Path(root), 'manifest.json', MAX_MANIFEST_BYTES)
    return _manifest_payload(payload, expected_manifest_sha256)


def _manifest_payload(payload: bytes, expected_manifest_sha256: str) -> dict:
    if type(payload) is not bytes or len(payload) > MAX_MANIFEST_BYTES:
        raise HistoricalExperienceError('historical manifest bytes exceed budget')
    if type(expected_manifest_sha256) is not str or not _HEX.fullmatch(expected_manifest_sha256):
        raise HistoricalExperienceError('exact retained manifest SHA-256 required')
    if _hash(payload) != expected_manifest_sha256:
        raise HistoricalExperienceError('retained manifest digest mismatch')
    try:
        manifest = json.loads(payload)
    except (ValueError, UnicodeError) as exc:
        raise HistoricalExperienceError('invalid history manifest') from exc
    _validate_semantics(manifest, allow_legacy=True)
    files = manifest.get('files')
    if type(files) is not list or len(files) > 300:
        raise HistoricalExperienceError('bounded artifact file manifest required')
    names = set()
    for item in files:
        if type(item) is not dict or set(item) != {'name','kind','year','rows','bytes','sha256'}:
            raise HistoricalExperienceError('invalid artifact file record')
        name = item['name']
        match = _FILE.fullmatch(name) if type(name) is str else None
        if (not match or name in names or match.groups() != (item['kind'],item['year'])
                or type(item['sha256']) is not str or not _HEX.fullmatch(item['sha256'])
                or type(item['bytes']) is not int or not 1 <= item['bytes'] <= MAX_FILE_BYTES
                or type(item['rows']) is not int or not 1 <= item['rows'] <= MAX_TOTAL_ROWS):
            raise HistoricalExperienceError('invalid artifact filename, hash or budget')
        names.add(name)
    return manifest


def _read_rows(root: Path, item: dict, target: str) -> list[dict]:
    return _row_payload(_regular_file(root, item['name'], MAX_FILE_BYTES), item, target)


def _row_payload(payload: bytes, item: dict, target: str) -> list[dict]:
    import pyarrow as pa
    import pyarrow.parquet as pq
    if type(payload) is not bytes or len(payload) > MAX_FILE_BYTES:
        raise HistoricalExperienceError('historical data bytes exceed budget')
    if len(payload) != item['bytes'] or _hash(payload) != item['sha256']:
        raise HistoricalExperienceError('historical data file digest mismatch')
    try:
        pf = pq.ParquetFile(pa.BufferReader(payload), pre_buffer=False)
        try:
            if pf.metadata.num_rows != item['rows']:
                raise HistoricalExperienceError('historical row count mismatch')
            decoded_size = sum(pf.metadata.row_group(i).total_byte_size
                               for i in range(pf.metadata.num_row_groups))
            if decoded_size > MAX_DATE_DECODE_BYTES:
                raise HistoricalExperienceError('historical decoded size exceeds budget')
            # One bounded local file does not need the asynchronous dataset scanner.
            # Its deferred Python-buffer cleanup can race interpreter finalization
            # (observed on Arrow25/Python3.14). Finish decoding before returning.
            table = pf.read(use_threads=False)
        finally:
            pf.close()
        import pyarrow.compute as pc
        table = table.filter(pc.equal(table['market_date'], pa.scalar(target)))
        if table.num_rows > MAX_SYMBOLS:
            raise HistoricalExperienceError('date slice exceeds proxy universe budget')
        rows = table.to_pylist()
        for row in rows:
            row['missing'] = json.loads(row['missing'])
            if row['market_date'] != target:
                raise HistoricalExperienceError('historical date filter mismatch')
    except HistoricalExperienceError:
        raise
    except (ValueError, TypeError, KeyError, OSError) as exc:
        raise HistoricalExperienceError('invalid historical data file') from exc
    return rows


def _compact_source_references(sources: dict) -> dict:
    # Full provenance remains in the exact hash-bound manifest. Repeating all
    # capture partitions in every day response made admitted archives impossible
    # to serve through the existing bounded Data & Lab transport.
    return {symbol: {
        'source_partition_count': len(source['source_partitions']),
        'source_partitions_sha256': _hash(_bytes(source['source_partitions'])),
        'input_rows': source['input_rows'],
        'input_rows_sha256': source['input_rows_sha256'],
        'reader_metadata_sha256': _hash(_bytes(source['reader_metadata'])),
    } for symbol, source in sources.items()}


def read_day(root: Path, market_date: str, *, expected_manifest_sha256: str,
             reveal_outcomes: bool = False) -> dict:
    root = Path(root)
    return read_day_from_reader(lambda name, limit: _regular_file(root, name, limit),
                               market_date, expected_manifest_sha256=expected_manifest_sha256,
                               reveal_outcomes=reveal_outcomes)


def read_day_from_reader(read_file, market_date: str, *, expected_manifest_sha256: str,
                         reveal_outcomes: bool = False) -> dict:
    """Decode through an existing admitted source owner, not a new path resolver.

    The callback is application code, never a user-supplied JSON field. Data &
    Lab supplies its existing descriptor-confined, read-only file owner. Local
    archive readers supply _regular_file. Both use identical validation below.
    """
    target = _date(market_date)
    if type(reveal_outcomes) is not bool:
        raise HistoricalExperienceError('outcome reveal must be an explicit boolean')
    if type(expected_manifest_sha256) is not str or not _HEX.fullmatch(expected_manifest_sha256):
        raise HistoricalExperienceError('exact retained manifest SHA-256 required')
    manifest = _manifest_payload(read_file('manifest.json', MAX_MANIFEST_BYTES), expected_manifest_sha256)
    matching = {r['kind']:r for r in manifest['files'] if r['year'] == target[:4]}
    rows = _row_payload(read_file(matching['states']['name'], MAX_FILE_BYTES), matching['states'], target) if 'states' in matching else []
    rows = select_day(rows, target)
    result = {'schema': HISTORY_SCHEMA, 'mode': MODE, 'artifact_id': manifest['artifact_id'],
              'manifest_sha256': expected_manifest_sha256, 'market_date': target,
              'status': 'OBSERVED' if rows else 'NO_OBSERVATION', 'rows': rows,
              'basis': manifest['basis'], 'pit_backtest_eligible': False,
              'redistribution_admitted': False, 'authority': dict(AUTHORITY),
              'horizon_unit': manifest['horizon_unit'],
              'feature_version': manifest['feature_version'],
              'reader_feature_version': FEATURE_VERSION,
              'feature_version_matches_reader': manifest['feature_version'] == FEATURE_VERSION,
              'source_code_sha256': manifest['source_code_sha256'],
              'source_reference_detail': 'compact_digests; full_detail_in_retained_manifest',
              'source_references': _compact_source_references(manifest['sources'])}
    if reveal_outcomes:
        result['outcomes'] = _row_payload(read_file(matching['outcomes']['name'], MAX_FILE_BYTES), matching['outcomes'], target) if 'outcomes' in matching else []
    return result
