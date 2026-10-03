"""Bounded evidence qualification for the EXISTING mechanism read tool.

Consumes the incumbent artifact, never runs its producer or changes market truth.
Dates describe owner snapshots; association-table directions are not observations
of realized transmission. Neither coverage nor link counts are causal confidence.

One clock rule (R4 — applies equally to compiler and reader):
  - value missing / None / "" / unparseable string / ANY non-string
    (e.g. the int 20261002) / NAIVE datetime string → `unknown_date`.
  - timezone-aware datetime later than now → `future_dated`.
  - date-only D with D > (now_utc + 14h).date() → `future_dated`
    (Kiritimati is the furthest forward inhabited zone).
  - calendar age >= _STALE_DAYS (5) → `stale`.
  - otherwise → `available`.

2026-10-03 clock and aggregate repair (R3/R5/R6 + reader-side E1–E6):
  - R3 (defence in depth): the reader independently rejects future-dated and
    unknown-dated node clocks.
  - R5 (legacy artifacts): only artifacts carrying `clock_basis=source_clock_v1`
    may have their node dates counted as verified source observation dates.
    Unmarked (legacy) artifacts → node dates are disclosed as
    `time_unverified_observation_links`; they never increment
    `reported_observation_links`.
  - R6 (aggregates earned): pathway-level coverage / coherence / direction
    text are passed through ONLY when ALL hold:
        (i)   the artifact carries the clock_basis marker;
        (ii)  the pathway's own source clock is `available`;
        (iii) at least one element qualifies — a well-formed edge with both
              endpoints present and an `available` source clock, OR for a
              pathway type that legitimately has zero edges (factor rotation),
              the pathway's own `available` clock plus a trigger node with
              `available` clock;
        (iv)  no declared edge is malformed.
      Otherwise coverage → None, coherence → 'unknown', direction_en/zh → None,
      and ONE bounded reason from the closed set
      {legacy_time_unverified, no_qualifying_evidence, malformed_edges,
       pathway_clock_stale, pathway_clock_future, pathway_clock_unknown}.
  - R7 (duplicates are not separate observations): `reported_observation_links`
    counts DISTINCT (src_node, dst_node, evidence_refs) links; surplus copies
    go to the additive `duplicate_observation_links` count.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from engine.neuralweb.mechanism_pathways import (
    AUTHORITY_BLOCK, CLOCK_BASIS_MARKER, SCHEMA, _STALE_DAYS,
)

SOURCE_PATH = 'data/neuralweb/mechanism_pathways.json'
MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_PATHWAYS = 3
MAX_NODES = 20
MAX_EDGES = 24
_BAD_CLOCKS = frozenset({'future_dated', 'unknown_date', 'unavailable'})
_STATUSES = frozenset({'measured', 'theory_prior', 'context_only', 'conflicted', 'missing', 'stale'})
_SIGNS = frozenset({'positive', 'negative', 'neutral'})

# Per R4 boundary rule: a date-only source clock D is "future" only when
# D > (now_utc + 14h).date() — the latest calendar date anywhere on Earth.
# Kiritimati (UTC+14) is the furthest forward inhabited zone.
_LATEST_EARTH_DATE_OFFSET_HOURS = 14


def _latest_earth_date(now: datetime) -> date:
    return (now + timedelta(hours=_LATEST_EARTH_DATE_OFFSET_HOURS)).date()


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
            # R4: date-only future boundary uses the latest Earth date.
            latest_earth = _latest_earth_date(now)
            future = day > latest_earth
            age = (now.date() - day).days
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
            'reported_observation_links', 'duplicate_observation_links',
            'contextual_transmission_links', 'theory_links', 'conflicted_links',
            'unavailable_links', 'stale_links', 'time_unverified_observation_links')},
        'note': ('Owner-reported observations, historical associations and theory are distinct. '
                 'Coverage is readability, not probability; links are not independent votes. '
                 'A snapshot date is not the time a market mechanism began. '
                 'Legacy artifacts without a clock_basis marker cannot launder '
                 'build-stamped node dates as source observations.'),
    }


def _node(raw: dict, now: datetime, *, is_repaired: bool = True) -> dict:
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
    # R5 — surface a per-node time-unverified disclosure when the artifact
    # carries no clock_basis marker. The node still exposes its values, but
    # the leg's own date is not yet a verified source observation date.
    if not is_repaired and out['as_of'] is not None:
        out['gaps'].append('legacy_unmarked_owner_clock')
    return out


def project_evidence(payload: Any, *, now: datetime) -> dict:
    """Pure bounded projection; never substitutes wrapper clocks or new causes.

    R5 (2026-10-03): the artifact must carry a `clock_basis` marker for any
    per-node date to count as a verified source observation. Legacy artifacts
    (no marker) → those links are disclosed as
    `time_unverified_observation_links`, never as `reported_observation_links`.

    R6: pathway-level coverage / coherence are derived from surviving evidence
    elements (zero-edge factor pathways use their own source clock).
    """
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
    # R5: clock_basis marker required for any per-node observation claim.
    # The marker is the source artifact's own declaration; absent → legacy.
    is_repaired = payload.get('clock_basis') == CLOCK_BASIS_MARKER
    if not is_repaired:
        out['gaps'] = out.get('gaps', []) + ['legacy_artifact_unverified_node_clocks']
    out['omitted_pathways'] = max(0, len(raw_paths) - MAX_PATHWAYS)
    summary = out['evidence_summary']
    for raw in raw_paths[:MAX_PATHWAYS]:
        if not isinstance(raw, dict):
            out['gaps'].append('invalid_pathway')
            continue
        p = {k: _token(raw.get(k)) for k in ('family', 'driver', 'pathway_role', 'coverage_basis')}
        # Optional producer disclosure; keep legacy coverage_basis semantics.
        if (reason := _token(raw.get('coverage_withheld_reason'))) is not None:
            p['coverage_withheld_reason'] = reason
        p.update(_stamp(raw.get('as_of'), now))
        p.update(nodes=[], edges=[], gaps=[], confidence_ceiling='context_only')
        p['coherence'] = raw.get('coherence') if raw.get('coherence') in ('supported', 'partial', 'conflicted') else 'unknown'
        p['coherence_semantics'] = 'owner_categorical_assessment_not_causal_confidence'
        # R7: surface dependent-leg / single-source disclosure
        ds = _number(raw.get('distinct_sources'))
        if ds is not None:
            p['distinct_sources'] = int(ds)
        p['independent_confirmations_disallowed'] = bool(raw.get('independent_confirmations_disallowed'))
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
        p['nodes'] = [_node(n, now, is_repaired=is_repaired) for n in nodes[:MAX_NODES] if isinstance(n, dict)]
        indexed = {n['node_id']: n for n in p['nodes'] if n['node_id'] and ids[n['node_id']] == 1}
        # R6 / E1 qualification is computed AFTER the edge loop (post-loop
        # qualification) — the loop records what each edge looks like, then
        # we decide whether the producer's positive aggregate (coverage /
        # coherence / direction_en / direction_zh) survives.
        malformed_edges = False
        seen_observation_links: set[tuple] = set()
        for raw_edge in edges[:MAX_EDGES]:
            if not isinstance(raw_edge, dict):
                p['gaps'].append('invalid_edge')
                malformed_edges = True
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
            # R5 (defence in depth): legacy artifacts may not count any per-node
            # date as a verified source observation. Their measured "observation"
            # edges are reclassified as time-unverified disclosures — the leg
            # nodes still expose their values, but the link is not a vote for
            # coverage / observation counting. The same applies if any leg's
            # own date is in a bad state (defence in depth: even when the
            # artifact has a clock_basis marker, future/unknown leg clocks are
            # not observations).
            leg_endpoints_ok = all(
                n is not None and n.get('reading_status') not in _BAD_CLOCKS
                for n in endpoints
            )
            if category == 'reported_observation_links' and not is_repaired:
                # Legacy artifacts may not count any per-node date as a verified
                # source observation. Measured "observation" edges are reclassified
                # as time-unverified disclosures — the leg nodes still expose
                # their values, but the link is not a vote for coverage /
                # observation counting. The marker-present-but-bad-clock case
                # cannot reach category='reported_observation_links' here:
                # earlier gates (line ~280) already demote a bad-clock edge to
                # status='missing', which routes category to 'unavailable_links'.
                category = 'time_unverified_observation_links'
            # R7 / E2: duplicates are not separate observations. Distinct
            # observation links are keyed by (src_node, dst_node, evidence_refs);
            # surplus copies route to the additive `duplicate_observation_links`.
            if category == 'reported_observation_links':
                link_id = (e['src_node'], e['dst_node'], tuple(e['evidence_refs']))
                if link_id in seen_observation_links:
                    category = 'duplicate_observation_links'
                else:
                    seen_observation_links.add(link_id)
            summary[category] += 1
            p['edges'].append(e)
        # E1 post-loop qualification: a pathway's positive aggregate
        # (coverage, coherence, direction_en/zh) is passed through ONLY when
        # ALL hold — (i) the artifact carries the clock_basis marker;
        # (ii) the pathway's own source clock is `available`;
        # (iii) at least one element qualifies — a well-formed edge with both
        #       endpoints present and an `available` source clock, OR for a
        #       pathway type that legitimately has zero edges (factor rotation),
        #       the pathway's own `available` clock plus a trigger node with
        #       `available` clock; (iv) no declared edge was malformed.
        # Otherwise coverage → None, coherence → 'unknown', direction_en/zh →
        # None, and ONE bounded reason from the closed set.
        _PATHWAY_CLOCK_REASONS = {
            'stale': 'pathway_clock_stale',
            'future_dated': 'pathway_clock_future',
            'unknown_date': 'pathway_clock_unknown',
        }
        withhold_reason = None
        if not is_repaired:
            withhold_reason = 'legacy_time_unverified'
        elif p['reading_status'] in _PATHWAY_CLOCK_REASONS:
            withhold_reason = _PATHWAY_CLOCK_REASONS[p['reading_status']]
        elif malformed_edges:
            withhold_reason = 'malformed_edges'
        elif not edges:
            # Zero-edge pathway: qualifies only with an available trigger node.
            has_trigger = any(
                n.get('pathway_role') == 'trigger'
                and n.get('reading_status') == 'available'
                for n in p['nodes']
            )
            if not has_trigger:
                withhold_reason = 'no_qualifying_evidence'
        else:
            qualified_edge = any(
                e.get('status') == 'measured'
                for e in p['edges']
            )
            if not qualified_edge:
                withhold_reason = 'no_qualifying_evidence'
        if withhold_reason is not None:
            p['coverage_score'] = None
            p['coherence'] = 'unknown'
            p['direction_en'] = None
            p['direction_zh'] = None
            if withhold_reason not in p['gaps']:
                p['gaps'].append(withhold_reason)
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
