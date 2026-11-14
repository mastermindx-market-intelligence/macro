"""Read-only adapter from the existing release-target vintage owner to research.

This is not a collector, observation store, release calendar, or forecast model.
Manifest/byte integrity is distinct from source authority, historical system
availability, model calibration, and production adoption. Daily as-of means the
end of the source vintage date, never a pre-release intraday decision.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import date, datetime
from hashlib import sha256
from io import BytesIO
import json
from math import isfinite
from numbers import Integral, Real
from pathlib import Path
import re
from typing import Callable, Mapping, Sequence

import pandas as pd

from engine import release_target_truth as release_truth
from engine.macro_turnaround import (
    AuthorityBoundary, IndicatorSpec, MacroTurnaroundEngine, Observation, Phase,
    Transform, TurnaroundConfig, _coerce_date, _content_hash, build_research_artifact,
)
from scripts.build_macro_turnaround_research import _unique_object, _reject_constant

_ALLOWED_FAMILIES = frozenset({'labor', 'activity', 'housing', 'consumer', 'credit', 'inflation'})
_MANIFEST_PATH = Path('data/fred_vintage/release_targets/manifest.json')
_COLUMNS = ('series', 'period', 'realtime_start', 'realtime_end', 'value', 'source_output_type')
_METHOD_NOTE = ('Research phase and standardized slope anomaly are unvalidated; '
                'anomaly is deviation from historical movement, not economic direction. '
                'Observed input movement is separate. No calibrated forecast or trade authority.')


@dataclass(frozen=True)
class SeriesBinding:
    key: str
    series_id: str | None
    family: str
    weight: float = 1.0
    transform: str = 'level'
    positive_when_rising: bool = True
    max_age_days: int = 100
    minimum_history: int = 18

    def __post_init__(self) -> None:
        spec = self.spec()
        if self.key != spec.key or self.family != spec.family:
            raise ValueError('binding key and family must be canonical strings')
        if self.family not in _ALLOWED_FAMILIES:
            raise ValueError('unknown evidence family')
        if self.series_id is not None:
            if self.series_id not in release_truth.SUPPORTED_SERIES:
                raise ValueError('unsupported full-vintage series; no initial-print fallback')
            expected = 'labor' if self.series_id == 'PAYEMS' else 'inflation'
            if self.family != expected:
                raise ValueError(f'{self.series_id} belongs to the {expected} family')

    def spec(self) -> IndicatorSpec:
        return IndicatorSpec(self.key, self.family, self.weight, Transform(self.transform),
                             self.positive_when_rising, self.max_age_days, self.minimum_history)


@dataclass(frozen=True)
class VintageRow:
    series: str
    period: date
    start: date
    end: date
    value: float


@dataclass(frozen=True)
class VintagePanel:
    rows: tuple[VintageRow, ...]
    series_ids: tuple[str, ...]
    _receipt_json: str

    @property
    def receipt(self) -> dict:
        return json.loads(self._receipt_json)


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _day(value: object, field: str) -> date:
    # A native Parquet timestamp must already be a naive midnight daily value.
    # Unlike the owner normalizer, no timezone or intraday information is erased.
    if isinstance(value, datetime):
        if pd.isna(value) or value.tzinfo is not None or value.time() != datetime.min.time():
            raise ValueError(f'{field} must be a naive midnight daily value')
        return value.date()
    try:
        return _coerce_date(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{field} must be a canonical daily date') from exc


def _clock(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError('collection clock must be an aware timestamp')
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('invalid collection clock') from exc
    if dt.tzinfo is None:
        raise ValueError('collection clock must be timezone-aware')
    return dt


def _strict_frame(frame: pd.DataFrame, sid: str) -> pd.DataFrame:
    if not isinstance(frame, pd.DataFrame) or not frame.columns.is_unique:
        raise ValueError('full-vintage input must have unique dataframe columns')
    if not set(_COLUMNS).issubset(frame.columns):
        raise ValueError(f'full-vintage input requires columns {_COLUMNS}, including source_output_type')
    if frame.empty:
        raise ValueError('empty full-vintage input cannot qualify a collected source')
    clean=[];seen={}
    for series, period, start, end, value, marker in frame.loc[:, _COLUMNS].itertuples(index=False, name=None):
        if series != sid or not isinstance(series, str):
            raise ValueError('series identity mismatch; no coercion or cross-series filtering')
        if isinstance(marker, bool) or not isinstance(marker, Integral) or marker != 2:
            raise ValueError('source_output_type must be the integer 2')
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError('value must be finite numeric, not a coerced scalar')
        try:
            number = float(value)
        except (ValueError, OverflowError) as exc:
            raise ValueError('value must be finite') from exc
        if not isfinite(number):
            raise ValueError('value must be finite')
        number = 0.0 if number == 0.0 else number
        p, s, e = _day(period, 'period'), _day(start, 'realtime_start'), _day(end, 'realtime_end')
        if p.day != 1:
            raise ValueError('monthly period must be the first day of the month')
        if e < s:
            raise ValueError('reversed realtime interval')
        key = (p, s)
        pair = (e, number)
        if key in seen and seen[key] != pair:
            raise ValueError('conflicting value or expiration for one vintage')
        seen[key] = pair
        clean.append((series, pd.Timestamp(p), pd.Timestamp(s), e, number, 2))
    checked = pd.DataFrame(clean, columns=_COLUMNS)
    # One existing owner; the strict adapter prevents its permissive coercions
    # from silently deleting bad rows or erasing unknown time information.
    normalized = release_truth.normalize_full_vintage_frame(checked, series_id=sid)
    if len(normalized) != len(seen):
        raise ValueError('canonical normalization unexpectedly removed observations')
    return normalized


def prepare_panel(frames: Mapping[str, pd.DataFrame]) -> VintagePanel:
    """Adapt detached frames. Without a byte-bound loader this is research input."""
    if not isinstance(frames, Mapping) or not frames:
        raise ValueError('at least one full-vintage frame is required')
    rows=[]
    for sid in sorted(frames):
        if sid not in release_truth.SUPPORTED_SERIES:
            raise ValueError('unsupported full-vintage series')
        normalized=_strict_frame(frames[sid], sid)
        rows.extend(VintageRow(sid, r.period.date(), r.realtime_start.date(), r.realtime_end, float(r.value))
                    for r in normalized.itertuples(index=False))
    rows.sort(key=lambda r:(r.series,r.period,r.start))
    return VintagePanel(tuple(rows), tuple(sorted(frames)), _json({
        'integrity_verified':False, 'production_parser_executed':False,
        'source_basis':'full_vintage_frames', 'historical_system_availability_proven':False,
        'normalization_owner':'engine.release_target_truth.normalize_full_vintage_frame',
    }))


def _bindings(bindings: Sequence[SeriesBinding]) -> tuple[SeriesBinding, ...]:
    if not bindings or any(not isinstance(b, SeriesBinding) for b in bindings):
        raise ValueError('nonempty validated bindings required')
    keys=[b.key for b in bindings];sids=[b.series_id for b in bindings if b.series_id is not None]
    if len(set(keys))!=len(keys) or len(set(sids))!=len(sids):
        raise ValueError('duplicate binding key or source series')
    return tuple(sorted(bindings,key=lambda b:b.key))


def _read_snapshot(path: Path, limit: int) -> bytes:
    if path.is_symlink():
        raise ValueError('source file must not be a symbolic link')
    with path.open('rb') as handle:
        content=handle.read(limit+1)
    if len(content)>limit:
        raise ValueError('source exceeds the bounded snapshot limit')
    return content


def load_panel(root: str | Path, bindings: Sequence[SeriesBinding], expected_manifest_sha256: str,
               *, decoder: Callable[[BytesIO],pd.DataFrame] | None=None) -> VintagePanel:
    """Read one pinned cohort; verify ALL selected bytes before decoding any.

    The optional decoder is an explicit laboratory/test seam. Its use is always
    disclosed as not executing the production parser. No automatic fallback.
    """
    bindings=_bindings(bindings);root=Path(root)
    if not isinstance(expected_manifest_sha256,str) or not re.fullmatch('[0-9a-f]{64}',expected_manifest_sha256):
        raise ValueError('an externally pinned manifest SHA256 is required')
    mb=_read_snapshot(root/_MANIFEST_PATH, 2_000_000)
    if sha256(mb).hexdigest()!=expected_manifest_sha256:
        raise ValueError('manifest integrity mismatch')
    manifest=json.loads(mb,object_pairs_hook=_unique_object,parse_constant=_reject_constant)
    if not isinstance(manifest,dict):raise ValueError('manifest must be an object')
    expected={'schema':'release_target_vintage_collection.v1','integrity_profile':'release_target_artifact_sha256_bytes.v1',
              'source':'FRED/ALFRED','status':'ok','publication_status':'complete'}
    if any(manifest.get(k)!=v for k,v in expected.items()):raise ValueError('unqualified collection manifest')
    if type(manifest.get('source_output_type')) is not int or manifest['source_output_type']!=2 or manifest.get('dry_run') is not False:
        raise ValueError('manifest must describe a completed full-vintage publication')
    if _clock(manifest.get('completed_at')) < _clock(manifest.get('collected_at')):
        raise ValueError('collection completion precedes collection start')
    if not isinstance(manifest.get('series'),dict):raise ValueError('manifest series must be an object')
    snapshots={};entries={};missing=[]
    for binding in bindings:
        sid=binding.series_id
        if sid is None or sid in snapshots:continue
        entry=manifest['series'].get(sid)
        if entry is None:
            missing.append(sid);continue
        if not isinstance(entry,dict) or entry.get('status')!='written':raise ValueError('source entry not written')
        path=release_truth.default_vintage_path(root,sid)
        if entry.get('path')!=path.relative_to(root).as_posix():raise ValueError('noncanonical source path')
        count=entry.get('artifact_bytes');digest=entry.get('artifact_sha256')
        if type(count) is not int or not 0<count<=64_000_000:raise ValueError('invalid source byte count')
        if not isinstance(digest,str) or not re.fullmatch('[0-9a-f]{64}',digest):raise ValueError('invalid source digest')
        data=_read_snapshot(path,64_000_000)
        if len(data)!=count or sha256(data).hexdigest()!=digest:raise ValueError('source byte integrity mismatch')
        snapshots[sid]=data;entries[sid]=dict(entry)
    if not snapshots:raise ValueError('no requested full-vintage source was published')
    frames={}
    for sid, data in snapshots.items():
        try:
            raw=(decoder or pd.read_parquet)(BytesIO(data))
        except ImportError as exc:
            raise ValueError('Parquet parser dependency unavailable; install the repository-approved Arrow dependency; no fallback used') from exc
        entry=entries[sid]
        if not isinstance(raw,pd.DataFrame) or type(entry.get('rows')) is not int or len(raw)!=entry['rows']:
            raise ValueError('source row count does not match manifest')
        # Perform the canonical normalization exactly once in prepare_panel.
        for col,field in (('period','periods'),('realtime_start','release_dates')):
            if col not in raw or type(entry.get(field)) is not int or raw[col].nunique()!=entry[field]:
                raise ValueError(f'source {field} does not match manifest')
        if _day(raw['period'].min(),'period').isoformat()!=entry.get('period_min') or _day(raw['period'].max(),'period').isoformat()!=entry.get('period_max'):
            raise ValueError('source period bounds do not match manifest')
        frames[sid]=raw
    panel=prepare_panel(frames)
    receipt=panel.receipt
    receipt.update({'integrity_verified':True,'manifest_sha256':expected_manifest_sha256,
                    'source_basis':'manifest_bound_full_vintage_snapshot','source_files':entries,
                    'collected_at':manifest['collected_at'],'completed_at':manifest['completed_at'],
                    'production_parser_executed':decoder is None,'missing_source_series':missing})
    return replace(panel,_receipt_json=_json(receipt))


@dataclass(frozen=True)
class _ActiveSelection:
    series_id: str | None
    active: tuple[VintageRow, ...]
    known_periods: frozenset[date]
    reason: str | None


def _selection_state(panel: VintagePanel, binding: SeriesBinding,
                     cutoff: date) -> _ActiveSelection:
    """One selector owns both score inputs and evidence-change explanations.

    Incomplete active history remains inspectable even when it must not score.
    Expiration is used for selection, never as future knowledge in an identity.
    """
    if binding.series_id is None:
        return _ActiveSelection(None, (), frozenset(), 'canonical_full_vintage_binding_missing')
    known=[r for r in panel.rows if r.series==binding.series_id and r.period<=cutoff and r.start<=cutoff]
    if not known:
        return _ActiveSelection(binding.series_id, (), frozenset(), 'no_vintage_available_at_cutoff')
    latest_period=max(r.period for r in known)
    active={}
    for row in known:
        if row.end>=cutoff and (row.period not in active or row.start>active[row.period].start):
            active[row.period]=row
    selected=tuple(active[p] for p in sorted(active))
    periods=frozenset(r.period for r in known)
    if latest_period not in active:
        return _ActiveSelection(binding.series_id, selected, periods, 'latest_period_has_no_active_vintage')
    months=[r.period.year*12+r.period.month for r in selected]
    if any(b-a!=1 for a,b in zip(months,months[1:])):
        return _ActiveSelection(binding.series_id, selected, periods, 'incomplete_active_monthly_history')
    return _ActiveSelection(binding.series_id, selected, periods, None)


def _selection_projection(state: _ActiveSelection):
    if state.reason:
        return (), None, state.reason
    selected=state.active
    last=selected[-1];prior=selected[-2] if len(selected)>1 else None
    change=last.value-prior.value if prior is not None else None
    if change is not None and not isfinite(change):change=None
    projection={'series_id':last.series,'period':last.period.isoformat(),'vintage_start':last.start.isoformat(),
                'value':last.value,'active_periods':len(selected),
                'selected_hash':_content_hash([(r.period.isoformat(),r.start.isoformat(),r.value) for r in selected]),
                'movement':{'change':change,'direction':None if change is None else 'rising' if change>0 else 'falling' if change<0 else 'unchanged',
                            'basis':'last_two_monthly_levels_in_the_active_asof_vintage','is_forecast':False}}
    observations=tuple(Observation(r.period,r.value,r.start) for r in selected)
    return observations,projection,None


def _select(panel: VintagePanel, binding: SeriesBinding, cutoff: date):
    """Compatibility wrapper around the one active-vintage selection owner."""
    return _selection_projection(_selection_state(panel, binding, cutoff))


_CHANGE_KINDS = (
    'new_period', 'historical_period_added', 'restored_period',
    'initial_availability', 'revised_value', 'withdrawn_period',
    'vintage_refreshed', 'unchanged_period',
)


def _active_hash(state: _ActiveSelection) -> str:
    return _content_hash({
        'series_id': state.series_id,
        'active': [(r.period.isoformat(), r.start.isoformat(), r.value) for r in state.active],
    })


def _observation_reference(row: VintageRow | None):
    if row is None:
        return None
    return {'value': row.value, 'vintage_start': row.start.isoformat()}


def _change_event(kind: str, period: date, before: VintageRow | None,
                  after: VintageRow | None) -> dict:
    difference = None
    status = 'not_comparable'
    if before is not None and after is not None:
        difference = after.value - before.value
        status = 'available'
        if not isfinite(difference):
            difference = None
            status = 'overflow'
    return {
        'kind': kind, 'period': period.isoformat(),
        'before': _observation_reference(before), 'after': _observation_reference(after),
        'numeric_delta': difference, 'numeric_delta_status': status,
    }


def _series_change(before: _ActiveSelection | None, after: _ActiveSelection) -> dict:
    result = {
        'before_active_hash': _active_hash(before) if before is not None else None,
        'after_active_hash': _active_hash(after),
        'before_input_status': (before.reason or 'available') if before is not None else None,
        'after_input_status': after.reason or 'available',
        'input_status_semantics': 'active_vintage_selection_not_model_usability',
        'counts': None, 'events': [], 'refreshed_periods': [],
        'active_values_unchanged': None, 'source_identity_unchanged': None,
        'evidence_unchanged': None,
    }
    if before is None:
        return result
    counts = dict.fromkeys(_CHANGE_KINDS, 0)
    left = {r.period: r for r in before.active}
    right = {r.period: r for r in after.active}
    prior_maximum = max(before.known_periods) if before.known_periods else None
    for period in sorted(left.keys() | right.keys()):
        old, new = left.get(period), right.get(period)
        if old is None:
            if prior_maximum is None:
                kind = 'initial_availability'
            elif period in before.known_periods:
                kind = 'restored_period'
            elif period > prior_maximum:
                kind = 'new_period'
            else:
                kind = 'historical_period_added'
        elif new is None:
            kind = 'withdrawn_period'
        elif old.value != new.value:
            kind = 'revised_value'
        elif old.start != new.start:
            counts['vintage_refreshed'] += 1
            result['refreshed_periods'].append(period.isoformat())
            continue
        else:
            counts['unchanged_period'] += 1
            continue
        counts[kind] += 1
        result['events'].append(_change_event(kind, period, old, new))
    result['counts'] = counts
    before_values = [(row.period, row.value) for row in before.active]
    after_values = [(row.period, row.value) for row in after.active]
    result['active_values_unchanged'] = before_values == after_values
    result['source_identity_unchanged'] = (
        result['before_active_hash'] == result['after_active_hash']
    )
    result['evidence_unchanged'] = (
        result['source_identity_unchanged']
        and result['before_input_status'] == result['after_input_status']
    )
    return result


def _number_change(before: float, after: float) -> dict:
    return {'before': before, 'after': after, 'delta': after - before}


def _assessment_change(before: dict, after: dict) -> dict:
    raw = {}
    for key in ('upturn', 'downturn'):
        if before['score_status'] == after['score_status'] == 'available_research_only':
            raw[key] = {**_number_change(before['raw_scores'][key], after['raw_scores'][key]),
                        'status': 'available_research_only'}
        else:
            raw[key] = {'before': None, 'after': None, 'delta': None,
                        'status': 'not_comparable_unavailable_score'}
    return {
        'previous_phase': before['phase'], 'phase': after['phase'],
        'phase_changed': before['phase'] != after['phase'],
        'previous_score_status': before['score_status'], 'score_status': after['score_status'],
        'confidence': _number_change(before['confidence'], after['confidence']),
        'quality': {k: _number_change(before['quality'][k], after['quality'][k])
                    for k in ('coverage', 'recency', 'agreement', 'history')},
        'raw_scores': raw,
        'quality_flags_added': sorted(set(after['quality']['flags']) - set(before['quality']['flags'])),
        'quality_flags_removed': sorted(set(before['quality']['flags']) - set(after['quality']['flags'])),
        'previous_exclusions': dict(before['quality']['excluded']),
        'exclusions': dict(after['quality']['excluded']),
    }


def _evidence_change(before: dict[str, _ActiveSelection] | None,
                     after: dict[str, _ActiveSelection], previous_day: date | None,
                     day: date, previous_assessment: dict | None, assessment: dict) -> dict:
    changes = {key: _series_change(before[key] if before is not None else None, after[key])
               for key in sorted(after)}
    compared = before is not None
    return {
        'schema': 'macro.turnaround_evidence_change.v1',
        'status': 'compared' if compared else 'baseline_unavailable',
        'previous_as_of': previous_day.isoformat() if previous_day is not None else None,
        'elapsed_days': (day - previous_day).days if previous_day is not None else None,
        'count_unit': 'source_periods_not_independent_economic_confirmations',
        'summary_counts': {kind: sum(x['counts'][kind] for x in changes.values())
                           for kind in _CHANGE_KINDS} if compared else None,
        'series': changes,
        'active_values_unchanged': (
            all(x['active_values_unchanged'] for x in changes.values()) if compared else None
        ),
        'source_identity_unchanged': (
            all(x['source_identity_unchanged'] for x in changes.values()) if compared else None
        ),
        'evidence_unchanged': all(x['evidence_unchanged'] for x in changes.values()) if compared else None,
        'assessment_change': _assessment_change(previous_assessment, assessment) if compared else None,
        'causal_score_attribution_established': False, 'is_forecast': False,
        'interpretation': (
            'Active-observation changes coincide with these cutoffs; causal score or phase attribution is not established. '
            'Revised value means the selected value changed, not a verified official correction announcement. '
            'Initial or newly archived availability does not establish an original official publication date. '
            'Active-values unchanged ignores vintage identity; source-identity unchanged includes it.'
        ),
    }


def replay(panel: VintagePanel, bindings: Sequence[SeriesBinding], cutoffs: Sequence[str | date],
           *, domain: str, config: TurnaroundConfig | None=None) -> dict:
    bindings=_bindings(bindings)
    if domain not in ('growth','inflation'):raise ValueError('domain must be growth or inflation')
    if domain=='growth' and any(b.family=='inflation' for b in bindings):raise ValueError('inflation cannot stand in for growth evidence')
    if domain=='inflation' and any(b.family!='inflation' for b in bindings):raise ValueError('inflation replay accepts only its own family')
    if domain=='growth' and {b.family for b in bindings}!={'labor','activity','housing','consumer','credit'}:
        raise ValueError('growth replay must declare all five evidence families; absent sources require explicit missing bindings')
    if not isinstance(panel,VintagePanel):raise ValueError('validated panel required')
    dates=sorted(_coerce_date(x) for x in cutoffs)
    if not dates or len(dates)>1200 or len(set(dates))!=len(dates):raise ValueError('one to 1200 unique daily cutoffs required')
    engine=MacroTurnaroundEngine(config);specs=[b.spec() for b in bindings];rows=[];prior=None
    previous_states = None
    previous_day = None
    previous_assessment = None
    for day in dates:
        observations={};selected={};unavailable={}
        states = {}
        for binding in bindings:
            states[binding.key] = _selection_state(panel, binding, day)
            series,projection,reason=_selection_projection(states[binding.key])
            observations[binding.key]=series
            if projection is not None:selected[binding.key]=projection
            if reason:unavailable[binding.key]=reason
        assessment=engine.assess(observations,specs,day,previous_phase=prior)
        usable={signal.key for signal in assessment.signals}
        families={}
        for family in sorted({binding.family for binding in bindings}):
            keys=[binding.key for binding in bindings if binding.family==family]
            families[family]={'configured_keys':keys,'observed_keys':[k for k in keys if k in selected],
                              'usable_keys':[k for k in keys if k in usable],
                              'excluded_keys':[k for k in keys if k not in usable]}
        artifact = build_research_artifact(assessment)
        comparison = _evidence_change(previous_states, states, previous_day, day,
                                      previous_assessment, artifact)
        rows.append({'as_of':day.isoformat(),'selected':selected,'unavailable':unavailable,
                     'family_evidence':families,'assessment':artifact,'method_note':_METHOD_NOTE,
                     'evidence_change':comparison})
        prior=assessment.phase
        previous_states = states
        previous_day = day
        previous_assessment = artifact
    result={'schema':'macro.turnaround_vintage_replay.v1','capability_state':'BUILT_NOT_PROVEN','domain':domain,
            'asof_semantics':'end_of_source_vintage_date_not_intraday','authority':AuthorityBoundary().to_dict(),
            'profile':{'bindings':[asdict(b) for b in bindings],'config':engine.config.to_dict()},
            'source_receipt':panel.receipt,'rows':rows,'historical_system_availability_proven':False,
            'forecast_accuracy_established':False,'method_note':_METHOD_NOTE}
    result['replay_hash']=_content_hash(result)
    return result
