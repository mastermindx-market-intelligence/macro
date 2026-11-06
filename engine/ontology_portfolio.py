"""Private, ephemeral Portfolio-to-TXI membership through the existing Data OS.

No holdings owner, price model, writes, cache, telemetry or ticker-equality join.
Only unique store symbols enter this reader; shares, costs and notes remain in
Portfolio's browser owner. Membership is a dated screen fact, never P&L.
"""
from __future__ import annotations

from datetime import UTC, date, datetime
import hashlib
import io
import json
from pathlib import Path
import re

from engine import ontology_explorer as explorer
from lib.dataos.identity import VendorAliasTable, parse_id, venue_currency

MAX_REQUEST_BYTES = 65536
_FIELDS = {'schema', 'chain', 'source_manifest_hash', 'symbols'}
_SYMBOL = re.compile(r'[A-Z0-9^][A-Z0-9.^=:_-]{0,63}')
_HASH = re.compile(r'sha256:[a-f0-9]{64}')


class PortfolioInputError(ValueError):
    """Closed error tokens only; never interpolate the private request."""


def validate_request(value: object) -> dict:
    if not isinstance(value, dict) or set(value) != _FIELDS:
        raise PortfolioInputError('invalid_request')
    if value['schema'] != 'ontology_portfolio_request.v1' or value['chain'] not in (
            explorer.DEFAULT_CHAIN, 'dollar_spike_em_multinational'):
        raise PortfolioInputError('invalid_request')
    manifest = value['source_manifest_hash']
    symbols = value['symbols']
    if not isinstance(manifest, str) or not _HASH.fullmatch(manifest):
        raise PortfolioInputError('invalid_request')
    if not isinstance(symbols, list) or len(symbols) > 500:
        raise PortfolioInputError('invalid_request')
    if any(not isinstance(s, str) or not _SYMBOL.fullmatch(s) for s in symbols):
        raise PortfolioInputError('invalid_request')
    if len(set(symbols)) != len(symbols):
        raise PortfolioInputError('invalid_request')
    return {**value, 'symbols': list(symbols)}


def parse_request(raw: bytes) -> dict:
    def unique(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise PortfolioInputError('invalid_request')
            result[k] = v
        return result
    try:
        if not isinstance(raw, bytes) or len(raw) > MAX_REQUEST_BYTES:
            raise PortfolioInputError('invalid_request')
        return validate_request(json.loads(raw, object_pairs_hook=unique))
    except (ValueError, TypeError, UnicodeError, OverflowError) as exc:
        raise PortfolioInputError('invalid_request') from exc


def project_portfolio_read(payload: dict, *, snapshot: dict,
                           aliases: VendorAliasTable | None, identity_date: date) -> dict:
    payload = validate_request(payload)
    source = snapshot['source']
    if source['source_manifest_hash'] != payload['source_manifest_hash']:
        raise PortfolioInputError('snapshot_changed')
    if source['chain'] != payload['chain']:
        raise PortfolioInputError('snapshot_changed')
    exposure = snapshot.get('company_exposure') or {}
    owner_date = exposure.get('asof')
    try:
        historical = date.fromisoformat(owner_date)
        if historical.isoformat() != owner_date or historical > identity_date:
            raise ValueError('owner clock')
    except (TypeError, ValueError):
        raise PortfolioInputError('owner_clock_unavailable') from None

    memberships = {}
    unresolved_channels = []
    available_channels = 0
    for screen in snapshot.get('exposure_screens', []):
        companies = screen.get('companies') or {}
        if screen.get('status') != 'available':
            unresolved_channels.append(screen['id'])
            continue
        available_channels += 1
        if companies.get('unlinked') or companies.get('identity_unavailable'):
            unresolved_channels.append(screen['id'])
        for entry in companies.get('linked', []):
            memberships.setdefault(entry['security_id'], []).append(screen['id'])
    rows = []
    for index, symbol in enumerate(payload['symbols']):
        row = {'index': index, 'symbol': symbol, 'security_id': None, 'currency': None,
               'channels': [], 'state': 'identity_unresolved', 'reason': None}
        if aliases is None:
            row['reason'] = 'identity_source_unavailable'
        else:
            try:
                sid = aliases.resolve('store', symbol, identity_date)
                current = aliases.vendor_symbol_for('store', sid, identity_date) if sid else None
                if not sid:
                    row['reason'] = 'identity_unresolved'
                elif current != symbol or aliases.resolve('store', current, identity_date) != sid:
                    row['reason'] = 'current_alias_not_proven'
                else:
                    kind, listing = parse_id(sid)
                    if kind != 'security':
                        raise ValueError('not security')
                    row['security_id'] = sid
                    row['currency'] = venue_currency(listing.mic)
                    row['channels'] = sorted(set(memberships.get(sid, [])))
                    row['state'] = ('covered' if row['channels'] else
                                    'not_in_available_screens' if available_channels and exposure.get('status') == 'available'
                                    else 'membership_unavailable')
            except (ValueError, TypeError):
                row['security_id'] = None
                row['currency'] = None
                row['channels'] = []
                row['state'] = 'identity_unresolved'
                row['reason'] = 'identity_not_proven'
        rows.append(row)
    counts = {key: sum(r['state'] == key for r in rows)
              for key in ('covered', 'not_in_available_screens', 'identity_unresolved', 'membership_unavailable')}
    return {
        'schema': 'ontology_portfolio_identity.v1',
        'source_manifest_hash': source['source_manifest_hash'], 'chain': source['chain'],
        'membership_asof': owner_date, 'identity_valid_on': identity_date.isoformat(),
        'identity_source_sha256': (exposure.get('identity_source') or {}).get('sha256'),
        'rows': rows, 'counts': counts,
        'membership_state': exposure.get('status', 'unavailable'),
        'membership_reason': exposure.get('reason'),
        'unresolved_channels': sorted(set(unresolved_channels)),
        'meaning': 'declared_screen_membership_only', 'pnl': None,
        'authority': {'can_rank': False, 'can_gate': False, 'can_size': False, 'can_trade': False},
    }


def compose_portfolio_read(root: Path, payload: dict, *, now: datetime | None = None) -> dict:
    payload = validate_request(payload)
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        raise PortfolioInputError('owner_clock_unavailable')
    root = Path(root)
    snapshot = explorer.compose_snapshot(root, chain=payload['chain'], now=now)
    if snapshot['source']['source_manifest_hash'] != payload['source_manifest_hash']:
        raise PortfolioInputError('snapshot_changed')
    identity = snapshot.get('company_exposure', {}).get('identity_source', {})
    aliases = None
    if identity.get('status') == 'available':
        try:
            raw = explorer._read_source(root / explorer._ALIASES_REL)
        except OSError as exc:
            raise explorer.SourceIncoherent('identity_read_changed') from exc
        if len(raw) > explorer.MAX_SOURCE_BYTES or hashlib.sha256(raw).hexdigest() != identity.get('sha256'):
            raise explorer.SourceIncoherent('identity_read_changed')
        try:
            import pyarrow.parquet as parquet
            # Preserve logical null/date values; Pandas3 string-null coercion
            # can turn an unbounded validity date into numeric NaN. The native
            # identity parser must still reject actual non-null numeric NaNs.
            aliases = VendorAliasTable.from_records(parquet.read_table(io.BytesIO(raw)).to_pylist())
        except Exception as exc:
            raise explorer.SourceIncoherent('identity_read_unavailable') from exc
    result = project_portfolio_read(payload, snapshot=snapshot, aliases=aliases,
                                    identity_date=now.astimezone(UTC).date())
    # Match every selected owner byte after the private projection, too. A later
    # ordinary generation is valid for a NEW reading, not this selected one.
    for receipt in snapshot['source']['reads']:
        try:
            raw = explorer._read_source(root / receipt['path'])
        except OSError as exc:
            raise explorer.SourceIncoherent('selected_source_changed') from exc
        if hashlib.sha256(raw).hexdigest() != receipt['sha256']:
            raise explorer.SourceIncoherent('selected_source_changed')
    return result
