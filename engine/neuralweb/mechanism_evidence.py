"""Bounded evidence qualification for the EXISTING mechanism read tool.

Consumes the incumbent artifact, never runs its producer or changes market truth.
Dates describe owner snapshots; association-table directions are not observations
of realized transmission. Neither coverage nor link counts are causal confidence.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from engine.neuralweb.mechanism_pathways import AUTHORITY_BLOCK, SCHEMA, _STALE_DAYS

SOURCE_PATH = 'data/neuralweb/mechanism_pathways.json'
MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_PATHWAYS = 3
MAX_NODES = 20
MAX_EDGES = 24
_BAD_CLOCKS = frozenset({'future_dated', 'unknown_date', 'unavailable'})
_STATUSES = frozenset({'measured', 'theory_prior', 'context_only', 'conflicted', 'missing', 'stale'})
_SIGNS = frozenset({'positive', 'negative', 'neutral'})


def _obj(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _text(value: Any, limit: int = 180) -> str | None:
    if not isinstance(value, str):
        return None
    # Source prose is bounded evidence, never a tool instruction or privileged field.
    return re.sub(r'[\x00-\x1f\x7f\u200b-\u200f\u202a-\u202e\u2066-\u2069]', ' ', value).strip()[:limit] or None


def _token(value: Any) -> str | None:
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.:/#\[\]-]{0,159}', value):
        return None
    return value


def _number(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        return value if math.isfinite(float(value)) else None
    except (OverflowError, ValueError):
        return None


def _refs(value: Any) -> list[str]:
    return [x for v in value[:8] if (x := _token(v))] if isinstance(value, list) else []


def _stamp(value: Any, now: datetime) -> dict:
    out = {'as_of': None, 'reading_status': 'unknown_date', 'precision': None,
           'age_calendar_days': None, 'clock_semantics': 'owner_snapshot_not_release_time',
           'currentness_certified': False}
    if not isinstance(value, str):
        return out
    try:
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            day = date.fromisoformat(value)
            age = (now.date() - day).days
            future = day > now.date()
            stamp, precision = value, 'date'
        else:
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                return out
            dt = dt.astimezone(timezone.utc)
            age = (now.date() - dt.date()).days
            future = dt > now
            stamp, precision = dt.isoformat(), 'datetime'
        out.update(as_of=stamp, precision=precision, age_calendar_days=age,
                   reading_status='future_dated' if future else 'stale' if age >= _STALE_DAYS else 'available')
    except (TypeError, ValueError, OverflowError):
        pass
    return out


def _base(now: datetime) -> dict:
    return {
        'schema': SCHEMA, 'is_context_only': True, 'display_only': True,
        'not_a_signal': True, 'authority': copy.deepcopy(AUTHORITY_BLOCK),
        'observed_at': now.isoformat(), 'reading_status': 'unavailable',
        'pathways': [], 'no_pathway': None, 'gaps': [],
        'historical_replay_eligible': False, 'causal_identification_established': False,
        'evidence_summary': {key: 0 for key in (
            'reported_observation_links', 'contextual_transmission_links',
            'theory_links', 'conflicted_links', 'unavailable_links', 'stale_links')},
        'note': ('Owner-reported observations, historical associations and theory are distinct. '
                 'Coverage is readability, not probability; links are not independent votes. '
                 'A snapshot date is not the time a market mechanism began.'),
    }


def _node(raw: dict, now: datetime) -> dict:
    out = {k: _token(raw.get(k)) for k in (
        'node_id', 'domain', 'source_artifact', 'source_tier', 'lag_class', 'pathway_role')}
    out.update(_stamp(raw.get('as_of'), now))
    out['entity'] = _text(raw.get('entity'), 100)
    out['evidence_refs'] = _refs(raw.get('evidence_refs'))
    out['gaps'] = []
    out['observation'] = {lang: _text(_obj(raw.get('observation')).get(lang), 280) for lang in ('en', 'zh')}
    out['direction'] = raw.get('direction') if raw.get('direction') in ('positive', 'negative', 'neutral', 1, -1, 0) and not isinstance(raw.get('direction'), bool) else None
    for key in ('value', 'z_or_percentile'):
        out[key] = _number(raw.get(key))
        if raw.get(key) is not None and out[key] is None:
            out['gaps'].append('invalid_numeric_value')
    if out['reading_status'] in _BAD_CLOCKS:
        out.update(value=None, z_or_percentile=None, direction=None, observation={})
        out['gaps'].append(out['reading_status'])
    return out


def project_evidence(payload: Any, *, now: datetime) -> dict:
    """Pure bounded projection; never substitutes wrapper clocks or new causes."""
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError('timezone-aware observation time required')
    now = now.astimezone(timezone.utc)
    out = _base(now)
    if not isinstance(payload, dict) or payload.get('schema') != SCHEMA:
        out['gaps'] = ['invalid_artifact_schema']
        return out
    out.update(_stamp(payload.get('as_of'), now))
    if out['reading_status'] in _BAD_CLOCKS:
        out['gaps'] = [out['reading_status']]
        return out
    raw_paths = payload.get('pathways')
    if not isinstance(raw_paths, list):
        out['gaps'] = ['pathways_unavailable']
        out['reading_status'] = 'unavailable'
        return out
    out['omitted_pathways'] = max(0, len(raw_paths) - MAX_PATHWAYS)
    summary = out['evidence_summary']
    for raw in raw_paths[:MAX_PATHWAYS]:
        if not isinstance(raw, dict):
            out['gaps'].append('invalid_pathway')
            continue
        p = {k: _token(raw.get(k)) for k in ('family', 'driver', 'pathway_role', 'coverage_basis')}
        p.update(_stamp(raw.get('as_of'), now))
        p.update(nodes=[], edges=[], gaps=[], confidence_ceiling='context_only')
        p['coherence'] = raw.get('coherence') if raw.get('coherence') in ('supported', 'partial', 'conflicted') else 'unknown'
        p['coherence_semantics'] = 'owner_categorical_assessment_not_causal_confidence'
        if p['reading_status'] in _BAD_CLOCKS:
            p['coherence'], p['coverage_score'] = 'unknown', None
            p['gaps'] = [p['reading_status']]
            out['pathways'].append(p)
            continue
        p['direction_en'], p['direction_zh'] = _text(raw.get('direction_en')), _text(raw.get('direction_zh'))
        coverage = _number(raw.get('coverage_score'))
        p['coverage_score'] = coverage if coverage is not None and 0 <= coverage <= 1 else None
        p['coverage_semantics'] = 'owner_readability_not_probability'
        p['stale_legs'] = [_text(x, 80) for x in raw.get('stale_legs', [])[:MAX_NODES]] if isinstance(raw.get('stale_legs'), list) else []
        nodes, edges = raw.get('nodes'), raw.get('edges')
        if not isinstance(nodes, list) or not isinstance(edges, list):
            p['coherence'], p['coverage_score'] = 'unknown', None
            p['gaps'].append('graph_unavailable')
            out['pathways'].append(p)
            continue
        # Count identities before truncation: a duplicate just past the cap still conflicts.
        ids = Counter(_token(n.get('node_id')) for n in nodes if isinstance(n, dict))
        if any(k and count > 1 for k, count in ids.items()):
            p['gaps'].append('ambiguous_node_identity')
        p['omitted_nodes'], p['omitted_edges'] = max(0, len(nodes) - MAX_NODES), max(0, len(edges) - MAX_EDGES)
        p['nodes'] = [_node(n, now) for n in nodes[:MAX_NODES] if isinstance(n, dict)]
        indexed = {n['node_id']: n for n in p['nodes'] if n['node_id'] and ids[n['node_id']] == 1}
        for raw_edge in edges[:MAX_EDGES]:
            if not isinstance(raw_edge, dict):
                p['gaps'].append('invalid_edge')
                continue
            e = {k: _token(raw_edge.get(k)) for k in ('src_node', 'dst_node', 'mechanism_type', 'expected_lag')}
            e['evidence_refs'] = _refs(raw_edge.get('evidence_refs'))
            e['status'] = raw_edge.get('status') if isinstance(raw_edge.get('status'), str) and raw_edge['status'] in _STATUSES else 'missing'
            for key in ('expected_sign', 'observed_sign'):
                value = raw_edge.get(key)
                e[key] = value if isinstance(value, str) and value in _SIGNS else None
            is_transmission = e['mechanism_type'] == 'transmission_channel'
            if is_transmission:
                e['prior_sign'] = e['expected_sign'] or e['observed_sign']
                e['observed_sign'] = None
                e['evidence_basis'] = 'historical_association_not_realized_transmission'
                if e['status'] == 'measured':
                    e['status'] = 'context_only'
            else:
                e['evidence_basis'] = 'owner_reported_observation_not_causality' if e['status'] == 'measured' else 'owner_hypothesis'
            endpoints = [indexed.get(e['src_node']), indexed.get(e['dst_node'])]
            if any(n is None or n['reading_status'] in _BAD_CLOCKS or 'invalid_numeric_value' in n['gaps'] for n in endpoints):
                e['status'], e['observed_sign'] = 'missing', None
            elif (out['reading_status'] == 'stale' or p['reading_status'] == 'stale'
                  or any(n['reading_status'] == 'stale' or n['entity'] in p['stale_legs'] for n in endpoints)):
                e['status'], e['observed_sign'] = 'stale', None
            elif e['status'] == 'measured':
                if e['mechanism_type'] != 'evidence_leg':
                    e['status'], e['observed_sign'] = 'context_only', None
                    e['evidence_basis'] = 'owner_hypothesis'
                elif (not endpoints[1]['source_artifact']
                      or all(endpoints[1][k] is None for k in ('value', 'z_or_percentile'))):
                    e['status'], e['observed_sign'] = 'missing', None
            if e['status'] == 'missing':
                # Required-leg expected signs were copied from observations by
                # the legacy producer. Withholding only observed_sign leaks the
                # same unavailable evidence via its other field name.
                e['observed_sign'], e['expected_sign'] = None, None
                if 'prior_sign' in e:
                    e['prior_sign'] = None
                e['evidence_basis'] = 'unavailable_source_evidence'
            if e['status'] in ('missing', 'stale'):
                p['coherence'], p['coverage_score'] = 'unknown', None
            category = {'conflicted': 'conflicted_links', 'missing': 'unavailable_links',
                        'stale': 'stale_links', 'theory_prior': 'theory_links'}.get(e['status'])
            if category is None:
                category = 'contextual_transmission_links' if is_transmission else 'reported_observation_links' if e['status'] == 'measured' else 'theory_links'
            summary[category] += 1
            p['edges'].append(e)
        out['pathways'].append(p)
    no_path = _obj(payload.get('no_pathway'))
    if no_path:
        out['no_pathway'] = {'reason': _token(no_path.get('reason')) or 'unknown', 'printed': True}
    return out


def _unique(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON member')
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError('non-finite JSON constant')


def read_evidence(root: Path, *, now: datetime | None = None) -> dict:
    """One bounded read of the incumbent artifact; no producer or provider call."""
    observed = now or datetime.now(timezone.utc)
    if not isinstance(observed, datetime) or observed.tzinfo is None:
        raise ValueError('timezone-aware observation time required')
    observed = observed.astimezone(timezone.utc)
    try:
        with (Path(root) / SOURCE_PATH).open('rb') as stream:
            data = stream.read(MAX_SOURCE_BYTES + 1)
        if len(data) > MAX_SOURCE_BYTES:
            out = _base(observed); out['gaps'] = ['source_too_large']; return out
        raw = json.loads(data, object_pairs_hook=_unique, parse_constant=_reject_constant)
        out = project_evidence(raw, now=observed)
        out['source'] = {'artifact': SOURCE_PATH, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
        return out
    except (OSError, ValueError, TypeError, OverflowError, UnicodeError, RecursionError):
        out = _base(observed); out['gaps'] = ['source_missing_or_unreadable']; return out
