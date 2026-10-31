"""Explicit selected-identity continuation into the existing house Theme Map.

No graph/identity writer, symbol resolution, vendor display, or owner replacement.
Graph paths use the selected Explorer clocks; identity is latest published only.
"""
from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import io
import json
import re
from pathlib import Path
from types import SimpleNamespace

import yaml

from engine import ontology_explorer as explorer
from engine.theme_graph import identity_resolution, security_navigation, store, rights
from engine.theme_graph.ontology import _clock_instant

METHOD = 'ontology_house_theme_continuation.v1'
MAX_GRAPH_BYTES = 32 * 1024 * 1024
MAX_GRAPH_ROWS = 250000
_FIELDS = {'schema', 'chain', 'source_manifest_hash', 'identity_kind', 'identity_id'}
_TABLES = {
    'nodes': store.NODE_COLUMNS,
    'edges': store.EDGE_COLUMNS,
    'evidence': store.EVIDENCE_COLUMNS,
    'node_lifecycle': store.NODE_LIFECYCLE_COLUMNS,
    'identity_resolution': store.IDENTITY_RESOLUTION_COLUMNS,
}


class ThemeInputError(ValueError):
    """Closed reason tokens, with no private input or owner payload."""


def validate_request(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != _FIELDS:
        raise ThemeInputError('invalid_request')
    if (payload['schema'] != 'ontology_theme_request.v1'
            or not isinstance(payload['chain'], str)
            or not re.fullmatch(r'[a-z0-9][a-z0-9_]{0,80}', payload['chain'])
            or not isinstance(payload['source_manifest_hash'], str)
            or not re.fullmatch(r'sha256:[0-9a-f]{64}', payload['source_manifest_hash'])):
        raise ThemeInputError('invalid_request')
    prefix = {'security': 'SEC:', 'issuer': 'ISS:'}.get(payload['identity_kind']) if isinstance(payload['identity_kind'], str) else None
    identity = payload['identity_id']
    if (prefix is None or not isinstance(identity, str) or not identity.startswith(prefix)
            or not len(prefix) < len(identity) <= 512
            or any(c.isspace() or ord(c) < 32 for c in identity)):
        raise ThemeInputError('invalid_request')
    return dict(payload)


def _read(root: Path, rel: str) -> bytes:
    # Bound allocation as well as the eventual serialized response. Fixed owner
    # paths only; no client-controlled path is used in a filesystem operation.
    with (root / rel).open('rb') as stream:
        raw = stream.read(MAX_GRAPH_BYTES + 1)
    if len(raw) > MAX_GRAPH_BYTES:
        raise explorer.SourceUnavailable('theme_source_exceeds_bound')
    return raw


def compose_theme_continuation(root: Path | str, payload: dict, *, now: datetime | None = None) -> dict:
    payload = validate_request(payload)
    root = Path(root)
    now = (now or datetime.now(UTC)).astimezone(UTC)
    snapshot = explorer.compose_snapshot(root, chain=payload['chain'], now=now)
    source = snapshot['source']
    if source['source_manifest_hash'] != payload['source_manifest_hash']:
        raise ThemeInputError('snapshot_changed')
    try:
        # The owner observation clock is a calendar date, never a week date,
        # timestamp or local-zone instant silently coerced into one.
        if not isinstance(source['asof'], str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', source['asof']):
            raise ValueError('observation date')
        effective = datetime.strptime(source['asof'], '%Y-%m-%d').date()
        cutoff = explorer._parse_build_stamp(source['built'])
        if (cutoff is None or cutoff.tzinfo is None or cutoff > now
                or effective > now.date() or effective > cutoff.date()):
            raise ValueError('clock')
    except (TypeError, ValueError, KeyError):
        raise explorer.SourceUnavailable('theme_owner_clock_unavailable') from None
    raw_sources = {}
    frames = {}
    try:
        import pyarrow.parquet as parquet
        import pandas as pd
        for name, columns in _TABLES.items():
            rel = f'data/theme_graph/{name}.parquet'
            raw_sources[rel] = _read(root, rel)
            table = parquet.read_table(io.BytesIO(raw_sources[rel]))
            if table.num_rows > MAX_GRAPH_ROWS or set(columns) - set(table.column_names):
                raise ValueError('graph shape')
            frames[name] = table.to_pylist()
        # The existing owner's latest-published view: stable max computed_at per
        # node, with no as-of identity re-resolution or symbol join.
        identities = pd.DataFrame(frames['identity_resolution'], columns=store.IDENTITY_RESOLUTION_COLUMNS)
        identities = identities.sort_values(['node_id', 'computed_at'], kind='stable').drop_duplicates('node_id', keep='last')
        identities = identities.sort_values('node_id', kind='stable').to_dict('records')
        matches = [r for r in identities if r.get(payload['identity_kind'] + '_id') == payload['identity_id']]
        if len(matches) > 64:
            raise ValueError('binding bound')
        for row in matches:
            if (_clock_instant(row['computed_at'], 'computed_at') > now
                    or datetime.fromisoformat(row['resolution_asof']).date() > now.date()):
                raise ValueError('future identity')
        # A separate data estate may contain a policy copy. It cannot grant
        # rights: require byte equality with the actual code-owned authority,
        # freshly read before and after composition (never its memoized loader).
        policy_rel = 'config/theme_sources.yml'
        raw_sources[policy_rel] = _read(root, policy_rel)
        authority_path = rights.registry_path()
        authority_raw = _read(authority_path.parent, authority_path.name)
        if raw_sources[policy_rel] != authority_raw:
            raise ValueError('policy authority differs')
        policy = yaml.safe_load(raw_sources[policy_rel])
        house = policy['families']['mastermind_curated']
        if (not isinstance(house, dict) or house.get('rights_class') not in rights.EMISSION_OK
                or house.get('auth_class') != 'house'):
            raise ValueError('house display not permitted')
        view = SimpleNamespace(read_nodes=lambda: frames['nodes'],
            read_edges=lambda: frames['edges'], read_node_lifecycle=lambda: frames['node_lifecycle'],
            read_evidence=lambda: frames['evidence'])
        result = security_navigation.compose_security_hierarchy(view, identities,
            identity_kind=payload['identity_kind'], identity_id=payload['identity_id'],
            asof=effective, knowledge_cutoff=cutoff, source_policy=policy)
        # The native cached reader may conservatively withhold a path. It must
        # not label admitted house output with an obsolete rights class.
        for binding in result['bindings']:
            for path in binding['paths']:
                for node in path['path'] + [hop['node'] for hop in path['via']]:
                    node['rights']['rights_class'] = house['rights_class']
        tracking = result['etf_tracking']
        refs = tracking['references']
        if refs:
            identity_sources = {}
            try:
                for rel in ('data/reference/_receipt.json', 'data/reference/security_master.parquet',
                            'data/reference/vendor_aliases.parquet'):
                    identity_sources[rel] = _read(root, rel)
                day = json.loads(identity_sources['data/reference/_receipt.json'])['symbol_directory_snapshot']
                if not isinstance(day, str) or datetime.fromisoformat(day).date().isoformat() != day:
                    raise ValueError('listing source clock')
                for rel in (f'data/symbol_directory/snapshots/{day}.parquet',
                            f'data/symbol_directory/receipts/snapshots/{day}.json'):
                    identity_sources[rel] = _read(root, rel)
                adopted = identity_resolution.adopt_etf_references(frames['nodes'], frames['node_lifecycle'],
                    [r['etf_node_id'] for r in refs], identity_sources, now=now)
            except (OSError, ValueError, KeyError, TypeError):
                adopted = {}
            # Bind every observed identity byte in the same rechecked manifest,
            # including a failed/partial owner observation. Never keep old IDs.
            raw_sources.update(identity_sources)
            for ref in refs:
                ref['security_identity'] = adopted.get(ref['etf_node_id'],
                    {'status': 'unavailable', 'reason': 'ETF_IDENTITY_INPUTS_UNAVAILABLE'})
            available = sum(r['security_identity']['status'] == 'available' for r in refs)
            tracking['security_identity'] = {'status': 'available' if available == len(refs)
                else 'partial' if available else 'unavailable',
                'reason': None if available == len(refs) else 'ETF_IDENTITY_NOT_FULLY_RESOLVED'}
    except (OSError, ValueError, TypeError, KeyError, RecursionError, yaml.YAMLError, rights.RightsRefusal):
        raise explorer.SourceUnavailable('theme_owner_unavailable') from None
    receipts = [{'path': rel, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
                for rel, raw in sorted(raw_sources.items())]
    # Nothing private or partial escapes after either source plane changes.
    for receipt in source['reads'] + receipts:
        try:
            raw = _read(root, receipt['path'])
        except OSError:
            raise explorer.SourceIncoherent('theme_source_changed') from None
        if hashlib.sha256(raw).hexdigest() != receipt['sha256']:
            raise explorer.SourceIncoherent('theme_source_changed')
    try:
        if _read(authority_path.parent, authority_path.name) != authority_raw:
            raise explorer.SourceIncoherent('theme_policy_changed')
    except OSError:
        raise explorer.SourceIncoherent('theme_policy_changed') from None
    return {'schema': 'ontology_theme_continuation.v1', 'source': {
        'chain': source['chain'], 'asof': source['asof'], 'built': source['built'],
        'source_manifest_hash': source['source_manifest_hash'], 'method': METHOD,
        'theme_source_manifest_hash': explorer.manifest_hash_for(receipts, method=METHOD),
        'policy_binding': 'AUTHORITATIVE_CODE_REGISTRY_EQUALS_SELECTED_SOURCE',
        'reads': receipts,
    }, 'selection': {'identity_kind': payload['identity_kind'], 'identity_id': payload['identity_id']},
        'theme_map': result}
