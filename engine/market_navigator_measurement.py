"""Measurement-context annotations, not volatility forecasts or a calendar owner.

The VIX1D phase labels describe Cboe's published methodology; they do not attest
that a feed actually performed each calculation. All session instants and their
availability come from the incumbent calendar/data owner, including early closes.
No guessed exchange schedule, rolling threshold, price series or trading rule.
"""
from dataclasses import dataclass
from typing import Any
from engine.market_navigator import AUTHORITY, ContractError, _clock, _ref

METHOD = 'cboe.vix1d.measurement-phase.launch-description-2023-04-24'
SOURCE = 'https://www.cboe.com/insights/posts/what-the-vix-and-vix-1-d-indices-attempt-to-measure-and-how-they-differ/'


@dataclass(frozen=True)
class IndexSession:
    session_ref: str
    source_revision: str
    available_at: str
    dissemination_start: str
    near_expiry: str
    dissemination_end: str

    def __post_init__(self):
        _ref(self.session_ref); _ref(self.source_revision)
        available, start, expiry, end = map(_clock, (self.available_at,
            self.dissemination_start,self.near_expiry,self.dissemination_end))
        if not start < expiry <= end:
            raise ContractError('session instants are not ordered')
        if available > end:
            raise ContractError('calendar evidence unavailable throughout the session')


def vix1d_measurement_context(*, observed_at: str, as_of: str,
                              session: IndexSession | None) -> dict[str, Any]:
    observed, cutoff = _clock(observed_at), _clock(as_of)
    out = {'schema':'market_navigator.vol_measurement/v1', 'method':METHOD,
        'observed_at':observed.isoformat(), 'as_of':cutoff.isoformat(),
        'phase':None, 'minutes_to_near_expiry':None,
        'methodology_annotation_only':True, 'directional_signal':False,
        'authority':dict(AUTHORITY)}
    if observed > cutoff:
        return out | {'status':'observation_not_yet_available'}
    if session is None:
        return out | {'status':'calendar_evidence_missing'}
    if not isinstance(session,IndexSession):
        raise ContractError('typed owner-supplied session required')
    if _clock(session.available_at) > cutoff:
        return out | {'status':'calendar_evidence_not_yet_available'}
    start,expiry,end=map(_clock,(session.dissemination_start,session.near_expiry,
                               session.dissemination_end))
    if not start <= observed <= end:
        return out | {'status':'outside_supplied_dissemination_window'}
    remaining=(expiry-observed).total_seconds()/60
    if remaining <= 0:
        phase='next_term_only'
    elif remaining < 60:
        phase='persisted_near_term_interpolation'
    else:
        phase='near_and_next_term'
    return out | {'status':'annotated', 'phase':phase,
        'minutes_to_near_expiry':max(0.0,remaining),
        'session_ref':session.session_ref, 'source_revision':session.source_revision}


def threshold_study_coverage(*, frequency: str, original_availability: bool,
        joint_underlying: bool, executable_option_quotes: bool,
        ordering_resolved: bool) -> dict:
    """Assess declared coverage only; never validates provenance or an alpha trial.

    No outcomes are read. Metadata flags are not admission grants. The research
    owner still verifies actual records, rights, registration and source lineage.
    """
    if frequency not in {'tick','second','minute','daily','unknown'}:
        raise ContractError('unknown measurement frequency')
    flags=(original_availability,joint_underlying,executable_option_quotes,ordering_resolved)
    if any(type(value) is not bool for value in flags):
        raise ContractError('coverage fields must be actual booleans')
    reasons=[]
    if frequency in {'daily','unknown'}: reasons.append('intraday_trigger_time_unobserved')
    if not original_availability: reasons.append('original_availability_unobserved')
    if not joint_underlying: reasons.append('joint_underlying_unobserved')
    if not executable_option_quotes: reasons.append('option_execution_unobserved')
    if not ordering_resolved: reasons.append('path_order_unresolved')
    return {'schema':'market_navigator.study_coverage/v1','frequency':frequency,
        'status':'declared_coverage_incomplete' if reasons else 'declared_coverage_only',
        'missing_requirements':reasons,'source_verified':False,'trial_admitted':False,
        'predictive_validation':False,'authority':dict(AUTHORITY)}
