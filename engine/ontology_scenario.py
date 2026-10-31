"""F04-X2 pure, ephemeral WTI threshold composition over the existing TXI owner.

This module has no loader, transport, persistence or owner-state-machine call.
The assigning server must supply one immutable snapshot and its exact native
series/calendar bytes. SeriesBaseline is an in-memory input, not a new owner or
calendar registry. Future sessions MUST come from that series owner's calendar;
we never generate business days, interpolate observed history or infer vintages.

Only the frozen WTI root is supported. Terminal-only evaluates its declared
return leaf through TXI but abstains on the MA path. Complete explicit paths
call TXI.eval_node unchanged. Neither result arms an episode or confirms a hop.
Scalar-only rates artifacts abstain. The additive native metadata enables the
existing same-window beta display method through its separate read-only adapter.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
import hashlib
import inspect
import json
import math
import re
from typing import Any

import pandas as pd

from engine import transmission_chains as txi

METHOD = 'ontology_scenario.wti_threshold.v1'
_FIELDS = frozenset({'schema', 'node_ref', 'shock_definition', 'magnitude', 'unit',
                     'horizon', 'path_shape', 'origin_class', 'baseline_effective_at',
                     'baseline_knowledge_cutoff'})
_AUTHORITY = dict(can_rank=False, can_gate=False, can_size=False, can_trade=False)
_ZERO = dict(owner_writes=0, episode_writes=0, calibration_writes=0,
             portfolio_writes=0, alert_writes=0)


class ScenarioInputError(ValueError):
    """Invalid/ambiguous private assumption; safe for a closed transport refusal."""


@dataclass(frozen=True)
class SeriesBaseline:
    series: pd.Series
    future_sessions: tuple[str, ...]
    calendar_id: str
    calendar_version: str
    generation: str
    source_manifest_hash: str
    effective_at: str
    knowledge_cutoff: str
    # Opaque identity of an EXISTING display-permission receipt, supplied by
    # the admitted owner boundary. A display tier is not a licence grant.
    rights_ref: str | None


def _hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    return 'sha256:' + hashlib.sha256(raw).hexdigest()


def _stamp(value: Any) -> datetime:
    if not isinstance(value, str): raise ValueError('missing instant')
    stamp = datetime.fromisoformat(value.replace(' UTC', '+00:00').replace('Z', '+00:00'))
    if stamp.tzinfo is None: raise ValueError('timezone required')
    return stamp


def parse_assumption(raw: bytes) -> dict:
    """A future private POST must use duplicate-rejecting parsing, never a URL."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ScenarioInputError('DUPLICATE_PARAMETER')
            result[key] = value
        return result
    try:
        if not isinstance(raw, bytes) or len(raw) > 4096: raise ValueError('byte bound')
        value = json.loads(raw, object_pairs_hook=unique)
        return _normalize(value)
    except (TypeError, ValueError, UnicodeError, OverflowError) as exc:
        raise ScenarioInputError('INVALID_ASSUMPTION') from exc


def _normalize(value: dict) -> dict:
    try:
        if not isinstance(value, dict) or set(value) != _FIELDS: raise ValueError('fields')
        if value['schema'] != 'ontology_scenario_assumption.v1': raise ValueError('schema')
        magnitude = value['magnitude']
        if isinstance(magnitude, bool) or not isinstance(magnitude, (int, float)) or not math.isfinite(magnitude):
            raise ValueError('magnitude')
        wti = value['node_ref'] == 'yahoo:CL=F'
        rates = value['node_ref'] == 'transmission:real10y_chg63'
        if not (wti or rates): raise ValueError('node')
        if value['unit'] != ('percent' if wti else 'bp'): raise ValueError('unit')
        if value['shock_definition'] != ('terminal_change_over_horizon' if wti else 'absolute_change_bp_over_horizon'):
            raise ValueError('definition')
        if wti and magnitude <= -100: raise ValueError('nonpositive assumed price')
        if value['horizon'] not in {'60d', '63d', '3m'}: raise ValueError('horizon')
        if value['path_shape'] not in {'terminal_only', 'linear_sessions', 'step_at_start'}: raise ValueError('shape')
        if value['origin_class'] not in {'unspecified', 'supply', 'demand', 'residual'}: raise ValueError('origin')
        if not isinstance(value['baseline_effective_at'], str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value['baseline_effective_at']):
            raise ValueError('effective date')
        date.fromisoformat(value['baseline_effective_at'])
        cutoff = _stamp(value['baseline_knowledge_cutoff']).astimezone(UTC).isoformat()
        return {**value, 'magnitude': 0.0 if magnitude == 0 else float(magnitude),
                'baseline_knowledge_cutoff': cutoff}
    except (TypeError, ValueError, OverflowError) as exc:
        raise ScenarioInputError('INVALID_ASSUMPTION') from exc


class _MemorySeries:
    def __init__(self, series: pd.Series): self._series = series
    def series(self, name: str) -> pd.Series:
        if name != 'CL=F': raise txi._Unresolvable('scenario series not supplied')
        return self._series.copy(deep=True)


def _snapshot_identity(snapshot: dict) -> str:
    # Freshness ages are request-time diagnostics, not a new owner generation.
    source = snapshot.get('source', {})
    return _hash({'schema': snapshot.get('schema'), 'source': {
        key: source.get(key) for key in ['chain', 'rev', 'asof', 'built',
                                       'composer_method', 'source_manifest_hash']}})


def _unavailable(reason: str) -> dict:
    return dict(status='UNAVAILABLE', method_class='UNAVAILABLE', confirmed=None, reason=reason)


def _owner_tuple(baseline: SeriesBaseline) -> tuple[dict, pd.Series]:
    """Validate supplied native bytes, without reading/replacing anything current."""
    for value in [baseline.calendar_id, baseline.calendar_version, baseline.generation,
                  baseline.effective_at, baseline.knowledge_cutoff]:
        if not isinstance(value, str) or not value: raise ValueError('owner identity')
    if not isinstance(baseline.rights_ref, str) or not re.fullmatch(r'sha256:[0-9a-f]{64}', baseline.rights_ref):
        raise ValueError('existing display-permission receipt digest')
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', baseline.source_manifest_hash): raise ValueError('manifest')
    effective = date.fromisoformat(baseline.effective_at)
    cutoff = _stamp(baseline.knowledge_cutoff)
    if cutoff.date() < effective: raise ValueError('clock order')
    series = baseline.series.copy(deep=True)
    if not isinstance(series.index, pd.DatetimeIndex) or series.empty or len(series) > 100_000:
        raise ValueError('native series')
    if not series.index.is_unique or not series.index.is_monotonic_increasing: raise ValueError('session order')
    # Preserve owner session labels; do not localize/reindex or drop missing bars.
    dates = [stamp.date() for stamp in series.index]
    if len(set(dates)) != len(dates) or dates[-1] != effective or any(d > effective for d in dates):
        raise ValueError('effective date')
    values = [float(v) for v in series]
    if not all(math.isfinite(v) for v in values) or values[-1] <= 0: raise ValueError('native values')
    if not isinstance(baseline.future_sessions, tuple) or len(baseline.future_sessions) > 1260:
        raise ValueError('owner calendar')
    future = [date.fromisoformat(d) for d in baseline.future_sessions]
    if not future or future != sorted(set(future)) or future[0] <= effective: raise ValueError('future sessions')
    receipt = dict(generation=baseline.generation, source_manifest_hash=baseline.source_manifest_hash,
                   calendar_id=baseline.calendar_id, calendar_version=baseline.calendar_version,
                   effective_at=baseline.effective_at, knowledge_cutoff=cutoff.astimezone(UTC).isoformat(),
                   rights_ref=baseline.rights_ref, native_series_hash=_hash([[str(i), v] for i, v in zip(series.index, values)]),
                   future_sessions=list(baseline.future_sessions))
    return receipt, series


def _rates_result(assumption: dict, snapshot: dict, calibration: dict | None,
                  receipt: dict | None, evaluated_at: str) -> tuple[dict, dict | None, list]:
    from engine import rate_inflation_transmission as owner
    missing = _unavailable('NUMERIC_OWNER_METADATA_UNAVAILABLE')
    missing['missing_owner_contract'] = ['scenario_beta_estimation_span', 'scenario_beta_sample_counts',
                                         'owner_calendar_and_knowledge_cutoff']
    try:
        methods = [owner.SCENARIO_METHOD, 'ontology_scenario.rates_adapter.v1',
                   _hash(inspect.getsource(owner.evaluate_scenario_beta)), _hash(inspect.getsource(_rates_result))]
    except (OSError, TypeError):
        return _unavailable('NUMERIC_METHOD_VERSION_UNAVAILABLE'), None, [owner.SCENARIO_METHOD]
    if calibration is None: return missing, None, methods
    try:
        src = snapshot['source']
        if (snapshot['schema'] != 'ontology_explorer_snapshot.v1' or not receipt
                or receipt['path'] != 'data/transmission/calibration.json'
                or receipt not in src['reads'] or not re.fullmatch(r'[a-f0-9]{64}', receipt['sha256'])
                or assumption['baseline_effective_at'] != src['asof']
                or _stamp(assumption['baseline_knowledge_cutoff']) != _stamp(src['built'])
                or _stamp(evaluated_at) < _stamp(src['built'])):
            raise ValueError('selected native generation')
        result = owner.evaluate_scenario_beta(calibration, shock_bp=assumption['magnitude'],
            horizon=assumption['horizon'], path_shape=assumption['path_shape'],
            effective_at=src['asof'], knowledge_cutoff=src['built'])
        native = result['calibration']
        owner_receipt = {'generation': 'sha256:' + receipt['sha256'],
            'calibration_source': dict(receipt), 'source_manifest_hash': src['source_manifest_hash'],
            'effective_at': native['effective_at'], 'knowledge_cutoff': native['generated_at'],
            'selected_effective_at': src['asof'], 'selected_knowledge_cutoff': src['built'],
            'calendar_id': native['calendar']['owner_ref'], 'calendar_version': native['calendar']['sha256'],
            'publication_contract': native['publication_contract'], 'historical_vintage_claim': False}
        return result, owner_receipt, methods + [f'{k}:{v}' for k, v in sorted(native['method_versions'].items())]
    except owner.ScenarioMetadataUnavailable as exc:
        return _unavailable(str(exc)), None, methods
    except (KeyError, TypeError, ValueError, OverflowError):
        return missing, None, methods


def evaluate_scenario(assumption: dict, *, snapshot: dict, chain: dict,
                      baseline: SeriesBaseline | None, evaluated_at: str, created_at: str | None = None,
                      owner_refusal: dict | None = None, rates_calibration: dict | None = None,
                      calibration_receipt: dict | None = None) -> dict:
    """Return a private derived result; caller retains it only for this reading.

    The snapshot, chain and SeriesBaseline are trusted native-owner inputs, NEVER
    accepted from an HTTP assumption body. This interface alone does not establish
    their runtime installation, calendar admission or historical byte availability.
    Missing tuple members abstain; no cached/live fallback exists here.
    """
    normalized = _normalize(assumption)
    evaluated = _stamp(evaluated_at)
    created_at = created_at or evaluated_at
    if _stamp(created_at) > evaluated: raise ScenarioInputError('CREATED_AFTER_EVALUATION')
    method_available = True
    try:
        method_versions = [METHOD, 'pandas:' + pd.__version__, _hash([
            inspect.getsource(f) for f in [txi._series_metric, txi._apply_op, txi.eval_test, txi.eval_node]])]
    except (OSError, TypeError):
        method_versions = [METHOD, 'TXI_METHOD_BYTES_UNAVAILABLE']
        method_available = False
    snapshot_id = _snapshot_identity(snapshot)
    assumption_id = _hash(dict(assumption=normalized, snapshot_id=snapshot_id))
    root = _unavailable('EPHEMERAL_REPLAY_UNAVAILABLE')
    owner_receipt = None
    if normalized['node_ref'] == 'transmission:real10y_chg63':
        root, owner_receipt, rate_methods = _rates_result(normalized, snapshot, rates_calibration,
                                                         calibration_receipt, evaluated_at)
        method_versions = [METHOD, *rate_methods]
    else:
        try:
            if not method_available: raise ValueError('method bytes unavailable')
            if baseline is None: raise ValueError('native owner inputs unavailable')
            owner_receipt, history = _owner_tuple(baseline)
            src = snapshot['source']
            if snapshot.get('schema') != 'ontology_explorer_snapshot.v1': raise ValueError('snapshot schema')
            if (src['source_manifest_hash'] != baseline.source_manifest_hash
                    or src['asof'] != baseline.effective_at or _stamp(src['built']) != _stamp(baseline.knowledge_cutoff)
                    or normalized['baseline_effective_at'] != baseline.effective_at
                    or _stamp(normalized['baseline_knowledge_cutoff']) != _stamp(baseline.knowledge_cutoff)
                    or _stamp(evaluated_at) < _stamp(baseline.knowledge_cutoff)):
                raise ValueError('snapshot/owner clock binding')
            if src['chain'] != chain['chain'] or src['rev'] != chain['rev']: raise ValueError('chain version')
            if normalized['horizon'] != '60d':
                root = _unavailable('HORIZON_INCOMPATIBLE')
            elif len(baseline.future_sessions) < 60:
                root = _unavailable('OWNER_CALENDAR_TOO_SHORT')
            else:
                node = chain['nodes']['oil_shock']
                # Bind this explicit adapter to the frozen owner root, not a generic
                # copied grammar. A changed owner form needs an explicit qualification.
                tests = node['test']['all']
                if (chain['chain'] != 'oil_inflation_duration_derate' or node['src'] != 'yahoo'
                        or len(tests) != 2 or tests[0] != {'series':'CL=F','metric':'ret','window':60,'op':'gt','value':25}
                        or tests[1] != {'series':'CL=F','metric':'ma_slope','window':50,'lookback':5,'op':'gt','value':0}):
                    raise ValueError('unqualified owner definition')
                end = float(history.iloc[-1]) * (1 + normalized['magnitude'] / 100)
                if not math.isfinite(end) or end <= 0: raise ValueError('assumed level')
                shape = normalized['path_shape']
                if shape == 'terminal_only':
                    # Missing intermediate points remain missing. Only the endpoint
                    # return leaf is evaluated, never slope/volatility/persistence.
                    values = [float('nan')] * 59 + [end]
                elif shape == 'step_at_start': values = [end] * 60
                else: values = [float(history.iloc[-1]) + (end - float(history.iloc[-1])) * i / 60 for i in range(1, 61)]
                future = pd.Series(values, index=pd.DatetimeIndex(baseline.future_sessions[:60]))
                # Preserve the baseline's timezone rather than mixing native indexes.
                if history.index.tz is not None: future.index = future.index.tz_localize(history.index.tz)
                adapters = {'yahoo': _MemorySeries(pd.concat([history, future]))}
                if shape == 'terminal_only':
                    passed, receipts = txi.eval_test(tests[0], adapters, 'yahoo')
                    root = dict(status='PARTIAL_UNKNOWN' if passed else 'SCENARIO_NOT_ARMED',
                                method_class='THRESHOLD_STATE_ONLY', confirmed=None,
                                path_condition='UNDETERMINED', threshold_evaluation=dict(confirmed=passed, receipts=receipts))
                else:
                    native = txi.eval_node(chain, 'oil_shock', adapters)
                    if not native['resolved']: native = {**native, 'confirmed': None}
                    root = dict(status=('ROOT_THRESHOLD_MET' if native['confirmed'] else 'SCENARIO_NOT_ARMED')
                                if native['resolved'] else 'UNAVAILABLE', method_class='THRESHOLD_STATE_ONLY', **native)
                root['input_status'] = dict(history='OBSERVED_BASELINE', future='ASSUMED', calendar='OWNER_SUPPLIED')
                root['horizon'] = dict(label='60d', unit='owner_sessions', count=60)
        except (KeyError, TypeError, ValueError, AttributeError, IndexError, OverflowError, txi.ChainSchemaError):
            root = _unavailable('EPHEMERAL_REPLAY_UNAVAILABLE')
            if baseline is None and owner_refusal:
                root.update({key:owner_refusal[key] for key in ['reason','missing_owner_inputs','adapter_method']
                             if key in owner_refusal})
    hops = [dict(from_node=h.get('from'), to_node=h.get('to'), method_class='HYPOTHESIS_MECHANISM',
                 value=None, reason='DOWNSTREAM_NOT_ASSUMED') for h in chain.get('hops', [])]
    logical = dict(assumption_id=assumption_id, snapshot_id=snapshot_id, chain_hash=_hash(chain),
                   owner=owner_receipt, method_versions=method_versions, root=root, hops=hops)
    return dict(schema='ontology_scenario_eval.v1', scenario_eval_id=_hash(logical),
                assumption={**normalized, 'assumption_id': assumption_id, 'snapshot_id': snapshot_id,
                            'created_at': created_at},
                assumption_id=assumption_id, snapshot_id=snapshot_id, evaluated_at=evaluated_at,
                method_versions=method_versions, owner_receipt=owner_receipt, root_evaluation=root,
                hop_evaluations=hops, combined_estimate=None,
                no_combined_estimate_reason='NO_ACCEPTED_JOINT_RESPONSE_OWNER',
                degradations=[] if root['status'] in {'ROOT_THRESHOLD_MET', 'NUMERIC_ILLUSTRATION'} else [root.get('reason', root['status'])],
                authority=dict(_AUTHORITY), side_effect_receipt=dict(_ZERO))
