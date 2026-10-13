"""Current company context composed from the incumbent Data OS identity readers.

The installed owner supplies one compatible immutable reference bundle. This
module neither allocates IDs nor qualifies a disclosure source or its purpose.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
import re
from typing import Protocol

from lib.dataos.identity import IssuerMaster, VendorAliasTable, parse_id, parse_listing_key, security_id, issuer_id as render_issuer_id
from engine.company_intelligence import issuer_disclosures as native

SCHEMA = 'company_intelligence.private_company_context/v1'
RECEIPT_SCHEMA = 'company_intelligence.current_issuer_identity/v1'
NAMESPACE = 'store'
MAX_REFERENCE_BYTES = 2 * 1024 * 1024
_SYMBOL = re.compile(r'[A-Z0-9][A-Z0-9.\-]{0,23}\Z')
_NAMES = ('security_master', 'vendor_aliases', 'issuer_master')


def _require(condition: bool) -> None:
    native._require(condition, 'CURRENT_IDENTITY_UNAVAILABLE')


@dataclass(frozen=True)
class IdentityBundle:
    """Owner-qualified bytes from one committed, compatible reference generation.

    source_commit must identify the actual tree that contains all three bytes.
    The installed owner verifies that relationship before supplying a bundle;
    a matching digest alone does not establish it. HTTP cannot supply this object.
    """
    source_commit: str
    security_master: bytes
    vendor_aliases: bytes
    issuer_master: bytes

    def validate(self) -> None:
        _require(type(self.source_commit) is str and bool(re.fullmatch(r'[0-9a-f]{40}', self.source_commit)))
        for name in _NAMES:
            raw = getattr(self, name)
            _require(type(raw) is bytes and 0 < len(raw) <= MAX_REFERENCE_BYTES)


class CompanyContextOwner(Protocol):
    def current_identity_bundle(self, purpose: str, audience: str) -> IdentityBundle | None:
        """Return a currently qualified immutable Data OS bundle, or refuse.

        Resolve the current owner generation on every call. Do not assemble three
        mutable path reads and declare them coherent, or keep an indefinite ALLOW.
        This metadata capability grants no disclosure read or publication rights.
        """
        ...


def _bundle(owner: CompanyContextOwner, purpose: str, audience: str) -> IdentityBundle:
    try:
        value = owner.current_identity_bundle(purpose, audience)
        _require(type(value) is IdentityBundle)
        value.validate()
        return value
    except native.DisclosureError:
        raise
    except Exception:
        raise native.DisclosureError('CURRENT_IDENTITY_UNAVAILABLE') from None


def _text(value: object) -> str | None:
    if value is None or (isinstance(value, float) and value != value):
        return None
    text = str(value).strip()
    return text or None


def _evidence_date(value: object, today: date) -> str:
    if type(value) is date:
        observed = value
    elif type(value) is str and re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
        observed = date.fromisoformat(value)
    else:
        raise native.DisclosureError('CURRENT_IDENTITY_UNAVAILABLE')
    _require(observed <= today)
    return observed.isoformat()


def _rows(raw: bytes) -> list[dict]:
    import pandas as pd
    return pd.read_parquet(BytesIO(raw)).to_dict('records')


def _unique(rows: list[dict], key: str) -> dict[str, dict]:
    values = [_text(row.get(key)) for row in rows]
    _require(all(values) and len(values) == len(set(values)))
    return dict(zip(values, rows, strict=True))


def resolve_current_company(bundle: IdentityBundle, symbol: str, *, today: date) -> dict:
    """Current store-alias query; never ticker-to-ISS derivation or PIT evidence."""
    bundle.validate()
    _require(type(symbol) is str and bool(_SYMBOL.fullmatch(symbol)) and type(today) is date)
    try:
        rows = _rows(bundle.security_master)
        securities = _unique(rows, 'security_id')
        issuers = _unique(_rows(bundle.issuer_master), 'issuer_id')
        master = IssuerMaster.from_records(rows)
        aliases = VendorAliasTable.from_records(_rows(bundle.vendor_aliases))
        sid = aliases.resolve(NAMESPACE, symbol, today)
        _require(sid is not None and sid in securities)
        _require(aliases.vendor_symbol_for(NAMESPACE, sid, today) == symbol)
        kind, listing = parse_id(sid)
        _require(kind == 'security' and listing.country == 'US' and listing.mic in {'XNAS', 'XNYS', 'XASE'})
        row = securities[sid]
        _require(not _text(row.get('security_state')) and not _text(row.get('superseded_by')))
        _require(row.get('issuer_state') == 'RESOLVED')
        iid = master.issuer_of_security(sid)
        cik = master.cik_of_issuer(iid) if iid else None
        key = master.listing_key_of_security(sid)
        _require(iid in issuers and cik is not None and key is not None)
        issuer_kind, issuer_key = parse_id(iid)
        _require(issuer_kind == 'issuer' and render_issuer_id(issuer_key) == iid)
        _require(security_id(parse_listing_key(key)) == sid)
        issuer = issuers[iid]
        _require(issuer.get('status') == 'active' and issuer.get('evidence_source') == 'sec_company_tickers')
        _require(_text(issuer.get('cik')) == cik and bool(re.fullmatch(r'[0-9]{10}', cik)) and int(cik) > 0)
        observed = _evidence_date(issuer.get('evidence_snapshot'), today)
        _require(_evidence_date(row.get('issuer_evidence_snapshot'), today) == observed)
        # Stable for every share class of one issuer in this owner bundle. Query
        # symbol, security and request time deliberately do not enter the receipt.
        receipt = {'schema': RECEIPT_SCHEMA, 'identity_mode': 'current', 'issuer_id': iid,
                   'evidenced_cik': cik, 'source_commit': bundle.source_commit,
                   'sources': {name: {'sha256': sha256(getattr(bundle, name)).hexdigest(),
                                     'byte_length': len(getattr(bundle, name))} for name in _NAMES},
                   'evidence_source': issuer['evidence_source'],
                   'evidence_snapshot': observed}
        raw = json.dumps(receipt, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
        _require(len(raw) <= native.MAX_OBJECT_BYTES)
        reference = {'schema': RECEIPT_SCHEMA, 'sha256': sha256(raw).hexdigest(), 'byte_length': len(raw)}
        return {'schema': SCHEMA, 'identity_mode': 'current',
                'query': {'namespace': NAMESPACE, 'symbol': symbol}, 'security_id': sid,
                'issuer_binding': {'issuer_id': iid, 'evidenced_cik': cik,
                                   'identity_snapshot_reference': reference},
                'identity_receipt': receipt}
    except native.DisclosureError:
        raise
    except Exception:
        raise native.DisclosureError('CURRENT_IDENTITY_UNAVAILABLE') from None


def read_company_context(owner: CompanyContextOwner, symbol: str, *, purpose: str, audience: str) -> dict:
    """Current UTC-date query; refuse a midnight transition or bundle change.

    This deliberately fixes UTC for this endpoint instead of the host-local
    date.today default used by the general workspace normalizer. No PIT claim.
    """
    initial = _bundle(owner, purpose, audience)
    today = datetime.now(timezone.utc).date()
    value = resolve_current_company(initial, symbol, today=today)
    _require(_bundle(owner, purpose, audience) == initial)
    _require(datetime.now(timezone.utc).date() == today)
    return value
