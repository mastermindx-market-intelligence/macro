"""Granular, read-only context for the existing Live Market State Packet.

This is a projection, not a regime/shock classifier or a publication owner. The
pure composer preserves selected native facts, their dimensions and clocks. It
has no network, persistence, fitted weights, forecasts, rankings or risk effects.
The reader opens only fixed product artifacts. Snapshot dates do not certify
underlying observation time or historical point-in-time availability.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

SOURCE_PATHS = {
    'regime': 'data/regime/latest.json',
    'transmission': 'data/transmission/latest.json',
    'participation': 'site/basketdata/breadth_split.json',
    'options': 'site/basketdata/vol_weather.json',
    'dispersion': 'data/dispersion/regime.json',
    'world_state': 'data/neuralweb/world_state.json',
    'leadership': 'data/leadership_crack/latest.json',
}
MAX_SOURCE_BYTES = 2 * 1024 * 1024
SCHEMA = 'market_packet.regime_context.v1'
QUAD_NAMES = {'Q1': 'Goldilocks', 'Q2': 'Reflation',
              'Q3': 'Stagflation', 'Q4': 'Growth-scare'}
# A current observation adapter, never a new membership registry. The full
# published theme universe is kept; these are explicitly named example cohorts
# in the compact US briefing, not the output of a new ranking.
BRIEF_THEME_IDS = ('ai_semiconductors', 'memory_storage', 'data_center_power')


def _dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _token(value: Any, *, maximum: int = 72) -> str | None:
    """Only bounded data tokens, never arbitrary upstream prose/instructions."""
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_ .:/+%()-]{0,71}', value):
        return None
    return value[:maximum]


def _choice(value: Any, allowed: tuple[str, ...]) -> str | None:
    return value if isinstance(value, str) and value in allowed else None


def _quad(value: Any) -> str | None:
    return value if isinstance(value, str) and value in QUAD_NAMES else None


def _num(value: Any, field: str, issues: list[str], *, low=None, high=None) -> float | None:
    if value is None:
        return None
    try:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError('not a numeric observation')
        out = float(value)
        if not math.isfinite(out) or (low is not None and out < low) or (high is not None and out > high):
            raise ValueError('not finite or outside semantic range')
        return out
    except (ValueError, TypeError, OverflowError):
        issues.append('invalid_field:' + field)
        return None


def _count(value: Any, field: str, issues: list[str]) -> int | None:
    n = _num(value, field, issues, low=0)
    if n is None:
        return None
    if not n.is_integer():
        issues.append('invalid_field:' + field)
        return None
    return int(n)


def _has_value(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_has_value(v) for v in value.values())
    if isinstance(value, list):
        return any(_has_value(v) for v in value)
    return not isinstance(value, bool) and value is not None and value != ''


def _date_info(value: Any, now: datetime) -> dict:
    out = {'as_of': None, 'precision': None, 'age_calendar_days': None,
           'future_dated': False, 'known_at': None, 'available_at': None}
    if not isinstance(value, str):
        return out
    try:
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            day = date.fromisoformat(value)
            out.update(as_of=value, precision='date',
                       age_calendar_days=(now.date() - day).days,
                       future_dated=day > now.date())
        else:
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                return out  # a timezone-less clock cannot certify an instant
            dt = dt.astimezone(timezone.utc)
            out.update(as_of=dt.isoformat(), precision='datetime',
                       age_calendar_days=(now.date() - dt.date()).days,
                       future_dated=dt > now)
    except (ValueError, TypeError, OverflowError):
        pass
    return out


def compose_context(sources: dict, *, now: datetime,
                    source_metadata: dict | None = None,
                    expected_session: date | None = None) -> dict:
    """Pure projection of separately captured owner objects, never a PIT replay.

    `now` is an explicit observation cutoff, not a historical issuance claim.
    Source metadata may carry actual read hashes;
    neither a hash nor a wrapper clock certifies the input's underlying vintage.
    """
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError('now must be an explicit timezone-aware datetime')
    now = now.astimezone(timezone.utc)
    sources, source_metadata = _dict(sources), _dict(source_metadata)
    dims: dict[str, dict] = {}

    def emit(name, key, pointer, raw, stamp, values, unit, *, issues=None,
             clock='owner_snapshot_date', stale=False, scope='US', notes=()):
        issues = list(issues or [])
        source = {'artifact': SOURCE_PATHS[key], 'pointer': pointer,
                  'sha256': _dict(source_metadata.get(key)).get('sha256'),
                  'clock_semantics': clock, **_date_info(stamp, now)}
        source['expected_us_session'] = expected_session.isoformat() if expected_session else None
        source['session_relation'] = None
        if source['as_of'] and expected_session:
            day = date.fromisoformat(source['as_of'][:10])
            source['session_relation'] = ('same_completed_session' if day == expected_session
                else 'older_than_completed_session' if day < expected_session else 'after_completed_session')
        if isinstance(raw, dict):
            available = _date_info(raw.get('available_at'), now)
            source['available_at'] = available['as_of']
            if available['future_dated']:
                source['future_dated'] = True
                issues.append('availability_after_observation_cutoff')
        if not raw or not _has_value(values):
            status = 'missing'; values = {}
        elif source['as_of'] is None:
            status = 'unknown_date'; values = {}
        elif source['future_dated']:
            status = 'future_dated'; values = {}
        elif stale:
            status = 'stale'
        else:
            status = 'partial' if issues else 'available'
        # A source saying "fresh" describes its last build, not this read.
        # Preserve observation age and do not manufacture an intraday freshness
        # certification from date-only/uncertified source clocks.
        dims[name] = {
            'status': status, 'scope': scope, 'source': source, 'unit': unit,
            'values': values, 'issues': issues, 'notes': list(notes),
            'currentness_certified': False,
        }

    regime = _dict(sources.get('regime'))
    rf = _dict(regime.get('freshness'))
    vector = _dict(regime.get('quad_vector'))
    tm = _dict(vector.get('transition_momentum'))
    one = _dict(regime.get('regime_one'))
    macro = _dict(one.get('macro'))
    errors: list[str] = []
    emit('macro', 'regime', '/', regime, regime.get('date'), {
        'confirmed_quad': _quad(regime.get('quad')),
        'tape_quad': _quad(_dict(one.get('tape')).get('quad')),
        'economic_quad': _quad(macro.get('quad')),
        'economic_freshness': _token(macro.get('worst_freshness')),
        'growth_proxy_score': _num(regime.get('growth_score'), 'growth_proxy_score', errors),
        'inflation_proxy_score': _num(regime.get('inflation_score'), 'inflation_proxy_score', errors),
        'transition_state': _token(regime.get('transition_state')),
        'quantity_overlay': _choice(regime.get('liquidity_overlay'), ('expanding', 'contracting', 'neutral')),
        'forecast_probability': None,
    }, 'owner_proxy_scores_and_labels', issues=errors, stale=rf.get('stale') is True,
       notes=('Mixed proxy axes are not reported GDP/inflation measurements.',
              'Membership movement is diagnostic, not a horizon-specific forecast.',
              'Economic sub-read retains its own stale/slow evidence limitation.'))

    errors = []
    prob = _dict(vector.get('p'))
    probabilities = {k: _num(prob.get(k), 'probability:' + k, errors, low=0, high=1)
                     for k in QUAD_NAMES}
    if set(prob) != set(QUAD_NAMES) or any(v is None for v in probabilities.values()) or abs(sum(v or 0 for v in probabilities.values()) - 1.) > .001:
        probabilities = {}
        if prob:
            errors.append('invalid_membership_distribution')
    emit('membership', 'regime', '/quad_vector', vector, vector.get('asof'), {
        'probabilities': probabilities,
        'interpretation': 'current_model_membership' if probabilities else None,
        'gaining_quad': _quad(tm.get('gaining')) if probabilities else None,
        'losing_quad': _quad(tm.get('losing')) if probabilities else None,
        'window_sessions': _count(tm.get('window_sessions'), 'window_sessions', errors) if probabilities else None,
        'forecast_probability': None,
    }, 'current_membership_distribution', issues=errors,
       stale=vector.get('stale') is True,
       notes=('Current membership is not an issued future forecast.',
              'A later-fit historical reconstruction is not point-in-time evidence.'))

    trans = _dict(sources.get('transmission'))
    rates = _dict(_dict(trans.get('state')).get('rates'))
    errors = []
    emit('real_rates', 'transmission', '/state/rates', rates, trans.get('asof'), {
        'level_pct': _num(rates.get('real_10y'), 'level_pct', errors),
        'change_22d_bp': _num(rates.get('real_10y_chg_22d_bp'), 'change_22d_bp', errors),
        'change_63d_bp': _num(rates.get('real_10y_chg_63d_bp'), 'change_63d_bp', errors),
        'percentile_0_1': _num(rates.get('real_10y_pctile'), 'percentile_0_1', errors, low=0, high=1),
        'owner_direction': _choice(rates.get('direction'), ('rising', 'falling', 'flat', 'stable')),
        'owner_rate_label': _token(rates.get('regime')),
        'acceleration_bp': None,
    }, 'yield_percent_and_basis_point_change', issues=errors,
       notes=('Snapshot clock only; underlying real-yield observation clock is not supplied.',
              'Owner 22d/63d windows retained; no new acceleration is calculated.',
              'Long real yield is not the short real policy rate relative to neutral.'))

    nominal = _dict(_dict(_dict(trans.get('yield_momentum')).get('series')).get('10y'))
    velocity = _dict(nominal.get('velocity_bp'))
    qualified = nominal.get('path_qualified') is True and nominal.get('status') == 'available'
    errors = []
    emit('nominal_10y', 'transmission', '/yield_momentum/series/10y', nominal, nominal.get('as_of'), {
        'level_pct': _num(nominal.get('level'), 'level_pct', errors),
        'change_5_grid_bp': _num(velocity.get('5d'), 'change_5_grid_bp', errors) if qualified else None,
        'change_22_grid_bp': _num(velocity.get('22d'), 'change_22_grid_bp', errors) if qualified else None,
        'change_63_grid_bp': _num(velocity.get('63d'), 'change_63_grid_bp', errors) if qualified else None,
        'acceleration_bp': _num(nominal.get('acceleration_bp'), 'acceleration_bp', errors) if qualified else None,
        'horizon_basis': _token(nominal.get('horizon_basis')),
        'path_qualified': qualified,
    }, 'yield_percent_and_basis_point_change', issues=errors, clock='source_observation_date',
       notes=('Weekday-grid intervals are not automatically Treasury trading sessions.',
              'Endpoint change/acceleration does not prove a durable yield peak.'))

    liq = _dict(regime.get('liquidity_quality'))
    errors = []
    emit('liquidity', 'regime', '/liquidity_quality', liq, liq.get('asof'), {
        'quality_label': _token(liq.get('label')),
        'quantity_change_bn': _num(liq.get('quantity_roc_bn'), 'quantity_change_bn', errors),
        'rrp_buffer_bn': _num(liq.get('rrp_buffer_bn'), 'rrp_buffer_bn', errors, low=0),
    }, 'owner_quantity_change_usd_billions', issues=errors,
       stale=liq.get('stale') is True,
       notes=('Quantity and composition/stress are separate readings.',))
    credit = _dict(liq.get('stress_overlay'))
    errors = []
    emit('credit', 'regime', '/liquidity_quality/stress_overlay', credit, liq.get('asof'), {
        'hy_oas_pct': _num(credit.get('hy_oas_pct'), 'hy_oas_pct', errors, low=0),
        'hy_oas_change_20d_pp': _num(credit.get('hy_oas_chg_20d'), 'hy_oas_change_20d_pp', errors),
        'nfci_level': _num(credit.get('nfci'), 'nfci_level', errors),
        'nfci_direction': _token(credit.get('nfci_trend')),
    }, 'oas_percent_change_percentage_points_nfci_index', issues=errors,
       stale=liq.get('stale') is True,
       notes=('A negative financial-conditions level may coexist with tightening.',))

    part = _dict(sources.get('participation'))
    latest, population = _dict(part.get('latest')), _dict(part.get('cohort_sizes'))
    errors = []
    pv = {
        'ai_above_50dma_pct': _num(latest.get('ai_pct50'), 'ai_above_50dma_pct', errors, low=0, high=100),
        'other_above_50dma_pct': _num(latest.get('nonai_pct50'), 'other_above_50dma_pct', errors, low=0, high=100),
        'spread_50dma_pp': _num(latest.get('spread_50'), 'spread_50dma_pp', errors, low=-100, high=100),
        'ai_above_200dma_pct': _num(latest.get('ai_pct200'), 'ai_above_200dma_pct', errors, low=0, high=100),
        'other_above_200dma_pct': _num(latest.get('nonai_pct200'), 'other_above_200dma_pct', errors, low=0, high=100),
        'ai_cohort_count': _count(population.get('ai_total'), 'ai_cohort_count', errors),
        'other_cohort_count': _count(population.get('non_ai'), 'other_cohort_count', errors),
        'universe_count': _count(population.get('universe'), 'universe_count', errors),
        'ma_eligible_denominators': None,
        'history_young': part.get('young') is True,
        'membership_version': _token(part.get('tag_version')),
    }
    emit('participation', 'participation', '/latest', part, part.get('as_of'), pv,
         'participation_percent_and_percentage_point_spread', issues=errors,
         stale=part.get('stale') is True,
         scope='AI-adjacent and other names in the owner price cache',
         notes=('Cohort counts are not per-indicator eligible denominators.',
                'Composition/relative prices do not prove literal capital flows.',
                'Current membership is not historical point-in-time membership.'))

    dispersion = _dict(sources.get('dispersion'))
    errors = []
    emit('dispersion', 'dispersion', '/', dispersion, dispersion.get('as_of'), {
        'percentile_0_1': _num(dispersion.get('dispersion_pctile'), 'percentile_0_1', errors, low=0, high=1),
        'average_correlation': _num(dispersion.get('avg_corr'), 'average_correlation', errors, low=-1, high=1),
    }, 'realized_dispersion_percentile_and_correlation', issues=errors,
       stale=dispersion.get('stale') is True,
       notes=('Do not equate realized dispersion with option-implied dispersion.',))

    options = _dict(sources.get('options'))
    chips = options.get('chips') if isinstance(options.get('chips'), list) else []
    # Duplicate source rows are ambiguous; never select whichever happens to be last.
    for key, name, unit in (
        ('vix_level', 'options_vix', 'index_implied_volatility_annualized_pct'),
        ('dspx', 'options_dspx', 'implied_dispersion_annualized_pct'),
        ('cor1m', 'options_cor1m', 'implied_correlation_index_points'),
        ('cor3m', 'options_cor3m', 'implied_correlation_index_points'),
    ):
        matches = [(i, c) for i, c in enumerate(chips) if isinstance(c, dict) and c.get('key') == key]
        errors = []
        idx, chip = matches[0] if len(matches) == 1 else (0, {})
        if len(matches) > 1:
            errors.append('ambiguous_duplicate_chip')
        emit(name, 'options', f'/chips/{idx}', chip, chip.get('last_date'), {
            'value': _num(chip.get('value'), 'value', errors, low=-100 if key.startswith('cor') else 0),
            'trailing_percentile_0_100': _num(chip.get('pctile'), 'trailing_percentile_0_100', errors, low=0, high=100),
        }, unit, issues=errors, clock='source_observation_date',
           stale=chip.get('freshness') in ('stale', 'missing'),
           notes=('Option-implied quantity, not a realized statistic or return forecast.',))

    weather = _dict(_dict(sources.get('world_state')).get('factor_weather'))
    errors = []
    emit('style', 'world_state', '/factor_weather', weather, weather.get('factor_state_as_of'), {
        'owner_style': _token(weather.get('style_regime')),
        'owner_factor_leader': _token(weather.get('factor_leader')),
        'qqq_spy_change_20d_fraction': _num(weather.get('ratio_qqq_spy_20d'), 'qqq_spy_change_20d_fraction', errors),
        'iwm_spy_change_20d_fraction': _num(weather.get('ratio_iwm_spy_20d'), 'iwm_spy_change_20d_fraction', errors),
    }, 'owner_style_and_relative_price_ratio_change', issues=errors,
       stale=weather.get('stale') is True,
       notes=('Descriptive factor context, not a new allocation or ranking.',))

    revisions = _dict(regime.get('theme_revisions'))
    themes, rows, errors = _dict(revisions.get('themes')), {}, []
    for tid, item in sorted(themes.items(), key=lambda x: str(x[0])):
        if not isinstance(tid, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,63}', tid) or not isinstance(item, dict):
            errors.append('invalid_theme_row'); continue
        sub: list[str] = []
        rows[tid] = {
            'breadth_index': _num(item.get('breadth'), tid + ':breadth_index', sub, low=-1, high=1),
            'breadth_change': _num(item.get('breadth_accel'), tid + ':breadth_change', sub, low=-2, high=2) if item.get('broadening_proxy') is not True and isinstance(item.get('basis_days'), int) and not isinstance(item.get('basis_days'), bool) and item['basis_days'] > 0 else None,
            'basis_days': _count(item.get('basis_days'), tid + ':basis_days', sub),
            'estimate_drift_90d_pct': _num(item.get('est_drift_90d'), tid + ':estimate_drift_90d_pct', sub),
            'n_covered': _count(item.get('n_covered'), tid + ':n_covered', sub),
            'n_members': _count(item.get('n_members'), tid + ':n_members', sub),
            'coverage_fraction': _num(item.get('coverage'), tid + ':coverage_fraction', sub, low=0, high=1),
            'broadening_state': _token(item.get('broadening_state')),
            'uses_broadening_proxy': item.get('broadening_proxy') is True,
        }
        errors.extend(sub)
    emit('earnings_revisions', 'regime', '/theme_revisions', revisions, revisions.get('asof'), {
        'themes': rows,
        'source_theme_count': _count(revisions.get('n_themes'), 'source_theme_count', errors),
        'included_theme_count': len(rows) if rows else None,
    }, 'revision_breadth_index_and_estimate_change_pct', issues=errors,
       stale=revisions.get('stale') is True, scope='published theme revision cohorts',
       notes=('Estimate revisions are neither realized earnings nor expected stock returns.',
              'Theme overlap means rows are not independent corroborating votes.',
              'Breadth level, change and coverage remain separate; proxy is not observed history.'))

    leaders = _dict(sources.get('leadership'))
    errors = []
    emit('leadership_damage', 'leadership', '/', leaders, leaders.get('asof'), {
        'owner_state': _token(leaders.get('state')),
        'cohort_role': _token(leaders.get('cohort_role')),
        'window_sessions': _count(leaders.get('high_window_sessions'), 'window_sessions', errors),
        'median_drawdown_fraction': _num(leaders.get('med_dd'), 'median_drawdown_fraction', errors, low=-1, high=0),
        'index_drawdown_fraction': _num(leaders.get('index_dd'), 'index_drawdown_fraction', errors, low=-1, high=0),
        'n_fresh': _count(leaders.get('n_fresh'), 'n_fresh', errors),
        'n_total': _count(leaders.get('n_total'), 'n_total', errors),
        'state_since': _date_info(leaders.get('state_since'), now)['as_of'],
    }, 'drawdown_fraction_and_session_window', issues=errors,
       stale=leaders.get('stale') is True,
       scope='owner-designated tracked AI-hardware damage cohort',
       notes=('This fixed damage-monitor cohort is not all current market leaders.',))

    populated = sum(bool(d['values']) and _has_value(d['values']) for d in dims.values())
    return {
        'schema': SCHEMA, 'scope': 'US; existing regional packet blocks are separate',
        'observed_at': now.isoformat(), 'expected_us_session': expected_session.isoformat() if expected_session else None, 'dimensions': dims,
        'coverage': {'total_dimensions': len(dims), 'populated_dimensions': populated,
                     'missing_dimensions': len(dims) - populated},
        'historical_replay_eligible': False,
        'authority': {k: False for k in ('may_rank', 'may_gate', 'may_size', 'may_trade', 'may_forecast', 'may_escalate')},
        'unmeasured': ['literal_capital_flows', 'valuation_implied_expected_returns',
                       'causal_identification', 'calibrated_transition_forecasts'],
    }


def read_context(root: Path, *, now: datetime | None = None) -> dict:
    """Capture bounded product files exactly once. Never runs their producers."""
    root = Path(root)
    sources, metadata, gaps = {}, {}, []
    for key, rel in SOURCE_PATHS.items():
        try:
            with (root / rel).open('rb') as stream:
                data = stream.read(MAX_SOURCE_BYTES + 1)
            if len(data) > MAX_SOURCE_BYTES:
                raise ValueError('source exceeds context read limit')
            payload = json.loads(data)
            if not isinstance(payload, dict):
                raise ValueError('source is not an object')
            sources[key] = payload
            metadata[key] = {'sha256': hashlib.sha256(data).hexdigest()}
        except (OSError, ValueError, TypeError, UnicodeError, RecursionError) as exc:
            sources[key] = None
            gaps.append({'source': key, 'reason': type(exc).__name__})
    observed = now or datetime.now(timezone.utc)
    expected = None
    try:
        from lib.nyse_calendar import expected_last_session
        expected = expected_last_session(observed)
    except (ImportError, ValueError, TypeError, OverflowError) as exc:
        gaps.append({'source': 'us_session_calendar', 'reason': type(exc).__name__})
    ctx = compose_context(sources, now=observed, source_metadata=metadata,
                          expected_session=expected)
    ctx['read_gaps'] = gaps
    return ctx


def _fmt(v, *, signed=False, scale=1.) -> str:
    if v is None:
        return '?'
    value = float(v) * scale
    if not math.isfinite(value):
        return '?'
    text = f'{value:+.2f}' if signed else f'{value:.2f}'
    return text.rstrip('0').rstrip('.')


def render_context(ctx: dict, char_budget: int = 1800, *, lang: str = 'en') -> str:
    """Bounded complete rows, with limits/omissions retained rather than clipped."""
    dims = _dict(_dict(ctx).get('dimensions'))
    zh = lang == 'zh'
    rows: list[tuple[str, str]] = []

    def add(key, label, text):
        d = _dict(dims.get(key))
        if not d.get('values') or d.get('status') in ('missing', 'future_dated', 'unknown_date'):
            return
        stamp = _dict(d.get('source')).get('as_of') or '?'
        suffix = '; stale/last-known' if d.get('status') == 'stale' else ''
        age = _dict(d.get('source')).get('age_calendar_days')
        if not suffix and isinstance(age, int) and age > 1:
            suffix = f'; {age} calendar days old'
        if d.get('issues'):
            suffix += '; partial input'
        clock = 'observed' if _dict(d.get('source')).get('clock_semantics') == 'source_observation_date' else 'snapshot'
        rows.append((key, f'{label} [{clock} {stamp}{suffix}]: {text}'))

    def v(key):
        return _dict(_dict(dims.get(key)).get('values'))

    x = v('real_rates')
    add('real_rates', 'Real 10Y' if not zh else '\u5b9e\u964510\u5e74\u671f',
        f"{_fmt(x.get('level_pct'))}%; owner {x.get('owner_direction') or '?'}; "
        f"22d {_fmt(x.get('change_22d_bp'), signed=True)}bp, 63d {_fmt(x.get('change_63d_bp'), signed=True)}bp; snapshot date only")
    x = v('participation')
    add('participation', 'Participation' if not zh else '\u53c2\u4e0e\u5ea6',
        f"AI {_fmt(x.get('ai_above_50dma_pct'))}% vs others {_fmt(x.get('other_above_50dma_pct'))}% above 50DMA; "
        f"cohorts {x.get('ai_cohort_count')}/{x.get('other_cohort_count')}; indicator denominators unreported")
    x = v('dispersion')
    add('dispersion', 'Realized dispersion' if not zh else '\u5b9e\u73b0\u79bb\u6563\u5ea6',
        f"percentile {_fmt(x.get('percentile_0_1'), scale=100)}/100; mean correlation {_fmt(x.get('average_correlation'))}")
    for key, label in (('options_vix', 'VIX implied index vol'), ('options_dspx', 'DSPX implied dispersion'),
                       ('options_cor1m', 'COR1M implied correlation')):
        add(key, label, _fmt(v(key).get('value')) + '; unlike measures, not a synthetic spread')
    x = v('earnings_revisions')
    themes = _dict(x.get('themes'))
    selected = [k for k in BRIEF_THEME_IDS if k in themes]
    detail = []
    for tid in selected:
        t = themes[tid]
        detail.append(f"{tid.replace('_', ' ')} breadth {_fmt(t.get('breadth_index'), signed=True)}, "
                      f"change {_fmt(t.get('breadth_change'), signed=True)} over {t.get('basis_days') or '?'} calendar days, "
                      f"coverage {t.get('n_covered')}/{t.get('n_members')}")
    add('earnings_revisions', 'Estimate revisions (named examples; not stock returns)', '; '.join(detail) or 'No named example covered')
    x = v('liquidity')
    add('liquidity', 'Liquidity', f"quality {x.get('quality_label') or '?'}; RRP buffer {_fmt(x.get('rrp_buffer_bn'))}bn")
    x = v('credit')
    add('credit', 'Credit/conditions', f"HY OAS {_fmt(x.get('hy_oas_pct'))}%, 20d change {_fmt(x.get('hy_oas_change_20d_pp'), signed=True)}pp; "
        f"NFCI {_fmt(x.get('nfci_level'))}, {x.get('nfci_direction') or '?'}")
    x = v('style')
    add('style', 'Style', f"{x.get('owner_style') or '?'}, owner leader {x.get('owner_factor_leader') or '?'}; "
        f"QQQ/SPY 20d {_fmt(x.get('qqq_spy_change_20d_fraction'), signed=True, scale=100)}%")
    x = v('macro')
    add('macro', 'Macro model', f"confirmed {QUAD_NAMES.get(x.get('confirmed_quad'), '?')}; "
        f"tape {QUAD_NAMES.get(x.get('tape_quad'), '?')}; economic {QUAD_NAMES.get(x.get('economic_quad'), '?')} "
        f"({x.get('economic_freshness') or 'freshness unknown'}); {x.get('transition_state') or '?'}; liquidity quantity {x.get('quantity_overlay') or '?'}")
    x = v('membership')
    add('membership', 'Model membership, not future odds', f"gaining {QUAD_NAMES.get(x.get('gaining_quad'), '?')}; losing {QUAD_NAMES.get(x.get('losing_quad'), '?')}; window {x.get('window_sessions') or '?'} sessions")
    x = v('leadership_damage')
    add('leadership_damage', 'Tracked AI-hardware damage cohort, not all leaders',
        f"median {_fmt(x.get('median_drawdown_fraction'), scale=100)}% from {x.get('window_sessions') or '?'}-session high; "
        f"coverage {x.get('n_fresh')}/{x.get('n_total')}")
    x = v('nominal_10y')
    add('nominal_10y', 'Nominal 10Y', f"{_fmt(x.get('level_pct'))}%; 5 weekday-grid change "
        f"{_fmt(x.get('change_5_grid_bp'), signed=True)}bp; acceleration {_fmt(x.get('acceleration_bp'), signed=True)}bp")
    if not rows:
        return ''
    header = 'REGIME DETAIL [US; source-dated context, not a forecast]:'
    caveat = 'Limits: no measured capital transfer, valuation-implied return or calibrated transition forecast. Different dates/scopes are not independent votes.'
    budget = max(0, int(char_budget))
    kept = list(rows)
    omitted: list[str] = []
    while kept:
        tail = '\nOmitted from compact brief: ' + ', '.join(omitted) + '.' if omitted else ''
        text = header + '\n' + '\n'.join(t for _, t in kept) + '\n' + caveat + tail
        if len(text) <= budget:
            return text
        key, _ = kept.pop()
        omitted.insert(0, key.replace('_', ' '))
    return ''
