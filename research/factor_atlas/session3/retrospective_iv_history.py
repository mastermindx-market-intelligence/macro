"""Private retrospectively reconstructed constituent-IV history, never an admitted feed.

The existing source owner retains all options chains, clocks and licenses. This
pure study takes numerical results of the same legacy EOD Greek selector for
the exact declared house roster and calendar. Unknown historical quote/mark
and publication provenance is *not* converted into a source-qualified rank.
Only descriptive PRIVATE research statistics can appear here.
"""
from __future__ import annotations

from collections import Counter
from datetime import date,datetime
from math import fsum,isfinite,sqrt
from numbers import Real
from typing import Mapping,Sequence
import re

from lib.us_cash_calendar import expected_last_session

_ROOT=re.compile(r"^[A-Z][A-Z0-9.-]{0,11}$")


def _number(v:object)->float|None:
    if isinstance(v,bool) or not isinstance(v,Real):
        return None
    try:
        n=float(v)
    except (OverflowError, ValueError):
        return None
    return n if isfinite(n) else None


def summarize_private_history(*,sessions:Sequence[date], weights:Mapping[str,float],
                            observed:Mapping[date,Mapping[str,dict]], captured_at:datetime)->dict:
    """Full-denominator 252-session research with separate current vs rank admission.

    A missing root/session is observable failure, not a denominator or universe
    change. Rank and percentile require 252/252 complete basket estimates.
    Even 252/252 numbers remain private retrospective research because all
    sources lack historical known-at/mark/entitlement attestation.
    """
    if (not isinstance(captured_at,datetime) or captured_at.tzinfo is None
        or captured_at.utcoffset() is None):
        raise ValueError("source acquisition needs an aware clock")
    if not isinstance(sessions,Sequence) or len(sessions)!=252 or any(type(d) is not date for d in sessions):
        raise ValueError("exact 252-source-session calendar required")
    sessions=list(sessions)
    if sessions!=sorted(set(sessions)):
        raise ValueError("duplicate or unordered source sessions")
    if sessions[-1]>expected_last_session(captured_at):
        raise ValueError("source calendar date cannot exceed capture's last completed session")
    if (not isinstance(weights,Mapping) or not 3<=len(weights)<=50 or
        any(not isinstance(r,str) or not _ROOT.fullmatch(r) or
            _number(w) is None or _number(w)<=0 for r,w in weights.items()) or
        abs(fsum(float(w) for w in weights.values())-1)>1e-12):
        raise ValueError("unchanged original basket positive weights required")
    if not isinstance(observed,Mapping):
        raise ValueError("date-keyed research observations required")
    if set(observed)-set(sessions):
        raise ValueError("observations outside expected calendar")
    roots=sorted(weights)
    covered_root={r:0 for r in roots}
    missing_by_root=Counter()
    failure_reasons=Counter()
    full_source_absences=[]
    partly_covered=[]
    all_unusable=[]
    output=[]
    for day in sessions:
        sources=observed.get(day,{})
        if not isinstance(sources,Mapping) or set(sources)-set(roots):
            raise ValueError("unrecognized research root identity")
        good={}
        reason_codes=[]
        for root in roots:
            obs=sources.get(root)
            reasons=[]
            if not isinstance(obs,Mapping):
                reasons=["SOURCE_OR_NAME_MISSING"]
            else:
                val=_number(obs.get("iv30"))
                reasons=obs.get("reasons")
                if not isinstance(reasons,list) or any(not isinstance(v,str) or not v for v in reasons):
                    raise ValueError("source selection reason vocabulary required")
                if val is None or not 0<val<=2.5:
                    reasons=reasons or ["IV_QUALITY_OR_TENOR_UNAVAILABLE"]
            if reasons:
                reason_codes.extend(reasons)
                missing_by_root[root]+=1
                failure_reasons.update(reasons)
                continue
            good[root]=val
            covered_root[root]+=1
        if not sources:
            full_source_absences.append(day.isoformat())
        if 0<len(good)<len(roots):
            partly_covered.append(day.isoformat())
        if not good:
            all_unusable.append(day.isoformat())
        original_weight=fsum(float(weights[r]) for r in good)
        full=len(good)==len(roots)
        subset=(fsum(float(weights[r])*good[r] for r in good)/original_weight) if original_weight else None
        output.append({
            "session":day.isoformat(),
            "covered_count":len(good),
            "original_count":len(roots),
            "covered_weight":float(original_weight),
            "missing_roots":sorted(set(roots)-set(good)),
            "full_basket_mean_iv":subset if full else None,
            "eligible_subset_mean_iv":subset,
            "reasons":sorted(set(reason_codes))
        })
    count=sum(row["full_basket_mean_iv"] is not None for row in output)
    eligible=count==252
    current=output[-1]["full_basket_mean_iv"]
    values=[row["full_basket_mean_iv"] for row in output if row["full_basket_mean_iv"] is not None]
    reasons=[] if eligible else ["INCOMPLETE_SESSION_COVERAGE"]
    min_value=max_value=rank=percentile=None
    if eligible:
        min_value=min(values)
        max_value=max(values)
        if max_value==min_value:
            reasons.append("DEGENERATE_IV_RANGE")
        else:
            rank=100*(current-min_value)/(max_value-min_value)
        below=sum(v<current for v in values)
        equal=sum(v==current for v in values)
        percentile=100*(below+.5*equal)/252
    return {
        "schema":"factor_atlas.s3.private_iv_history/v1",
        "classification":"PRIVATE_RETROSPECTIVE_RESEARCH_NO_AS_KNOWN",
        "source_type":"retrospective_date_only_legacy_options",
        "asof_session":sessions[-1].isoformat(),
        "captured_at":captured_at.isoformat(),
        "historical_known_at":None,
        "population":{"roots":roots,
                      "weights":{r:float(weights[r]) for r in roots},
                      "basis":"current_house_roster_not_historical_point_in_time"},
        "coverage":{"expected_sessions":252,"complete_sessions":count,
                    "fraction":count/252,"per_root":covered_root,
                    "incomplete_sessions":252-count,
                    "failure_diagnostics":{
                       "all_root_source_missing_sessions":full_source_absences,
                       "all_root_unusable_sessions":all_unusable,
                       "partly_covered_sessions":partly_covered,
                       "missing_by_root":{r:missing_by_root[r] for r in roots},
                       "failure_reasons":dict(sorted(failure_reasons.items()))}},
        "series":output,
        "stats":{"current_mean_iv":current,"min_iv":min_value,"max_iv":max_value,
                 "iv_rank_minmax_pct":rank,"iv_percentile_midrank_pct":percentile,
                 "population":"whole-house-basket_constituent_mean_iv",
                 "tie_policy":"midrank_half_of_equals_including_current"},
        "reasons":reasons,
        "source_quality":{"historical_quote_timestamps_available":False,
                          "historical_known_at_certified":False,
                          "price_mark_model_certified":False,
                          "redistribution_rights_certified":False},
        "product":{"qualified":False,"iv_rank":None,"iv_percentile":None},
        "authority":{"publication":False,"prophet":False,"position_sizing":False},
    }
