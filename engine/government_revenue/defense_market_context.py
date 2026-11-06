"""Pure current-context projection of the incumbent canonical daily price owner.

The trusted publisher supplies admitted, sealed owner bytes. This module does
not acquire, publish, authenticate a caller, grant rights or allocate identity.
It quotes the incumbent chg_1d calculation with distinct bar/version/read clocks.
"""
from __future__ import annotations
from datetime import date, datetime
from hashlib import sha256, md5
from io import BytesIO
import json
import math
import re
import pandas as pd
from engine.stock_technicals import chg_1d
from lib import nyse_calendar
from lib.dataos.identity import VendorAliasTable, IssuerMaster, parse_listing_key
from engine.company_intelligence.contracts import canonical_json_bytes
from engine.company_intelligence.identity import company_id_for_cik, security_id_for
from engine.company_intelligence.event_workspace import select_current_event_from_aliases
from engine.government_revenue.defense_economics import COHORT

_REFERENCE_FILES = {
    'security_master_bytes': 'data/reference/security_master.parquet',
    'vendor_aliases_bytes': 'data/reference/vendor_aliases.parquet',
    'issuer_master_bytes': 'data/reference/issuer_master.parquet',
    'receipt_bytes': 'data/reference/_receipt.json',
}
_SHA = re.compile(r'[0-9a-f]{64}\Z')
_MAX_BYTES = 16 * 1024 * 1024

def _require(condition, reason):
    if not condition:
        raise ValueError(reason)

def _clock(value):
    _require(isinstance(value, str), 'owner_clock_missing')
    clock = datetime.fromisoformat(value.replace('Z', '+00:00'))
    _require(clock.tzinfo is not None, 'owner_clock_requires_timezone')
    return clock

def _bytes(value):
    _require(isinstance(value, bytes) and 0 < len(value) <= _MAX_BYTES, 'owner_bytes_invalid')
    return value

def _digest(value):
    return sha256(value).hexdigest()

def _json_digest(value):
    return _digest(canonical_json_bytes(value))

def _receipt_identity(meta):
    return tuple(meta.get(k) for k in ('key', 'sha256', 'etag', 'last_modified', 'content_length'))

def _reference_readers(snapshot):
    refs = snapshot['owner_refs']
    for field, path in _REFERENCE_FILES.items():
        _require(_SHA.fullmatch(str(refs.get(path, ''))) is not None
                 and _digest(_bytes(snapshot[field])) == refs[path], 'reference_hash_mismatch')
    receipt = json.loads(snapshot['receipt_bytes'])
    _require(receipt.get('authority', {}).get('identity_authority') == 'canonical_exact_identity',
             'reference_identity_authority_unqualified')
    master_rows = pd.read_parquet(BytesIO(snapshot['security_master_bytes']))
    alias_rows = pd.read_parquet(BytesIO(snapshot['vendor_aliases_bytes']))
    aliases = alias_rows.loc[(alias_rows.vendor == 'store') & alias_rows.vendor_symbol.isin(COHORT)]
    return (IssuerMaster.from_records(master_rows.to_dict('records')),
            VendorAliasTable.from_records(aliases.to_dict('records')), master_rows)

def _financial_subject(ticker, financial, cik, mic, today):
    manifest = financial['manifest']
    _require(_json_digest(manifest) == financial['manifest_sha256'], 'financial_manifest_hash_mismatch')
    selected = select_current_event_from_aliases(ticker, manifest['aliases'])
    held = financial['rows'][selected.event_id]
    row = held['workspace']
    declared = manifest['files'].get('workspaces/' + selected.event_id + '.json')
    _require(declared is not None and declared['sha256'] == held['sha256'] == _json_digest(row)
             and row['event_id'] == selected.event_id
             and row['generation_id'] == manifest['generation_id'], 'financial_owner_row_mismatch')
    sources = [s for s in row['sources'] if s.get('kind') == 'issuer_release'
               and (s.get('filing_key') or {}).get('cik') == cik
               and s.get('receipt_state') == 'byte_replayed']
    listings = [v for v in row['issuer']['listings'] if v.get('ticker') == ticker
                and v.get('mic') == mic and v.get('share_class') == 'common'
                and v.get('is_primary') is True
                and date.fromisoformat(v['valid_from']) <= today
                and (v.get('valid_to') is None or today < date.fromisoformat(v['valid_to']))]
    _require(len(sources) == len(listings) == 1, 'current_cik_mic_common_listing_join_unqualified')
    _require(row['issuer']['company_id'] == company_id_for_cik(cik)
             and listings[0]['security_id'] == security_id_for(mic,ticker),
             'existing_financial_identity_namespace_mismatch')
    return row, listings[0], sources[0], held['sha256']

def compose_defense_market_context(price_snapshot, financial_snapshot, reference_snapshot,
                                   rights_ref, *, generated_at):
    """Return closed price axes/bindings; missing or corrupt inputs fail publication.

    Owner snapshots and rights_ref come only from the trusted publisher, never
    an HTTP caller. Hash/shape checks do not grant identity or display authority.
    The store aliases and CIK reader qualify CURRENT identity, never historical PIT.
    """
    generated = _clock(generated_at)
    _require(rights_ref.get('path') == 'research/licenses/MASSIVE_ENTITLEMENT_RECORD.md'
             and _SHA.fullmatch(str(rights_ref.get('sha256', ''))) is not None
             and rights_ref.get('derived_display_qualified') is True
             and rights_ref.get('debrand_required') is True, 'derived_display_rights_unqualified')
    refs = reference_snapshot['owner_refs']
    _require(refs.get(rights_ref['path']) == rights_ref['sha256'], 'rights_owner_reference_mismatch')
    for path in ('engine/stock_technicals.py', 'lib/nyse_calendar.py', 'lib/dataos/identity.py',
                 'lib/dataos/price.py', 'config/dataset_registry.yml','engine/company_intelligence/identity.py'):
        _require(_SHA.fullmatch(str(refs.get(path, ''))) is not None, 'owner_dependency_reference_missing')
    raw_manifest = _bytes(price_snapshot['manifest_bytes'])
    manifest = json.loads(raw_manifest)
    receipt = price_snapshot['receipt']
    before, after = receipt['manifest_before'], receipt['manifest_after']
    _require(receipt.get('state') == 'STABLE_CANONICAL_SNAPSHOT_READ'
             and _receipt_identity(before) == _receipt_identity(after)
             and before.get('key') == 'massive_stock_day/_manifest.json'
             and before.get('sha256') == _digest(raw_manifest)
             and before.get('content_length') == len(raw_manifest), 'canonical_manifest_identity_mismatch')
    before_read, after_read = _clock(before['observed_at']), _clock(after['observed_at'])
    _require(_clock(before['last_modified']) <= before_read <= after_read <= generated,
             'canonical_manifest_clock_invalid')
    _require(manifest.get('dir') == 'massive_stock_day' and isinstance(manifest.get('files'), list)
             and isinstance(manifest.get('store'), dict)
             and isinstance(manifest.get('count'),int) and not isinstance(manifest.get('count'),bool)
             and manifest['count'] == len(manifest['files']) >= len(COHORT)
             and len(set(manifest['files'])) == len(manifest['files']), 'canonical_manifest_shape_invalid')
    _require(isinstance(before.get('etag'),str) and before['etag'], 'canonical_manifest_etag_missing')
    if '-' not in before['etag']:
        _require(md5(raw_manifest).hexdigest() == before['etag'], 'canonical_manifest_etag_mismatch')
    store = manifest['store']
    _require(_clock(store['updated_at']) <= _clock(before['last_modified']), 'store_generation_after_manifest')
    master, aliases, master_rows = _reference_readers(reference_snapshot)
    result = {'recognition_by_ticker': {}, 'source_bindings': {}, 'evidence': {}}
    for ticker in COHORT:
        raw = _bytes(price_snapshot['parquet_bytes'][ticker])
        obj = receipt['objects'][ticker]
        _require(ticker + '.parquet' in manifest['files']
                 and obj.get('state') == 'STABLE_BYTE_READ'
                 and obj.get('key') == 'massive_stock_day/' + ticker + '.parquet'
                 and obj.get('sha256') == _digest(raw)
                 and obj.get('content_length') == len(raw), 'canonical_object_identity_mismatch')
        etag = obj.get('etag')
        _require(isinstance(etag, str) and etag, 'canonical_object_etag_missing')
        if '-' not in etag:
            _require(md5(raw).hexdigest() == etag, 'canonical_object_etag_mismatch')
        vintage, observed = _clock(obj['last_modified']), _clock(obj['observed_at'])
        _require(vintage <= observed <= after_read <= generated, 'canonical_object_clock_invalid')
        frame = pd.read_parquet(BytesIO(raw))
        _require(isinstance(frame.index, pd.DatetimeIndex) and frame.index.is_unique
                 and frame.index.is_monotonic_increasing and len(frame) >= 2
                 and {'close', 'volume'} <= set(frame.columns)
                 and all(pd.api.types.is_numeric_dtype(frame[c]) and not pd.api.types.is_bool_dtype(frame[c]) for c in ('close','volume')), 'daily_bar_shape_invalid')
        last = frame.tail(2)
        previous, market_as_of = [v.date() for v in last.index]
        _require(previous < market_as_of and all(nyse_calendar.is_session(d) for d in (previous, market_as_of))
                 and not nyse_calendar.sessions_strictly_between(previous, market_as_of)
                 and str(market_as_of) == store['latest_date']
                 and market_as_of <= nyse_calendar.expected_last_session(generated)
                 and market_as_of <= nyse_calendar.expected_last_session(vintage), 'daily_bar_calendar_invalid')
        _require(all(not isinstance(v, bool) and math.isfinite(float(v)) and float(v) > 0
                     for column in ('close', 'volume') for v in last[column]), 'daily_bar_value_invalid')
        change = chg_1d(frame['close'])
        _require(change is not None and math.isfinite(change), 'owner_price_change_unavailable')
        lag = nyse_calendar.sessions_behind(market_as_of, generated)
        security = aliases.resolve('store', ticker, generated.date())
        _require(security is not None and master.security_state_of(security) is None,
                 'current_store_security_unqualified')
        issuer = master.issuer_of_security(security)
        cik = master.cik_of_issuer(issuer)
        key = master.listing_key_of_security(security)
        _require(cik is not None and key is not None, 'current_issuer_cik_unqualified')
        listing_key = parse_listing_key(key)
        subject_rows = master_rows.loc[master_rows.security_id == security]
        _require(len(subject_rows) == 1 and subject_rows.iloc[0]['issuer_state'] == 'RESOLVED'
                 and listing_key.country == 'US' and listing_key.mic == 'XNYS', 'current_listing_unqualified')
        row, listing, source, row_hash = _financial_subject(ticker, financial_snapshot, cik, listing_key.mic, generated.date())
        _require(_clock(row['lifecycle']['observed_at']) <= generated
                 and _clock(row['lifecycle']['source_available_at']) <= generated,
                 'financial_subject_after_generation')
        bridge = {'mode': 'current_owner_evidence_join', 'source_store_symbol': ticker,
                  'dataos_security_id': security, 'dataos_issuer_id': issuer, 'evidenced_cik': cik,
                  'listing_key': str(listing_key), 'mic': listing_key.mic, 'share_class': listing['share_class'],
                  'financial_issuer_id': row['issuer']['company_id'], 'financial_security_id': listing['security_id'],
                  'financial_generation': financial_snapshot['manifest']['generation_id'],
                  'financial_manifest_sha256': financial_snapshot['manifest_sha256'],
                  'financial_workspace_sha256': row_hash, 'financial_document_id': source['document_id'],
                  'historical_identity_admitted': False}
        envelope = {'object': {k:obj[k] for k in ('key','sha256','etag','last_modified','observed_at','content_length')},
                    'manifest': {k:before[k] for k in ('key','sha256','etag','last_modified','observed_at','content_length')},
                    'manifest_after_read': after['observed_at'], 'identity_bridge': bridge,
                    'owner_refs': refs, 'rights_ref': rights_ref, 'calculator': 'engine.stock_technicals.chg_1d',
                    'metric': {'market_as_of':str(market_as_of),'previous_session':str(previous),
                               'window_sessions':1,'sessions_behind':lag,'price_adjustment':'raw','return_pct':change}}
        digest = _json_digest(envelope)
        ref = 'market_context:' + ticker + ':' + digest[:24]
        state = 'stale' if lag else 'supported'
        binding = {'sha256':digest,'content_id':'raw-price-context:'+digest[:24],
                   'contract':'equity.bars.daily.massive@1.0.0','owner_family':'market',
                   'issuer_id':row['issuer']['company_id'],'security_id':listing['security_id'],
                   'observed_at':obj['observed_at'],'owner_admission_ref':'bounded_canonical_R2_read:'+_json_digest(receipt),
                   'price_adjustment':'raw'}
        leg = {'state':state,'owner_ref':ref,'observed_at':obj['observed_at'],'security_id':listing['security_id'],
               'price_adjustment':'raw','price_vintage':obj['last_modified'],'window_sessions':1,'return_pct':change,
               'market_as_of':str(market_as_of),'previous_session':str(previous),'sessions_behind':lag}
        limitations = ['raw_price_change_not_total_return','no_observed_market_expectations','no_historical_identity_admission']
        if lag: limitations.append('archive_behind_exchange_calendar')
        result['source_bindings'][ref] = binding
        result['recognition_by_ticker'][ticker] = {
            'state':state,'display_scope':'government_revenue_entitled',
            'summary_en':f'Archived session {market_as_of}: one-session raw closing-price change {change:+.1f}%. At this snapshot the archive is {lag} completed session behind the exchange calendar.',
            'summary_zh':f'存档交易日 {market_as_of}：单个交易日未经调整的收盘价变化 {change:+.1f}%。此快照的存档较交易所日历落后 {lag} 个已结束的交易日。',
            'owner_ref':ref,'evidence_refs':[ref],'observed_at':obj['observed_at'],'fiscal_period':None,
            'reason_code':'observed_raw_price_context','facts':[],'limitations':limitations,
            'expectations_kind':'not_observed','price_response':leg,
            'valuation_scenario':{'state':'missing_owner','owner_ref':None,'observed_at':None}}
        result['evidence'][ref] = envelope
    return result


def load_defense_market_inputs(root, *, rights_ref):
    """Read the existing-owner mirror only; no hydration, credentials or writes.

    The publisher independently qualifies rights_ref against its existing rights
    owner. The tracked collector _manifest.json is deliberately never consulted.
    """
    from pathlib import Path
    root = Path(root)
    store = root / 'data/massive_stock_day'
    scratch = store / '.defense_read'
    def bounded_read(path):
        for ancestor in reversed(path.parents):
            _require(not ancestor.is_symlink() and (not ancestor.exists() or ancestor.is_dir()),
                     'owner_mirror_ancestor_unsafe')
        _require(path.is_file() and not path.is_symlink(), 'required_market_owner_mirror_missing')
        _require(0 < path.stat().st_size <= _MAX_BYTES, 'owner_mirror_size_invalid')
        return _bytes(path.read_bytes())
    manifest = bounded_read(scratch / 'manifest.json')
    receipt = json.loads(bounded_read(scratch / 'read_receipt.json'))
    prices = {'manifest_bytes':manifest, 'receipt':receipt,
              'parquet_bytes':{ticker:bounded_read(store / (ticker+'.parquet')) for ticker in COHORT}}
    references = {field:bounded_read(root/path) for field,path in _REFERENCE_FILES.items()}
    reference_paths = list(_REFERENCE_FILES.values()) + [
        'engine/stock_technicals.py','lib/nyse_calendar.py','lib/dataos/identity.py',
        'lib/dataos/price.py','config/dataset_registry.yml','engine/company_intelligence/identity.py',
        'engine/government_revenue/defense_market_context.py',
        'research/licenses/MASSIVE_ENTITLEMENT_RECORD.md',
    ]
    references['owner_refs'] = {path:_digest(bounded_read(root/path)) for path in reference_paths}
    _require(references['owner_refs'].get(rights_ref.get('path')) == rights_ref.get('sha256'),
             'rights_owner_mirror_changed')
    return prices, references
