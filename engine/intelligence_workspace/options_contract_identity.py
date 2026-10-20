"""Scoped dated option identity over native captured evidence; no alias publication.

This adapter returns only a selected-contract binding, never a reusable root alias.
Capture receipts establish known-by evidence, not provider first availability or rights.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
import hashlib
import io
import json
import re

import pandas as pd

from lib.dataos.identity import _aware_utc
from lib.options_source_receipts import native_acquisitions, massive_reference_terms, ordinary_spy_terms
from lib.symbol_directory_receipts import validate_symbol_directory_completion_receipt_bytes
from .entity import IdentityArtifactRead, IdentityResolutionError, _identity_read, _captured_option_security_target


def _sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _key(row):
    expiry=row['expiration']
    expiry=expiry.date().isoformat() if isinstance(expiry, datetime) else str(expiry)
    date.fromisoformat(expiry)
    strike=Decimal(str(row['strike']))
    if not strike.is_finite() or strike<=0 or row['right'] not in ('C','P'):
        raise IdentityResolutionError('Invalid scoped contract coordinate')
    return (expiry, format(strike.normalize(),'f'), row['right'])


def _strict_json(raw):
    def pairs(items):
        out={}
        for k,v in items:
            if k in out:raise IdentityResolutionError('Duplicate identity observation field')
            out[k]=v
        return out
    return json.loads(raw,object_pairs_hook=pairs,
        parse_constant=lambda v: (_ for _ in ()).throw(IdentityResolutionError('Nonfinite observation')))


@dataclass(frozen=True)
class DatedContractIdentity:
    """A bound selected book, unusable as a general vendor/root relation."""
    receipt: dict


def resolve_dated_spy_contract_identity(greeks, oi, *, source_session, input_sha256,
        reference: IdentityArtifactRead, security_master: IdentityArtifactRead,
        listing: IdentityArtifactRead, listing_receipt: IdentityArtifactRead, decision_at):
    """Bind one bounded SPY expiry through exact historical reference and native target.

    Exact artifact reads/digests are supplied by the incumbent admitted reader.
    Reference is its captured parsed-response observation, not fabricated raw HTTP
    bytes. The raw response digest is retained separately; no authentication is
    claimed by an unkeyed hash. Current canonical reads may be later than source
    session; every use remains gated by their actual known-by clocks.
    """
    try:
        cutoff=_aware_utc(decision_at,'decision_at');on=date.fromisoformat(source_session)
        if not re.fullmatch(r'[a-f0-9]{64}',input_sha256):raise ValueError('Input binding missing')
        reads=[_identity_read(r,cutoff) for r in (reference,security_master,listing,listing_receipt)]
        if on>cutoff.date():raise ValueError('Future source session')
        obs=_strict_json(reference.body)
        params=obs.get('params') or {}
        if (obs.get('path')!='/v3/reference/options/contracts'
                or params.get('as_of')!=source_session or params.get('underlying_ticker')!='SPY'
                or not isinstance(obs.get('contracts'),list) or not 0<len(obs['contracts'])<=100
                or obs.get('historical_first_availability_established') is not False):
            raise ValueError('Historical reference scope unknown')
        source_at=_aware_utc(obs['completed_at'],'reference completed_at')
        if source_at>reads[0] or source_at>cutoff:raise ValueError('Reference availability conflicts')
        source_clocks=[source_at]
        selected=set()
        for frame,kind in ((greeks,'greeks'),(oi,'oi')):
            captures=native_acquisitions(frame,'SPY',source_session,kind)
            if not captures:raise ValueError('Native selected acquisition missing')
            for capture in captures:
                p=capture['parameters']
                if (p.get('expiration') in (None,'*') or p.get('right')!='both'
                        or type(p.get('strike_range')) is not int or not 0<=p['strike_range']<=5):
                    raise ValueError('Native acquisition is not bounded selected scope')
                source_clocks.append(_aware_utc(capture['received_at'],'capture received_at'))
            keys=[]
            for row in frame.to_dict('records'):
                d=row.get('date')
                d=d.date().isoformat() if isinstance(d,datetime) else str(d)
                if row.get('root')!='SPY' or d!=source_session:raise ValueError('Native root/session mismatch')
                keys.append(_key(row))
            if len(keys)!=len(set(keys)):raise ValueError('Duplicate selected coordinate')
            selected.update(keys)
        expiries={k[0] for k in selected}
        if len(expiries)!=1 or not 0<len(selected)<=22 or params.get('expiration_date') not in expiries:
            raise ValueError('Selected expiry/population is outside bound')
        terms={}
        for c in obs['contracts']:
            t=ordinary_spy_terms(massive_reference_terms(obs,'SPY',contract=c))
            k=_key(t)
            if k in terms:raise ValueError('Duplicate reference coordinate')
            terms[k]=t
        if not selected<=set(terms):raise ValueError('Selected contract missing exact reference')
        if any(terms[k].get('deliverable')!='100_underlying_shares' for k in selected):
            raise ValueError('Adjusted/unknown selected series is unsupported')
        security_id='SEC:US-ARCX-SPY'
        listing_key,master_at=_captured_option_security_target(security_id,on,
            decision_at=cutoff,security_master=security_master)
        receipt=validate_symbol_directory_completion_receipt_bytes(
            _strict_json(listing_receipt.body),listing_receipt.body,listing.body,expected_kind='listing_snapshot')
        listing_on=date.fromisoformat(receipt['observation_date'])
        listing_completed=_aware_utc(receipt['clocks']['collector_completed_at'],'listing completed_at')
        if listing_on>on or listing_completed>reads[2] or not receipt['authority']['listing_identity_observation_eligible']:
            raise ValueError('Listing observation does not support dated target')
        frame=pd.read_parquet(io.BytesIO(listing.body));rows=frame.loc[frame.symbol=='SPY']
        if len(rows)!=1:raise ValueError('Listing SPY missing or ambiguous')
        row=rows.iloc[0]
        if (listing_key!='US-ARCX-SPY' or row['exchange']!='P' or not bool(row['etf'])
                or bool(row['test_issue']) or bool(row['is_preferred'])):
            raise ValueError('Listing/canonical target mismatch')
        known=max(*reads,*source_clocks,master_at,listing_completed)
        if known>cutoff:raise ValueError('Identity evidence after decision')
        out=dict(schema='options.dated_contract_identity/v1',scope='selected_contracts',root='SPY',
            source_session=source_session,effective_from=on.isoformat(),
            effective_to=(on+timedelta(days=1)).isoformat(),known_at=known.isoformat(),
            security_id=security_id,listing_key=listing_key,input_sha256=input_sha256,
            contract_keys=[list(k) for k in sorted(selected)],reference_observation_sha256=reference.sha256,
            source_response_sha256=obs['payload_sha256'],security_master_sha256=security_master.sha256,
            listing_sha256=listing.sha256,listing_receipt_sha256=listing_receipt.sha256,
            source_evidence_representation='captured_parsed_reference_observation',
            historical_first_availability_established=False,root_alias_created=False)
        out['binding_sha256']=_sha(out)
        return DatedContractIdentity(out)
    except IdentityResolutionError:raise
    except (ValueError,TypeError,KeyError,AttributeError,ArithmeticError) as exc:
        raise IdentityResolutionError('Dated contract identity refused: '+str(exc)) from exc


def validate_dated_contract_identity(receipt, *, root, source_session, input_sha256, cutoff):
    """Recheck the retained native composition's exact scope before producer use.

    A deterministic seal is consistency, not capture authentication. The admitted
    owner constructs this receipt through resolve_dated_spy_contract_identity.
    """
    required = frozenset("schema scope root source_session effective_from effective_to known_at security_id listing_key input_sha256 contract_keys reference_observation_sha256 source_response_sha256 security_master_sha256 listing_sha256 listing_receipt_sha256 source_evidence_representation historical_first_availability_established root_alias_created binding_sha256".split())
    if not isinstance(receipt,dict) or set(receipt)!=required:
        raise IdentityResolutionError('Scoped identity receipt missing/unknown fields')
    body={k:v for k,v in receipt.items() if k!='binding_sha256'}
    on=date.fromisoformat(source_session)
    if (receipt.get('schema')!='options.dated_contract_identity/v1'
            or receipt.get('scope')!='selected_contracts' or receipt.get('root')!=root or root!='SPY'
            or receipt.get('source_session')!=source_session or receipt.get('input_sha256')!=input_sha256
            or receipt.get('security_id')!='SEC:US-ARCX-SPY' or receipt.get('listing_key')!='US-ARCX-SPY'
            or receipt.get('effective_from')!=source_session
            or receipt.get('effective_to')!=(on+timedelta(days=1)).isoformat()
            or receipt.get('root_alias_created') is not False
            or receipt.get('historical_first_availability_established') is not False
            or receipt.get('source_evidence_representation')!='captured_parsed_reference_observation'
            or any(not isinstance(receipt.get(k),str) or not re.fullmatch(r'[a-f0-9]{64}',receipt[k]) for k in ('input_sha256','reference_observation_sha256','source_response_sha256','security_master_sha256','listing_sha256','listing_receipt_sha256'))
            or receipt.get('binding_sha256')!=_sha(body)):
        raise IdentityResolutionError('Scoped identity binding mismatch')
    known=_aware_utc(receipt.get('known_at'),'known_at')
    if known.date()<on or known>_aware_utc(cutoff,'cutoff'):raise IdentityResolutionError('Scoped identity not yet known')
    keys=receipt.get('contract_keys')
    if (not isinstance(keys,list) or not 0<len(keys)<=22 or any(not isinstance(k,list) or len(k)!=3 for k in keys)
            or len({tuple(k) for k in keys})!=len(keys)):
        raise IdentityResolutionError('Invalid selected identity scope')
    try:
        normalized=[_key(dict(expiration=k[0],strike=k[1],right=k[2])) for k in keys]
        if (any(tuple(k)!=n for k,n in zip(keys,normalized)) or len({k[0] for k in normalized})!=1
                or any(date.fromisoformat(k[0])<on for k in normalized)):
            raise ValueError('Noncanonical scope coordinate')
    except (ValueError,TypeError,ArithmeticError) as exc:
        raise IdentityResolutionError('Invalid selected identity coordinate') from exc
    return frozenset(normalized)
