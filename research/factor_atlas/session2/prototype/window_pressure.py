"""Pure cumulative projection over the existing research Bar/Membership types.

No ingest, revision selection, calendar generation, permission or publication.
Calendar/membership/rights/basis/availability must be qualified by their owners.
A complete estimate includes explicit policy-neutral rows; it is not tape truth.
"""
from __future__ import annotations
from collections import defaultdict
from dataclasses import asdict, dataclass
import math
from typing import Iterable, Sequence
import pressure as m


@dataclass(frozen=True)
class WindowContribution:
    security_id: str
    expected_cells: int
    observed_cells: int
    first_missing_utc_s: int | None
    observed_gross_usd: float
    estimated_net_observed_usd: float
    directionally_usable_gross_usd: float
    policy_neutral_gross_usd: float
    other_estimated_gross_usd: float
    unestimated_gross_usd: float


@dataclass(frozen=True)
class WindowFactor:
    factor_id: str
    membership_version: str
    membership_basis: str
    status: str
    expected_cells: int
    observed_cells: int
    missing_cells: int
    observed_gross_usd: float
    full_gross_usd: float | None
    estimated_net_observed_usd: float
    full_estimated_net_usd: float | None
    directionally_usable_gross_usd: float
    policy_neutral_gross_usd: float
    other_estimated_gross_usd: float
    unestimated_gross_usd: float
    availability_eligible: bool
    source_known_at_utc_s: int | None
    contributions: tuple[WindowContribution, ...]
    gross_reference: m.Reference | None
    net_reference: m.Reference | None
    input_digest: str


@dataclass(frozen=True)
class WindowPressure:
    session_id: str
    start_utc_s: int
    end_utc_s: int
    mode: str
    estimator_id: str
    factors: tuple[WindowFactor, ...]
    union_observed_gross_usd: float
    sum_factor_observed_gross_usd: float
    duplicated_gross_usd: float
    overlap: tuple[tuple[str, tuple[str, ...]], ...]
    input_digest: str
    authority: tuple[tuple[str, bool], ...] = m.AUTHORITY


def _sum(values: Iterable[float]) -> float:
    try:
        return m._finite(math.fsum(values), 'window_sum')
    except OverflowError:
        raise ValueError('window_sum_overflow') from None


def _segments(segments: Sequence[m.Segment], start: int, end: int,
              cutoff: int) -> tuple[m.Segment, ...]:
    for value, name in ((start,'window_start'),(end,'window_end'),(cutoff,'cutoff')):
        m._integer(value, name)
    if start % 60 or end % 60 or not 0 < end-start <= 960*60:
        raise ValueError('invalid_minute_window')
    if cutoff < end:
        raise ValueError('window_not_closed')
    if not segments or len(segments)>3 or any(not isinstance(s,m.Segment) for s in segments):
        raise ValueError('qualified_segments_required')
    ordered=tuple(sorted(segments,key=lambda s:s.start_utc_s))
    for s in ordered:
        s.validate()
        if s.start_utc_s % 60 or s.end_utc_s % 60:
            raise ValueError('segment_minute_alignment')
    identities={(s.session_id,s.calendar_ref,s.session_class) for s in ordered}
    if len(identities)!=1:
        raise ValueError('mixed_segment_identity')
    if any(a.end_utc_s!=b.start_utc_s for a,b in zip(ordered,ordered[1:])):
        raise ValueError('segment_gap_or_overlap')
    if not ordered[0].start_utc_s<=start<end<=ordered[-1].end_utc_s:
        raise ValueError('window_outside_segments')
    return ordered


def measure_windows(bars: Iterable[m.Bar], memberships: Sequence[m.Membership],
                    segments: Sequence[m.Segment], *, start_utc_s: int,
                    end_utc_s: int, cutoff_utc_s: int, config: m.BVCConfig,
                    mode: str='as_observed') -> WindowPressure:
    """Compute once at cutoff, then reduce many explicit factor windows.

    No caller-supplied later-cutoff PressurePoint can enter this API. Inputs
    before the window are retained only as same-session estimator history.
    Missing source rows never acquire zero values or observation timestamps.
    """
    config.validate()
    if mode not in ('as_observed','corrected_history'):
        raise ValueError('invalid_mode')
    segs=_segments(segments,start_utc_s,end_utc_s,cutoff_utc_s)
    if not memberships or any(not isinstance(g,m.Membership) for g in memberships):
        raise ValueError('memberships_required')
    # Reuse incumbent pure membership/duplicate validation, not a new registry.
    topology=m.aggregate_factors((),memberships)
    groups=tuple(sorted(memberships,key=lambda g:g.factor_id))
    members=set(sid for g in groups for sid in g.member_ids)
    membership_of=defaultdict(list)
    for g in groups:
        for sid in g.member_ids:
            membership_of[sid].append(g.factor_id)
    admitted=[]
    basis_by_id=defaultdict(set)
    for bar in bars:
        if not isinstance(bar,m.Bar):
            raise ValueError('bar_required')
        if bar.security_id not in members:
            continue
        m._integer(bar.end_utc_s,'bar_end')
        if bar.end_utc_s>end_utc_s or bar.end_utc_s<=segs[0].start_utc_s:
            continue
        if mode=='as_observed':
            if bar.available_at_utc_s is None:
                raise ValueError('availability_missing')
            m._integer(bar.available_at_utc_s,'available_at')
            if bar.available_at_utc_s>cutoff_utc_s:
                continue
        m._validate_bar(bar)
        if bar.segment not in segs:
            raise ValueError('source_segment_mismatch')
        basis_by_id[bar.security_id].add(bar.basis_id)
        admitted.append(bar)
    if any(len(values)!=1 for values in basis_by_id.values()):
        raise ValueError('mixed_security_monetary_basis')
    points=m.bvc_series(admitted,config,cutoff_utc_s=cutoff_utc_s,mode=mode)
    history_by_id=defaultdict(list)
    selected_by_id=defaultdict(list)
    for point in points:
        history_by_id[point.bar.security_id].append(point)
        if start_utc_s<=point.bar.start_utc_s and point.bar.end_utc_s<=end_utc_s:
            selected_by_id[point.bar.security_id].append(point)
    # ET shape matches across DST without using a guessed holiday calendar.
    shape={'calendar_ref':segs[0].calendar_ref,'session_class':segs[0].session_class,
           'anchor_minute_et':m._et_clock(start_utc_s)[1],
           'end_minute_et':m._et_clock(end_utc_s)[1],
           'segments':[(s.phase,m._et_clock(max(s.start_utc_s,start_utc_s))[1],
                        m._et_clock(min(s.end_utc_s,end_utc_s))[1]) for s in segs
                       if s.start_utc_s<end_utc_s and s.end_utc_s>start_utc_s],
           'mode':mode,'reducer':'factor_atlas.cumulative_window.v1'}
    estimator_id=config.identity+':window:'+m.digest(shape)
    end_segment=next(s for s in segs if s.start_utc_s<end_utc_s<=s.end_utc_s)
    slots=(end_utc_s-start_utc_s)//60
    factors=[]
    # The same immutable PressurePoint contributes to the union digest and
    # often several overlapping factor membership digests. Materialize its
    # canonical dataclass structure once at this evaluation cutoff; reuse
    # without mutating it or changing the original digest order or content.
    point_docs_by_id={sid:tuple(asdict(p) for p in history_by_id[sid])
                      for sid in sorted(history_by_id)}
    outer_digest=m.digest({'shape':shape,'start':start_utc_s,'end':end_utc_s,
        'estimator':estimator_id,'groups':[asdict(g)|{'member_ids':sorted(g.member_ids)} for g in groups],
        'points':[doc for sid in sorted(point_docs_by_id)
                  for doc in point_docs_by_id[sid]]})
    for group in groups:
        ids=tuple(sorted(group.member_ids))
        selected=[p for sid in ids for p in selected_by_id[sid]]
        history=[p for sid in ids for p in history_by_id[sid]]
        contributions=[]
        for sid in ids:
            rows=selected_by_id[sid]
            present={p.bar.start_utc_s for p in rows}
            first_missing=next((t for t in range(start_utc_s,end_utc_s,60) if t not in present),None)
            contributions.append(WindowContribution(sid,slots,len(rows),first_missing,
                _sum(p.gross_usd for p in rows),
                _sum(p.net_usd for p in rows if p.net_usd is not None),
                _sum(p.gross_usd for p in rows if p.directionally_usable),
                _sum(p.gross_usd for p in rows if not p.directionally_usable and p.buy_fraction==.5),
                _sum(p.gross_usd for p in rows if not p.directionally_usable and p.buy_fraction not in (None,.5)),
                _sum(p.gross_usd for p in rows if p.net_usd is None)))
        gross=_sum(c.observed_gross_usd for c in contributions)
        net=_sum(c.estimated_net_observed_usd for c in contributions)
        expected=slots*len(ids);observed=len(selected)
        complete=observed==expected
        net_complete=complete and all(p.net_usd is not None for p in selected)
        eligible=(mode=='as_observed' and bool(history)
                  and all(p.bar.available_at_utc_s is not None and p.bar.available_at_utc_s<=cutoff_utc_s for p in history))
        known=max(p.bar.available_at_utc_s for p in history) if eligible else None
        member_identity=m.digest({'version':group.version,'basis':group.basis,'members':ids})
        money_identity=m.digest([(sid,sorted(basis_by_id[sid]),
                    sorted({p.gross_basis for p in history_by_id[sid]})) for sid in ids])
        result_digest=m.digest({'membership':member_identity,'start':start_utc_s,'end':end_utc_s,
            'estimator':estimator_id,'points':[doc for sid in ids
                for doc in point_docs_by_id.get(sid,())]})
        def reference(measure: str,value: float) -> m.Reference:
            key=m.MatchKey(group.factor_id,end_segment.phase,m._et_clock(end_utc_s)[1],
                segs[0].session_class,measure,estimator_id,'members:'+member_identity,
                'monetary_basis:'+money_identity,end_utc_s-start_utc_s,'USD')
            ref=m.Reference(key,segs[0].session_id,end_utc_s,known,value,gross,True,result_digest)
            ref.validate()
            return ref
        gross_ref=reference('cumulative_gross_usd',gross) if complete and eligible else None
        net_ref=reference('cumulative_estimated_net_usd',net) if net_complete and eligible else None
        status='PARTIAL_COVERAGE' if not complete else 'COMPLETE_ESTIMATE' if net_complete else 'DIRECTION_UNAVAILABLE'
        factors.append(WindowFactor(group.factor_id,group.version,group.basis,status,expected,observed,
            expected-observed,gross,gross if complete else None,net,net if net_complete else None,
            _sum(c.directionally_usable_gross_usd for c in contributions),
            _sum(c.policy_neutral_gross_usd for c in contributions),
            _sum(c.other_estimated_gross_usd for c in contributions),
            _sum(c.unestimated_gross_usd for c in contributions),eligible,known,
            tuple(contributions),gross_ref,net_ref,result_digest))
    union=_sum(p.gross_usd for sid in sorted(selected_by_id) for p in selected_by_id[sid])
    total=_sum(f.observed_gross_usd for f in factors)
    duplicate=_sum(p.gross_usd*(len(membership_of[sid])-1)
                   for sid in sorted(selected_by_id) for p in selected_by_id[sid])
    return WindowPressure(segs[0].session_id,start_utc_s,end_utc_s,mode,estimator_id,
                          tuple(factors),union,total,duplicate,topology.overlap,outer_digest)
