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
from lib.options_source_receipts import native_acquisitions, massive_reference_terms, ordinary_spy_terms, reference_population_terms
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
        if (len(expiries)!=1 or not 0<len(selected)<=22 or params.get('expiration_date') not in expiries
                or any(date.fromisoformat(expiry)<on for expiry in expiries)):
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
        if (listing_on>on or listing_completed.date()>on or listing_completed>min(reads[2],reads[3])
                or not receipt['authority']['listing_identity_observation_eligible']):
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
    if isinstance(receipt, dict) and receipt.get('schema') == 'options.dated_contract_identity/v2':
        try:
            return _validate_observed_identity(receipt, root=root, source_session=source_session,
                                               input_sha256=input_sha256, cutoff=cutoff)
        except IdentityResolutionError:
            raise
        except (ValueError, TypeError, KeyError, AttributeError, ArithmeticError) as exc:
            raise IdentityResolutionError('Observed identity malformed: ' + str(exc)) from exc
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


def _observed_target(root):
    # Exact admitted listing profiles, never a ticker-derived canonical ID.
    targets={'SPY':('SEC:US-ARCX-SPY','US-ARCX-SPY','P'),
             'QQQ':('SEC:US-XNAS-QQQ','US-XNAS-QQQ','NASDAQ')}
    if root not in targets:
        raise IdentityResolutionError('Observed ETF root is not supported')
    return targets[root]


def resolve_observed_spy_contract_identity(greeks, oi, **kwargs):
    """Compatibility entry point; the existing SPY-only call stays unchanged."""
    return resolve_observed_etf_contract_identity(greeks, oi, root='SPY', **kwargs)


def resolve_observed_etf_contract_identity(greeks, oi, *, root, source_session, input_sha256,
        reference: IdentityArtifactRead, security_master: IdentityArtifactRead,
        listing: IdentityArtifactRead, listing_receipt: IdentityArtifactRead, decision_at,
        retained_inputs=None):
    """Bind one supported observed ETF population without minting a root alias.

    Retained store reads establish possession now, never an original HTTP request,
    model/version, provider publication time or historical availability. Numerical
    qualification remains the exposure producer's separate responsibility.
    """
    from engine.options_exposure_projection import exposure_input_digest
    try:
        cutoff=_aware_utc(decision_at,'decision_at');on=date.fromisoformat(source_session)
        security_id,expected_listing,expected_exchange=_observed_target(root)
        if root=='QQQ' and on<date(2026,10,20):
            raise ValueError('QQQ observed identity predates native admission')
        if exposure_input_digest(greeks,oi,source_session,root) != input_sha256:
            raise ValueError('Observed input digest mismatch')
        reads=[_identity_read(r,cutoff) for r in (reference,security_master,listing,listing_receipt)]
        if on>cutoff.date():raise ValueError('Future source session')
        obs=_strict_json(reference.body)
        if obs.get('source_session') != source_session:raise ValueError('Reference source session mismatch')
        terms,pages=reference_population_terms(obs,root)
        source_clocks=[_aware_utc(p['completed_at'],'page completed_at') for p in pages]
        if any(t>reads[0] for t in source_clocks):raise ValueError('Reference read before page capture')
        artifacts=[]
        if retained_inputs is not None:
            if not isinstance(retained_inputs,dict) or set(retained_inputs)!={'greeks','oi'}:
                raise ValueError('Retained pair incomplete')
            frames=[]
            for kind in ('greeks','oi'):
                read=retained_inputs[kind];at=_identity_read(read,cutoff)
                import pyarrow.parquet as pq
                parquet=pq.ParquetFile(io.BytesIO(read.body))
                if (parquet.metadata.num_rows>100000 or len(parquet.schema_arrow.names)>64
                        or sum(parquet.metadata.row_group(i).total_byte_size for i in range(parquet.metadata.num_row_groups))>128*1024*1024):
                    raise ValueError('Retained input exceeds decoded bound')
                source=parquet.read().to_pandas()
                frames.append(source)
                artifacts.append(dict(kind=kind,sha256=read.sha256,read_at=at.isoformat()))
                source_clocks.append(at)
            if exposure_input_digest(*frames,source_session,root) != input_sha256:
                raise ValueError('Retained artifacts do not bind observed rows')
            basis='retained_native_store_read'
        else:
            basis='native_acquisition'
        observed=set()
        for frame,kind in ((greeks,'greeks'),(oi,'oi')):
            if len(frame)>100000:raise ValueError('Observed input exceeds bound')
            if retained_inputs is None:
                captures=native_acquisitions(frame,root,source_session,kind)
                if not captures:raise ValueError('Native observed acquisition missing')
                for capture in captures:
                    p=capture['parameters']
                    if (p.get('expiration')!='*' or p.get('right','both')!='both'
                            or p.get('strike','*')!='*' or p.get('strike_range') is not None
                            or str(p['start_date']).replace('-','')!=source_session.replace('-','')
                            or str(p['end_date']).replace('-','')!=source_session.replace('-','')):
                        raise ValueError('Native acquisition is not the declared whole observed root')
                    source_clocks.append(_aware_utc(capture['received_at'],'capture received_at'))
            keys=[]
            for row in frame.to_dict('records'):
                d=row.get('date');d=d.date().isoformat() if isinstance(d,datetime) else str(d)
                if row.get('root')!=root or d!=source_session:raise ValueError('Observed root/session mismatch')
                key=_key(row)
                if date.fromisoformat(key[0])<on:raise ValueError('Expired observed contract')
                keys.append(key)
            if len(keys)!=len(set(keys)):raise ValueError('Duplicate observed coordinate')
            observed.update(keys)
        if not 0<len(observed)<=100000 or len({k[:2] for k in observed})>50000:
            raise ValueError('Observed population outside bound')
        by_key={}
        for term in terms:by_key.setdefault(_key(term),[]).append(term)
        # Reference omissions/ambiguity withhold their coordinates only. They do
        # not remove those contracts from the declared observed denominator.
        bound={k for k in observed if len(by_key.get(k,[]))==1}
        listing_key,master_at=_captured_option_security_target(security_id,on,
            decision_at=cutoff,security_master=security_master)
        receipt=validate_symbol_directory_completion_receipt_bytes(_strict_json(listing_receipt.body),
            listing_receipt.body,listing.body,expected_kind='listing_snapshot')
        completed=_aware_utc(receipt['clocks']['collector_completed_at'],'listing completed_at')
        if (date.fromisoformat(receipt['observation_date'])>on or completed.date()>on
                or completed>min(reads[2],reads[3]) or not receipt['authority']['listing_identity_observation_eligible']):
            raise ValueError('Listing observation does not support dated target')
        listing_rows=pd.read_parquet(io.BytesIO(listing.body));rows=listing_rows.loc[listing_rows.symbol==root]
        if len(rows)!=1:raise ValueError('Listing ETF missing or ambiguous')
        row=rows.iloc[0]
        if (listing_key!=expected_listing or row['exchange']!=expected_exchange or not bool(row['etf'])
                or bool(row['test_issue']) or bool(row['is_preferred'])):
            raise ValueError('Listing/canonical target mismatch')
        known=max(*reads,*source_clocks,master_at,completed)
        if known>cutoff:raise ValueError('Identity evidence after decision')
        out=dict(schema='options.dated_contract_identity/v2',scope='observed_contracts',root=root,
            source_session=source_session,effective_from=source_session,effective_to=(on+timedelta(days=1)).isoformat(),
            known_at=known.isoformat(),security_id=security_id,listing_key=listing_key,input_sha256=input_sha256,
            contract_keys=[list(k) for k in sorted(bound)],observed_contract_keys=[list(k) for k in sorted(observed)],
            reference_observation_sha256=reference.sha256,reference_pages=pages,security_master_sha256=security_master.sha256,
            listing_sha256=listing.sha256,listing_receipt_sha256=listing_receipt.sha256,
            source_evidence_representation='captured_reference_population_observation',source_evidence_basis=basis,
            source_input_artifacts=artifacts,historical_first_availability_established=False,root_alias_created=False)
        out['binding_sha256']=_sha(out)
        return DatedContractIdentity(out)
    except IdentityResolutionError:raise
    except (ValueError,TypeError,KeyError,AttributeError,ArithmeticError) as exc:
        raise IdentityResolutionError('Observed contract identity refused: '+str(exc)) from exc


def _validate_observed_identity(receipt, *, root, source_session, input_sha256, cutoff):
    required=frozenset('schema scope root source_session effective_from effective_to known_at security_id listing_key input_sha256 contract_keys observed_contract_keys reference_observation_sha256 reference_pages security_master_sha256 listing_sha256 listing_receipt_sha256 source_evidence_representation source_evidence_basis source_input_artifacts historical_first_availability_established root_alias_created binding_sha256'.split())
    if set(receipt)!=required:raise IdentityResolutionError('Observed identity fields invalid')
    on=date.fromisoformat(source_session);known=_aware_utc(receipt['known_at'],'known_at')
    security_id,listing_key,_=_observed_target(root)
    # The admitted native QQQ target starts Oct20. A self-consistent receipt
    # cannot extend that current intake to older retained option populations.
    if root=='QQQ' and on<date(2026,10,20):
        raise IdentityResolutionError('QQQ observed identity predates native admission')
    if (receipt['root']!=root or receipt['source_session']!=source_session
            or receipt['scope']!='observed_contracts' or receipt['security_id']!=security_id
            or receipt['listing_key']!=listing_key or receipt['effective_from']!=source_session
            or receipt['effective_to']!=(on+timedelta(days=1)).isoformat() or receipt['input_sha256']!=input_sha256
            or receipt['source_evidence_representation']!='captured_reference_population_observation'
            or receipt['historical_first_availability_established'] is not False or receipt['root_alias_created'] is not False
            or known.date()<on or known>_aware_utc(cutoff,'cutoff')
            or any(not re.fullmatch('[a-f0-9]{64}',str(receipt[k])) for k in ('input_sha256','reference_observation_sha256','security_master_sha256','listing_sha256','listing_receipt_sha256'))
            or receipt['binding_sha256']!=_sha({k:v for k,v in receipt.items() if k!='binding_sha256'})):
        raise IdentityResolutionError('Observed identity binding invalid')
    def keys(name,empty=False):
        values=receipt[name]
        if not isinstance(values,list) or not (0 if empty else 1)<=len(values)<=100000:
            raise IdentityResolutionError('Observed identity population outside bound')
        normalized=[]
        for key in values:
            if not isinstance(key,list) or len(key)!=3:raise IdentityResolutionError('Observed coordinate invalid')
            n=_key(dict(expiration=key[0],strike=key[1],right=key[2]))
            if tuple(key)!=n or date.fromisoformat(n[0])<on:raise IdentityResolutionError('Observed coordinate noncanonical')
            normalized.append(n)
        if len(set(normalized))!=len(normalized):raise IdentityResolutionError('Observed coordinate duplicated')
        return frozenset(normalized)
    observed=keys('observed_contract_keys');bound=keys('contract_keys',True)
    if not bound<=observed or len({k[:2] for k in observed})>50000:
        raise IdentityResolutionError('Bound population widens observed scope or cell limit')
    pages=receipt['reference_pages'];artifacts=receipt['source_input_artifacts']
    if not isinstance(pages,list) or not 0<len(pages)<=20:raise IdentityResolutionError('Observed page bounds invalid')
    scope=dict(underlying_ticker=root,as_of=source_session,**{'expiration_date.gte':source_session},
               expired='false',order='asc',sort='ticker',limit=1000)
    for index,page in enumerate(pages):
        if (not isinstance(page,dict) or set(page)!={'params','response_sha256','completed_at','response_bytes','contracts'}
                or not re.fullmatch('[a-f0-9]{64}',str(page['response_sha256']))
                or _aware_utc(page['completed_at'],'page completed_at')>known
                or type(page['response_bytes']) is not int or not 0<page['response_bytes']<=1024*1024
                or type(page['contracts']) is not int or not 0<=page['contracts']<=1000):
            raise IdentityResolutionError('Observed page evidence invalid')
        query=page['params']
        if (not isinstance(query,dict) or (index==0 and query!=scope)
                or (index>0 and (not isinstance(query.get('cursor'),str) or not 0<len(query['cursor'])<=8192
                    or set(query)-set(scope)-{'cursor'}
                    or any(str(v)!=str(scope[k]) for k,v in query.items() if k!='cursor')))):
            raise IdentityResolutionError('Observed page query invalid')
    if (sum(p['response_bytes'] for p in pages)>8*1024*1024 or sum(p['contracts'] for p in pages)>20000
            or len(bound)>sum(p['contracts'] for p in pages)
            or len({json.dumps(p['params'],sort_keys=True) for p in pages})!=len(pages)
            or len({p['params']['cursor'] for p in pages[1:]})!=len(pages)-1):
        raise IdentityResolutionError('Observed reference population exceeds bounds or cycles')
    basis=receipt['source_evidence_basis']
    if basis=='native_acquisition':
        if artifacts!=[]:raise IdentityResolutionError('Unexpected retained evidence')
    elif basis=='retained_native_store_read':
        if (not isinstance(artifacts,list) or len(artifacts)!=2
                or any(not isinstance(a,dict) for a in artifacts)
                or {a.get('kind') for a in artifacts}!={'greeks','oi'}):
            raise IdentityResolutionError('Retained pair missing')
        for artifact in artifacts:
            if (set(artifact)!={'kind','sha256','read_at'} or not re.fullmatch('[a-f0-9]{64}',str(artifact['sha256']))
                    or _aware_utc(artifact['read_at'],'read_at')>known):raise IdentityResolutionError('Retained evidence invalid')
    else:raise IdentityResolutionError('Observed source basis unknown')
    return bound
