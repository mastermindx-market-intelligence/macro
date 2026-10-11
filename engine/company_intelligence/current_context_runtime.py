"""Read-only installed Data OS generation for the private company context route.

The incumbent deployment selects HEAD; the incumbent identity producer owns the
four reference artifacts. This adapter neither fetches nor publishes anything.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from io import BytesIO
import json
import os
from pathlib import Path
import re
import subprocess
from threading import RLock

from engine.company_intelligence import current_company_context as context
from lib.dataos.identity import (IssuerMaster, VendorAliasTable, parse_id, parse_listing_key,
                                 security_id, issuer_id)
from lib.dataos.registry import DatasetContract, Registry, validate_registry

_PURPOSE = 'private_company_intelligence_context'
_AUDIENCE = 'company_intelligence_entitled'
_PRODUCER = 'scripts/build_security_master.py'
_ARTIFACTS = {name: f'data/reference/{name}.parquet' for name in context._NAMES}
_RECEIPT = 'data/reference/_receipt.json'
_REGISTRY = 'config/dataset_registry.yml'
_PATHS = (*_ARTIFACTS.values(), _RECEIPT)
_OID = re.compile(r'[0-9a-f]{40}\Z')
_MAX_BYTES = context.MAX_REFERENCE_BYTES


def _require(value: bool) -> None:
    context._require(value)


def _qualify_registry(raw: bytes) -> None:
    import yaml
    payload = yaml.safe_load(raw)
    _require(type(payload) is dict and type(payload.get('datasets')) is list)
    names = {f'reference.{name}' for name in _ARTIFACTS}
    rows = [row for row in payload['datasets']
            if type(row) is dict and row.get('dataset_id') in names]
    registry = Registry(DatasetContract.from_mapping(row) for row in rows)
    _require(len(rows) == 3 and not validate_registry(registry))
    # Validate the real adopted contracts, not a parallel registry or a fixture.
    for name, path in _ARTIFACTS.items():
        row = registry.get(f'reference.{name}')
        _require(row is not None and row.status.value == 'PRODUCED'
                 and row.owner == 'macro-dashboard' and row.producer == _PRODUCER
                 and row.storage == path and row.format == 'parquet'
                 and row.frequency == 'on_demand')


def _qualify_bundle(blobs: dict[str, bytes]) -> None:
    import pandas as pd
    receipt = json.loads(blobs[_RECEIPT])
    _require(type(receipt) is dict and receipt.get('producer') == _PRODUCER
             and receipt.get('notes') == [])
    ids = receipt.get('dataset_ids')
    _require(type(ids) is list and all(f'reference.{n}' in ids for n in _ARTIFACTS))
    authority = receipt.get('authority')
    _require(type(authority) is dict
             and authority.get('identity_authority') == 'canonical_exact_identity'
             and all(authority.get(k) == 'none'
                     for k in ['signal_authority', 'ranking_authority', 'trade_authority'])
             and type(authority.get('consumers')) is list
             and 'gmi.identity_resolution/v1' in authority['consumers'])
    generated = datetime.fromisoformat(receipt['generated_at'])
    # The incumbent producer's _iso_now serializes naive UTC.
    generated = generated.replace(tzinfo=timezone.utc) if generated.tzinfo is None else generated
    _require(generated <= datetime.now(timezone.utc))
    counts = receipt.get('row_counts')
    _require(type(counts) is dict)
    rows = {name: pd.read_parquet(BytesIO(blobs[path])).to_dict('records')
            for name, path in _ARTIFACTS.items()}
    for name, values in rows.items():
        _require(type(counts.get(name)) is int and counts[name] == len(values))
    securities = context._unique(rows['security_master'], 'security_id')
    issuers = context._unique(rows['issuer_master'], 'issuer_id')
    # Use the existing readers to validate their canonical input contracts.
    IssuerMaster.from_records(rows['security_master'])
    table = VendorAliasTable.from_records(rows['vendor_aliases'])
    _require(counts.get('vendor_alias_rows_readable') == len(table.rows))
    census = Counter()
    for sid, row in securities.items():
        kind, key = parse_id(sid)
        _require(kind == 'security' and security_id(key) == sid)
        listing = context._text(row.get('listing_key'))
        if listing is not None:
            parsed = parse_listing_key(listing)
            _require(parsed.render() == listing and security_id(parsed) == sid)
        iid = context._text(row.get('issuer_id'))
        if iid is not None:
            kind, key = parse_id(iid)
            _require(kind == 'issuer' and issuer_id(key) == iid)
        # The incumbent producer excludes superseded security tombstones from
        # issuer membership, but retains them for security/alias references.
        if context._text(row.get('security_state')):
            continue
        if iid is not None:
            _require(iid in issuers)
            census[iid] += 1
            cik = context._text(row.get('issuer_cik'))
            # An unresolved member may lack CIK. Never manufacture evidence or
            # reject that permitted absence; all evidenced links must agree.
            if cik is not None or row.get('issuer_state') == 'RESOLVED':
                _require(cik is not None and bool(re.fullmatch(r'[0-9]{10}', cik))
                         and int(cik) > 0 and cik == context._text(issuers[iid].get('cik')))
    _require(set(census) == set(issuers))
    for iid, row in issuers.items():
        kind, key = parse_id(iid)
        _require(kind == 'issuer' and issuer_id(key) == iid)
        _require(type(row.get('n_securities')) is int and row['n_securities'] == census[iid])
    for row in rows['vendor_aliases']:
        _require(context._text(row.get('security_id')) in securities)


class CommittedCompanyContextOwner:
    """Follow the installed protected tree, with immutable, bounded Git reads.

    repo comes only from the existing application deployment configuration.
    Missing local objects and unsupported Git guards fail closed. No network,
    worktree writes, lock recovery, producer invocation or private Store exists.
    """
    def __init__(self, repo: Path):
        self.repo = Path(repo)
        self._lock = RLock()
        self._cached_key = None
        self._cached_bundle = None

    def _git(self, *args: str, data: bytes | None = None) -> bytes:
        # -C does not override GIT_DIR/object/config environment redirection.
        # Keep the configured deployment root and ordinary installed Git config;
        # no request inherits another process's repository selection.
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        env.update(GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0',
                   GIT_NO_LAZY_FETCH='1', GIT_ALLOW_PROTOCOL='')
        # Git2.43 lacks --no-lazy-fetch. The empty protocol whitelist overrides
        # even an explicit per-protocol allow, preventing all retrieval when old
        # Git ignores the newer lazy-fetch variable. Never retry unguarded.
        result = subprocess.run(
            ['git', '--no-replace-objects', '-C', str(self.repo), *args],
            input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=3, check=True, env=env)
        _require(len(result.stdout) <= 5 * _MAX_BYTES + 4096)
        return result.stdout

    def _head(self) -> str:
        value = self._git('rev-parse', '--verify', 'HEAD^{commit}').decode().strip()
        _require(bool(_OID.fullmatch(value)))
        return value

    def _objects(self, commit: str, paths: tuple[str, ...]) -> dict[str, tuple[str, int]]:
        raw = self._git('ls-tree', '-l', '-z', commit, '--', *paths)
        result = {}
        for entry in raw.split(b'\0'):
            if not entry:
                continue
            header, name = entry.split(b'\t', 1)
            mode, kind, oid, size = header.split()
            path = name.decode()
            _require(path in paths and path not in result and mode == b'100644'
                     and kind == b'blob' and bool(_OID.fullmatch(oid.decode())))
            length = int(size)
            _require(0 < length <= _MAX_BYTES)
            result[path] = (oid.decode(), length)
        _require(set(result) == set(paths))
        return result

    def _read(self, objects: dict[str, tuple[str, int]]) -> dict[str, bytes]:
        raw = self._git('cat-file', '--batch', data=''.join(
            f'{oid}\n' for oid, _ in objects.values()).encode())
        blobs = {}
        offset = 0
        for path, (oid, length) in objects.items():
            stop = raw.index(b'\n', offset)
            _require(raw[offset:stop] == f'{oid} blob {length}'.encode())
            offset = stop + 1
            blobs[path] = raw[offset:offset + length]
            _require(len(blobs[path]) == length and raw[offset + length:offset + length + 1] == b'\n')
            offset += length + 1
        _require(offset == len(raw))
        return blobs

    def current_identity_bundle(self, purpose: str, audience: str) -> context.IdentityBundle | None:
        if (purpose, audience) != (_PURPOSE, _AUDIENCE):
            return None
        try:
            with self._lock:
                head = self._head()
                self._git('merge-base', '--is-ancestor', head, 'refs/remotes/origin/main')
                generation = self._git('log', '-1', '--format=%H', head, '--', *_PATHS).decode().strip()
                _require(bool(_OID.fullmatch(generation)))
                current = self._objects(head, (*_PATHS, _REGISTRY))
                selected = self._objects(generation, _PATHS)
                # Include the producer receipt: receipt-only corrections revoke
                # the old qualification even if the three Parquets are identical.
                _require(all(current[path] == selected[path] for path in _PATHS))
                key = (generation, tuple(sorted(current.items())))
                if key != self._cached_key:
                    blobs = self._read(current)
                    _qualify_registry(blobs[_REGISTRY])
                    _qualify_bundle(blobs)
                    bundle = context.IdentityBundle(generation, **{
                        name: blobs[path] for name, path in _ARTIFACTS.items()})
                    bundle.validate()
                    self._cached_key, self._cached_bundle = key, bundle
                _require(self._head() == head)
                return self._cached_bundle
        except (OSError, ValueError, KeyError, TypeError, AttributeError,
                subprocess.SubprocessError, context.native.DisclosureError):
            return None
