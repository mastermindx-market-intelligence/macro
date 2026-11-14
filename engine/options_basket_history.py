"""Source-qualified Factor Atlas constituent-IV history statistics, with no I/O.

Input is the incumbent private `options_hub.factor_options/v1` aggregate envelope
per source session. Every point must be full-basket and exactly source qualified;
no sparse-name renormalization, historical identity backprojection or vendor
`iv_rank_252` reinterpretation. Percentile uses explicit midranks for ties,
whereas min/max rank is a different statistic. This does not certify source
entitlements or publish data; the caller must be the owner-qualified source.
"""
from __future__ import annotations

from datetime import date, datetime
from math import fsum, isfinite
from numbers import Real
import re
from typing import Mapping, Sequence

_DIGEST=re.compile(r'^[0-9a-f]{64}$')


def _aware(value: object) -> datetime | None:
    if not isinstance(value,str):return None
    try: out=datetime.fromisoformat(value)
    except ValueError:return None
    return out if out.tzinfo is not None and out.utcoffset() is not None else None


def _session(value: object) -> date | None:
    """Parse only the owner-supplied cash-session label, never a timestamp."""
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        result = date.fromisoformat(value)
    except ValueError:
        return None
    return result if result.isoformat() == value else None


def _num(value: object) -> float | None:
    if isinstance(value,bool) or not isinstance(value,Real):return None
    try:
        n=float(value)
    except (OverflowError, ValueError):
        return None
    return n if isfinite(n) else None


def _weights(point: Mapping) -> tuple[tuple[str,float], ...] | None:
    rows=point.get('inputs')
    if not isinstance(rows,list) or not rows:return None
    seen=set();pairs=[]
    for row in rows:
        if not isinstance(row,dict):return None
        root=row.get('root');weight=_num(row.get('weight'))
        if not isinstance(root,str) or not root or root.strip()!=root or root in seen or weight is None or weight<=0:
            return None
        seen.add(root)
        pairs.append((root,weight))
    if abs(fsum(v for _,v in pairs)-1)>1e-12:return None
    return tuple(sorted(pairs))


def _observation(point: Mapping, *, asof: datetime) -> float | None:
    """Revalidate a full qualified owner envelope; numeric input isn't authority."""
    if point.get('schema')!='options_hub.factor_options/v1':return None
    if not isinstance(point.get('factor_ref'),str) or not point['factor_ref']:return None
    source=_aware(point.get('asof'))
    if source is None or source>asof:return None
    session=_session(point.get('source_session'))
    if session is None:return None
    definition=point.get('definition')
    if (not isinstance(definition,dict) or not isinstance(definition.get('source_ref'),str)
        or not isinstance(definition.get('sha256'),str) or not _DIGEST.fullmatch(definition['sha256'])):return None
    def_known=_aware(definition.get('known_at'))
    if def_known is None or def_known>source:return None
    horizon=point.get('horizon')
    if horizon != {'days':30,'basis':'ACT/365F','unit':'calendar_day'}:return None
    if point.get('authority')!={'display_only':True,'publication':False,'prophet':False,'position_sizing':False}:return None
    members=_weights(point)
    if members is None:return None
    rows=point['inputs'];coverage=point.get('coverage')
    if (not isinstance(coverage,dict) or coverage.get('count')!=len(members)
        or coverage.get('total_count')!=len(members)
        or coverage.get('excluded')!=[]
        or (_num(coverage.get('weight')) is None or abs(coverage['weight']-1)>1e-12)):
        return None
    values={}
    for row in rows:
        if _session(row.get('source_session')) != session:return None
        if row.get('qualified') is not True:return None
        if row.get('method') not in ('iv30_exact_act365f','iv30_total_variance_act365f'):
            return None
        if row.get('year_basis')!='ACT/365F' or _num(row.get('tenor_calendar_days'))!=30:return None
        iv=_num(row.get('iv'))
        if iv is None or iv<0:return None
        if not isinstance(row.get('source_ref'),str) or not row.get('source_ref'):return None
        if not isinstance(row.get('sha256'),str) or not _DIGEST.fullmatch(row['sha256']):return None
        obs,known,deadline=(_aware(row.get(k)) for k in ('observed_at','known_at','valid_until'))
        if obs is None or known is None or deadline is None or not obs<=known<=source<deadline:
            return None
        values[row['root']]=iv
    if len(values)!=len(members):return None
    computed=fsum(weight*values[root] for root,weight in members)
    advertised=point.get('covered')
    if not isinstance(advertised,dict):return None
    summary=_num(advertised.get('mean_iv'))
    headline=_num(point.get('headline_mean_iv'))
    if summary is None or abs(summary-computed)>1e-10:raise ValueError('source mean disagrees with constituent aggregation')
    if headline is None:return None  # Respect the incumbent producer's headline policy.
    if abs(headline-computed)>1e-10:raise ValueError('headline mean disagrees with constituent aggregation')
    return computed


def _policy_vintage(point: Mapping) -> tuple | None:
    """The incumbent coverage gate is part of the history's source identity.

    If the owner changes the admission policy or even only a threshold,
    an otherwise complete historical observation needs an explicit
    comparable-vintage rebuild; do not silently reuse its IV percentile.
    """
    name=point.get('policy')
    params=point.get('policy_parameters')
    fields=('min_weight','min_count_fraction','min_names',
            'max_missing_name_weight','premium_dominance',
            'full_risk_requires_complete_coverage')
    if not isinstance(name,str) or not name or name.strip()!=name:
        return None
    if not isinstance(params,dict) or set(params)!=set(fields):
        return None
    if type(params.get('min_names')) is not int or params['min_names']<1:
        return None
    if params.get('full_risk_requires_complete_coverage') is not True:
        return None
    values=tuple(_num(params.get(k)) for k in fields[:2]+fields[3:5])
    if any(v is None or not 0<=v<=1 for v in values):
        return None
    return (name, params['min_names'], values, True)


def _iv_method_vintage(point: Mapping) -> tuple | None:
    """Keep method identity by root, not by row presentation order."""
    entries=point.get('inputs')
    if not isinstance(entries,list) or not entries:
        return None
    signatures=[]
    for row in entries:
        if not isinstance(row,dict) or not isinstance(row.get('root'),str):
            return None
        method=row.get('method')
        if method not in ('iv30_exact_act365f','iv30_total_variance_act365f'):
            return None
        signatures.append((row['root'],method))
    return tuple(sorted(signatures))


def summarize_iv_history(points: Sequence[Mapping], *, expected_sessions: Sequence[date], asof: datetime) -> dict:
    """Compute min/max rank and empirical midrank percentile over exactly 252 days.

    One expected cash session means one source-comparable basket observation.
    Its explicit source_session and each constituent's session must agree.
    Envelope asof is the evaluation/availability clock, not the market date;
    later receipt never rewrites that date or permits earlier knowledge.
    Without all 252 source-qualified sessions, both headline statistics are
    null and the full original session denominator is retained.
    """
    if not isinstance(asof,datetime) or asof.tzinfo is None or asof.utcoffset() is None:
        raise ValueError('timezone-aware evaluation time required')
    if not isinstance(expected_sessions,Sequence) or len(expected_sessions)!=252 or any(type(s) is not date for s in expected_sessions):
        raise ValueError('exact 252-session incumbent calendar required')
    days=list(expected_sessions)
    if days!=sorted(set(days)):
        raise ValueError('duplicate or unordered incumbent cash sessions')
    if not isinstance(points,Sequence) or not points:
        raise ValueError('nonempty source-qualified basket observations required')
    byday={};reasons=[]
    definitions=set();factor_refs=set();policy_vintages=set();method_vintages=set()
    baseline_weights=None
    for point in points:
        if not isinstance(point,Mapping):
            raise ValueError('typed aggregate source envelope required')
        recorded=_aware(point.get('asof'))
        if recorded is None:raise ValueError('aware source observation time required')
        if recorded>asof:raise ValueError('future observation as-of leaked into history')
        day=_session(point.get('source_session'))
        if day is None:raise ValueError('explicit canonical source session required')
        if day not in days:raise ValueError('source observation outside expected calendar')
        if day in byday:raise ValueError('duplicate source history session')
        item=_observation(point,asof=asof)
        byday[day]=item
        factor_refs.add(point.get('factor_ref'))
        policy_vintages.add(_policy_vintage(point))
        method_vintages.add(_iv_method_vintage(point))
        definition=point.get('definition')
        if isinstance(definition,dict):definitions.add((definition.get('source_ref'),definition.get('sha256')))
        point_weights=_weights(point)
        if baseline_weights is None:
            baseline_weights=point_weights
        elif point_weights!=baseline_weights:
            reasons.append('INCOMPATIBLE_BASKET_WEIGHTS')
    if len(factor_refs)!=1 or any(not isinstance(x,str) or not x for x in factor_refs):
        reasons.append('INCOMPATIBLE_FACTOR_IDENTITY')
    if len(definitions)!=1:
        reasons.append('INCOMPATIBLE_BASKET_DEFINITION')
    if None in policy_vintages:
        reasons.append('COVERAGE_POLICY_UNQUALIFIED')
    if len(policy_vintages)!=1:
        reasons.append('INCOMPATIBLE_COVERAGE_POLICY')
    if None in method_vintages:
        reasons.append('IV_METHOD_VINTAGE_UNQUALIFIED')
    if len(method_vintages)!=1:
        reasons.append('INCOMPATIBLE_IV_METHOD_VINTAGE')
    if any(value is None for value in byday.values()):reasons.append('UNQUALIFIED_POINT')
    qualified=[v for v in byday.values() if v is not None]
    complete=len(qualified)==252 and len(byday)==252
    if not complete:reasons.append('INCOMPLETE_SESSION_COVERAGE')
    if (len(definitions)!=1 or len(factor_refs)!=1 or
        len(policy_vintages)!=1 or None in policy_vintages or
        len(method_vintages)!=1 or None in method_vintages or
        'INCOMPATIBLE_BASKET_WEIGHTS' in reasons):
        complete=False
    rank=percentile=None
    current=byday.get(days[-1])
    low,high=None,None
    if complete:
        low=min(qualified);high=max(qualified)
        if high==low:reasons.append('DEGENERATE_IV_RANGE')
        else:rank=100*(current-low)/(high-low)
        below=sum(v<current for v in qualified)
        equals=sum(v==current for v in qualified)
        percentile=100*(below+0.5*equals)/len(qualified)
    return {'schema':'options_hub.factor_iv_history/v1',
            'basis':'full_coverage_constituent_mean_iv_not_traded_basket_iv',
            'factor_ref':next(iter(factor_refs)) if len(factor_refs)==1 else None,
            'asof':asof.isoformat(),
            'current_source_session':days[-1].isoformat(),
            'history_window':{'cash_sessions':252,'selection':'owner_calendar_strict','includes_current_session':True,
                              'session_key':'source_session',
                              'tie_convention':'midrank_half_of_equals','rank_convention':'min_max_0_to_100'},
            'coverage':{'qualified_sessions':len(qualified),
                        'expected_sessions':252,'missing_or_unqualified_sessions':252-len(qualified),
                        'fraction':len(qualified)/252},
            'current_constituent_mean_iv':current if complete else None,
            'min_iv':low,'max_iv':high,'iv_rank_minmax_pct':rank,
            'iv_percentile_midrank_pct':percentile,
            'definition':list(definitions)[0] if len(definitions)==1 else None,
            'reasons':sorted(set(reasons)),
            'authority':{'display_only':True,'publication':False,'prophet':False,'position_sizing':False}}
