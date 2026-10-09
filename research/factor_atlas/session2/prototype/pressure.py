"""Factor Atlas: original, production-inert capital-pressure research primitives.

No I/O, ingest, calendar generation, identity registry, revision resolution or
publication. Caller supplies qualified observations and incumbent-owner refs.
The disclosed-core profile follows LIQN's public mathematical outline; numerical
parity remains unproved because several vendor edge policies are undisclosed.
All inferred pressure is descriptive; it does not identify beneficial owners.
"""
from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
import hashlib
import json
import math
from statistics import median, stdev
from typing import Iterable, Sequence

from scipy.special import ndtr, stdtr

ET = ZoneInfo('America/New_York')


def _et_clock(utc_s: int) -> tuple[str, int, int]:
    try:
        dt = datetime.fromtimestamp(utc_s, timezone.utc).astimezone(ET)
        return dt.date().isoformat(), dt.hour * 60 + dt.minute, dt.second
    except (ValueError, OverflowError, OSError):
        raise ValueError('invalid_utc_clock') from None


MAD_NORMAL_SCALE = 1.482602218505602
AUTHORITY = tuple((name, False) for name in
                  ('may_rank', 'may_alert', 'may_size', 'may_trade', 'may_publish'))


def _finite(value: object, name: str, *, nonnegative: bool = False,
            positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name}: finite_number_required')
    try:
        result = float(value)
    except (ValueError, OverflowError):
        raise ValueError(f'{name}: finite_number_required') from None
    if not math.isfinite(result) or (nonnegative and result < 0) or (positive and result <= 0):
        raise ValueError(f'{name}: invalid_number')
    return result


def _integer(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f'{name}: integer_utc_seconds_required')
    return value


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 256:
        raise ValueError(f'{name}: nonempty_bounded_identity_required')
    return value


def _date(value: str) -> str:
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError('canonical_session_date_required') from None
    return value


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class Segment:
    session_id: str
    phase: str
    start_utc_s: int
    end_utc_s: int
    calendar_ref: str
    session_class: str

    def validate(self) -> None:
        _date(self.session_id)
        if self.phase not in ('PRE', 'RTH', 'AH'):
            raise ValueError('invalid_phase')
        _integer(self.start_utc_s, 'segment_start')
        _integer(self.end_utc_s, 'segment_end')
        if self.start_utc_s >= self.end_utc_s:
            raise ValueError('invalid_segment')
        if (_et_clock(self.start_utc_s)[0] != self.session_id
                or _et_clock(self.end_utc_s - 1)[0] != self.session_id):
            raise ValueError('session_clock_mismatch')
        _text(self.calendar_ref, 'calendar_ref')
        _text(self.session_class, 'session_class')


@dataclass(frozen=True)
class Bar:
    security_id: str
    segment: Segment
    start_utc_s: int
    end_utc_s: int
    available_at_utc_s: int | None
    close: float
    volume: float
    vwap: float | None
    basis_id: str
    source_revision: str
    rights_ref: str


@dataclass(frozen=True)
class BVCConfig:
    window_minutes: int = 60
    min_returns: int = 20
    cdf: str = 'student_t'
    degrees_freedom: float | None = 0.25
    zero_volatility: str = 'neutral'
    change_basis: str = 'simple_return'
    notional_basis: str = 'vwap_if_present'
    history_scope: str = 'segment'
    warmup_policy: str = 'unavailable'

    def validate(self) -> None:
        _integer(self.window_minutes, 'window_minutes')
        _integer(self.min_returns, 'min_returns')
        if not 2 <= self.min_returns <= self.window_minutes <= 240:
            raise ValueError('invalid_history_configuration')
        _validate_cdf(self.cdf, self.degrees_freedom, self.zero_volatility)
        for name, allowed in (('change_basis', ('simple_return', 'price_change')),
                              ('notional_basis', ('vwap_if_present', 'close')),
                              ('history_scope', ('segment', 'session')),
                              ('warmup_policy', ('unavailable', 'neutral'))):
            if getattr(self, name) not in allowed:
                raise ValueError('unsupported_' + name)

    @property
    def identity(self) -> str:
        return 'factor_atlas.bvc.prototype.v2:' + digest(asdict(self))


def disclosed_core_config() -> BVCConfig:
    """Public LIQN outline, with explicit reconstruction assumptions.

    Documented: price changes, t(.25), 60-minute same-session history, neutral
    warmup, volume times close. Assumed: lagged ddof=1, 20 valid prior changes,
    no gap bridge, neutral zero variance. This is not a vendor parity claim.
    """
    return BVCConfig(change_basis='price_change', notional_basis='close',
                     history_scope='session', warmup_policy='neutral')


def _validate_cdf(cdf: str, df: float | None, zero_volatility: str) -> None:
    if cdf not in ('student_t', 'normal'):
        raise ValueError('unsupported_cdf')
    if cdf == 'student_t':
        _finite(df, 'degrees_freedom', positive=True)
    elif df is not None:
        raise ValueError('normal_profile_requires_no_degrees_freedom')
    if zero_volatility not in ('neutral', 'one_sided_limit'):
        raise ValueError('unsupported_zero_volatility_policy')


def buy_fraction(return_value: float, sigma: float, cdf: str = 'student_t',
                 degrees_freedom: float | None = 0.25,
                 zero_volatility: str = 'neutral') -> float:
    """Estimated fraction, not a calibrated probability of investor identity."""
    r = _finite(return_value, 'return')
    s = _finite(sigma, 'sigma', nonnegative=True)
    _validate_cdf(cdf, degrees_freedom, zero_volatility)
    if s == 0:
        if zero_volatility == 'neutral' or r == 0:
            return .5
        return 1. if r > 0 else 0.
    z = r / s
    # An infinite standardized move has the analytic one-sided CDF limit.
    if math.isinf(z):
        return 1. if z > 0 else 0.
    value = float(stdtr(degrees_freedom, z) if cdf == 'student_t' else ndtr(z))
    return min(1., max(0., value))


@dataclass(frozen=True)
class PressurePoint:
    bar: Bar
    estimator_id: str
    mode: str
    gross_usd: float
    gross_basis: str
    buy_fraction: float | None
    buy_usd: float | None
    sell_usd: float | None
    net_usd: float | None
    state: str
    directionally_usable: bool
    sigma: float | None
    n_history: int
    availability_eligible: bool  # Clock eligibility only; custody is established by the input owner.
    input_digest: str
    authority: tuple[tuple[str, bool], ...] = AUTHORITY


def _validate_bar(bar: Bar) -> None:
    _text(bar.security_id, 'security_id')
    if not isinstance(bar.segment, Segment):
        raise ValueError('qualified_segment_required')
    bar.segment.validate()
    _integer(bar.start_utc_s, 'bar_start')
    _integer(bar.end_utc_s, 'bar_end')
    if bar.end_utc_s - bar.start_utc_s != 60 or bar.start_utc_s % 60:
        raise ValueError('exact_one_minute_grain_required')
    if not (bar.segment.start_utc_s <= bar.start_utc_s < bar.end_utc_s <= bar.segment.end_utc_s):
        raise ValueError('segment_boundary')
    if bar.available_at_utc_s is not None:
        _integer(bar.available_at_utc_s, 'available_at')
        if bar.available_at_utc_s < bar.end_utc_s:
            raise ValueError('available_before_bar_close')
    _finite(bar.close, 'close', positive=True)
    _finite(bar.volume, 'volume', nonnegative=True)
    if bar.vwap is not None:
        _finite(bar.vwap, 'vwap', positive=True)
    _text(bar.basis_id, 'basis_id')
    if bar.basis_id != 'unadjusted/USD' and not bar.basis_id.startswith('unadjusted/USD/'):
        raise ValueError('unadjusted_usd_monetary_basis_required')
    _text(bar.source_revision, 'source_revision')
    _text(bar.rights_ref, 'rights_ref')


def bvc_series(bars: Iterable[Bar], config: BVCConfig, *, cutoff_utc_s: int,
               mode: str = 'as_observed') -> tuple[PressurePoint, ...]:
    """Deterministic calculation on already-qualified, revision-resolved input.

    The current return never enters its own scale. Reset at each supplied
    session segment/basis. Missing slots are not filled. Corrected-history mode
    permits later-vintage geometry but grants no past operational availability.
    """
    config.validate()
    _integer(cutoff_utc_s, 'cutoff')
    if mode not in ('as_observed', 'corrected_history'):
        raise ValueError('invalid_mode')
    eligible = []
    for bar in bars:
        if not isinstance(bar, Bar):
            raise ValueError('bar_required')
        _integer(bar.end_utc_s, 'bar_end')
        # Do not let later corruption/revisions change a lawful earlier prefix.
        if bar.end_utc_s > cutoff_utc_s:
            continue
        if mode == 'as_observed':
            if bar.available_at_utc_s is None:
                raise ValueError('availability_missing')
            _integer(bar.available_at_utc_s, 'available_at')
            if bar.available_at_utc_s > cutoff_utc_s:
                continue
        _validate_bar(bar)
        eligible.append(bar)
    eligible.sort(key=lambda b: (b.start_utc_s, b.security_id))
    seen = set()
    history: dict[tuple, deque[tuple[int, float]]] = {}
    previous: dict[tuple, Bar | None] = {}
    output = []
    estimator_id = config.identity
    for bar in eligible:
        identity = (bar.security_id, bar.start_utc_s)
        if identity in seen:
            raise ValueError('duplicate_bar_revision_requires_owner_resolution')
        seen.add(identity)
        history_identity = (bar.segment.session_id, bar.segment.calendar_ref,
                            bar.segment.session_class) if config.history_scope == 'session' else bar.segment
        scope = (bar.security_id, history_identity, bar.basis_id)
        h = history.setdefault(scope, deque())
        lower = bar.end_utc_s - 60 * config.window_minutes
        while h and h[0][0] < lower:
            h.popleft()
        prev = previous.get(scope)
        is_first = scope not in previous
        sigma = None
        n = len(h)
        p = None
        directionally_usable = False
        current_return = None
        use_vwap = config.notional_basis == 'vwap_if_present' and bar.vwap is not None
        price = bar.vwap if use_vwap else bar.close
        gross = _finite(price * bar.volume, 'derived_gross', nonnegative=True)
        gross_basis = 'bar_vwap_x_volume_estimate' if use_vwap else 'bar_close_x_volume_proxy'
        if bar.volume == 0:
            p, state = .5, 'ZERO_VOLUME'
        elif is_first:
            p, state = .5, 'FIRST_BAR_NEUTRAL'
        elif prev is None or prev.end_utc_s != bar.start_utc_s:
            p, state = .5, 'GAP_NEUTRAL'
        else:
            change = bar.close - prev.close if config.change_basis == 'price_change' else bar.close / prev.close - 1.
            current_return = _finite(change, 'derived_change')
            if n < config.min_returns:
                p = .5 if config.warmup_policy == 'neutral' else None
                state = 'WARMUP_NEUTRAL' if p is not None else 'INSUFFICIENT_HISTORY'
            else:
                sigma = _finite(stdev(x[1] for x in h), 'derived_sigma', nonnegative=True)
                p = buy_fraction(current_return, sigma, config.cdf,
                                 config.degrees_freedom, config.zero_volatility)
                if sigma == 0:
                    state = 'ZERO_VOL_NEUTRAL' if config.zero_volatility == 'neutral' else 'ZERO_VOL_LIMIT'
                else:
                    state = 'FLAT' if current_return == 0 else 'SIGNED'
                    directionally_usable = True
        buy = gross * p if p is not None else None
        sell = gross - buy if buy is not None else None
        net = buy - sell if buy is not None else None
        if net == 0:
            net = 0.0  # Stable signed-zero serialization.
        output.append(PressurePoint(
            bar, estimator_id, mode, gross, gross_basis, p, buy, sell, net,
            state, directionally_usable, sigma, n,
            bar.available_at_utc_s is not None and bar.available_at_utc_s <= cutoff_utc_s,
            digest(asdict(bar))))
        if current_return is not None:
            h.append((bar.end_utc_s, current_return))
        previous[scope] = bar if bar.volume > 0 else None
    return tuple(output)


@dataclass(frozen=True)
class MatchKey:
    subject: str
    phase: str
    clock_minute: int
    session_class: str
    measure: str
    estimator_id: str
    membership_id: str
    basis_id: str
    interval_seconds: int
    currency: str

    def validate(self) -> None:
        for name in ('subject','session_class','measure','estimator_id','membership_id','basis_id','currency'):
            _text(getattr(self, name), name)
        if self.phase not in ('PRE','RTH','AH'):
            raise ValueError('invalid_phase')
        _integer(self.clock_minute, 'clock_minute')
        _integer(self.interval_seconds, 'interval_seconds')
        if not 0 <= self.clock_minute < 1440 or self.interval_seconds <= 0:
            raise ValueError('invalid_clock_key')


@dataclass(frozen=True)
class Reference:
    key: MatchKey
    session_id: str
    event_end_utc_s: int
    available_at_utc_s: int | None
    value: float
    gross_usd: float
    complete: bool
    source_revision: str

    def validate(self) -> None:
        self.key.validate()
        _date(self.session_id)
        _integer(self.event_end_utc_s, 'reference_end')
        day, minute, second = _et_clock(self.event_end_utc_s)
        if day != self.session_id:
            raise ValueError('session_clock_mismatch')
        if minute != self.key.clock_minute or second != 0:
            raise ValueError('matched_clock_mismatch')
        if self.available_at_utc_s is None:
            raise ValueError('reference_availability_missing')
        _integer(self.available_at_utc_s, 'reference_available_at')
        if self.available_at_utc_s < self.event_end_utc_s:
            raise ValueError('reference_available_before_close')
        _finite(self.value, 'reference_value')
        _finite(self.gross_usd, 'reference_gross', nonnegative=True)
        if not isinstance(self.complete, bool):
            raise ValueError('reference_complete_boolean_required')
        _text(self.source_revision, 'reference_revision')


@dataclass(frozen=True)
class BaselineConfig:
    max_sessions: int = 60
    min_observations: int = 20
    minimum_coverage: float = .8
    absolute_floor: float = 0.
    relative_floor: float = 0.
    display_clip: float = 12.

    def validate(self) -> None:
        _integer(self.max_sessions, 'max_sessions')
        _integer(self.min_observations, 'min_observations')
        if not 2 <= self.min_observations <= self.max_sessions <= 252:
            raise ValueError('invalid_baseline_sample_configuration')
        coverage = _finite(self.minimum_coverage, 'minimum_coverage', positive=True)
        if coverage > 1:
            raise ValueError('invalid_minimum_coverage')
        _finite(self.absolute_floor, 'absolute_floor', nonnegative=True)
        _finite(self.relative_floor, 'relative_floor', nonnegative=True)
        _finite(self.display_clip, 'display_clip', positive=True)


@dataclass(frozen=True)
class BaselineResult:
    status: str
    n: int
    scheduled_sessions: int
    coverage: float
    median: float | None
    mad: float | None
    scale: float | None
    floor_applied: bool
    z_raw: float | None
    z_display: float | None
    percentile: float | None
    reference_digest: str
    authority: tuple[tuple[str, bool], ...] = AUTHORITY


def matched_baseline(target: Reference, history: Iterable[Reference],
                     prior_sessions: Sequence[str], config: BaselineConfig, *,
                     cutoff_utc_s: int) -> BaselineResult:
    """Prior-session-only reference; no implicit calendar or revision choice."""
    config.validate()
    target.validate()
    _integer(cutoff_utc_s, 'cutoff')
    if (target.event_end_utc_s > cutoff_utc_s or target.available_at_utc_s > cutoff_utc_s
            or not target.complete):
        raise ValueError('target_not_available_and_complete')
    days = tuple(prior_sessions)
    if (not days or len(days) > config.max_sessions or len(set(days)) != len(days)
            or tuple(sorted(days)) != days):
        raise ValueError('invalid_prior_session_window')
    for day in days:
        _date(day)
        if day >= target.session_id:
            raise ValueError('reference_window_must_precede_target_session')
    allowed = set(days)
    selected = []
    seen = set()
    for row in history:
        if (row.key != target.key or row.session_id not in allowed
                or row.session_id >= target.session_id or not row.complete):
            continue
        _integer(row.event_end_utc_s, 'reference_end')
        if row.event_end_utc_s > cutoff_utc_s:
            continue
        if row.available_at_utc_s is None:
            continue
        _integer(row.available_at_utc_s, 'reference_available')
        if row.available_at_utc_s > cutoff_utc_s:
            continue
        row.validate()
        if row.session_id in seen:
            raise ValueError('duplicate_reference_revision_requires_owner_resolution')
        seen.add(row.session_id)
        selected.append(row)
    selected.sort(key=lambda row: row.session_id)
    n = len(selected)
    coverage = n / len(days)
    reference_digest = digest({'key': asdict(target.key), 'prior_sessions': days,
                               'rows': [asdict(x) for x in selected]})
    unavailable = lambda status: BaselineResult(status, n, len(days), coverage,
                                                None, None, None, False, None,
                                                None, None, reference_digest)
    if n < config.min_observations:
        return unavailable('INSUFFICIENT_OBSERVATIONS')
    if coverage < config.minimum_coverage:
        return unavailable('INSUFFICIENT_COVERAGE')
    values = [float(x.value) for x in selected]
    center = median(values)
    mad = median(abs(x-center) for x in values)
    raw_scale = MAD_NORMAL_SCALE * mad
    floor = max(config.absolute_floor,
                config.relative_floor * median(x.gross_usd for x in selected))
    scale = _finite(max(raw_scale, floor), 'derived_scale', nonnegative=True)
    floored = floor > raw_scale
    percentile = (sum(x < target.value for x in values) + .5 * sum(x == target.value for x in values)) / n
    if scale == 0:
        return BaselineResult('ZERO_SCALE', n, len(days), coverage, center, mad,
                              0., False, None, None, percentile, reference_digest)
    z = _finite((target.value-center)/scale, 'derived_z')
    return BaselineResult('FLOORED_SCALE' if floored else 'OK', n, len(days),
                          coverage, center, mad, scale, floored, z,
                          min(config.display_clip, max(-config.display_clip, z)),
                          percentile, reference_digest)


@dataclass(frozen=True)
class Membership:
    factor_id: str
    version: str
    basis: str
    member_ids: tuple[str, ...]


@dataclass(frozen=True)
class FactorPressure:
    factor_id: str
    membership_version: str
    membership_basis: str
    expected_members: int
    observed_members: int
    member_coverage: float
    gross_usd_observed: float
    classified_gross_usd: float
    net_usd_covered: float
    estimated_net_usd: float | None
    directional_notional_coverage: float | None
    pressure_ratio_covered: float | None
    top_member_gross_share: float | None
    effective_n_gross: float | None
    contributions: tuple[tuple[str, float | None, float | None, str], ...]


@dataclass(frozen=True)
class MultiFactorPressure:
    factors: tuple[FactorPressure, ...]
    union_gross_usd: float
    sum_factor_gross_usd: float
    duplicated_gross_usd: float
    overlap: tuple[tuple[str, tuple[str, ...]], ...]
    authority: tuple[tuple[str, bool], ...] = AUTHORITY


def _validate_point(point: PressurePoint) -> None:
    if not isinstance(point, PressurePoint):
        raise ValueError('pressure_point_required')
    _validate_bar(point.bar)
    if point.authority != AUTHORITY or point.mode not in ('as_observed','corrected_history'):
        raise ValueError('invalid_research_authority_or_mode')
    if point.input_digest != digest(asdict(point.bar)):
        raise ValueError('input_digest_mismatch')
    _text(point.estimator_id, 'estimator_id')
    _integer(point.n_history, 'n_history')
    if point.n_history < 0 or not isinstance(point.directionally_usable, bool):
        raise ValueError('invalid_direction_quality')
    bar = point.bar
    if point.gross_basis not in ('bar_vwap_x_volume_estimate', 'bar_close_x_volume_proxy'):
        raise ValueError('gross_basis_unknown')
    use_vwap = point.gross_basis == 'bar_vwap_x_volume_estimate'
    if use_vwap and bar.vwap is None:
        raise ValueError('vwap_missing')
    expected_gross = (bar.vwap if use_vwap else bar.close) * bar.volume
    gross = _finite(point.gross_usd, 'gross', nonnegative=True)
    if gross != expected_gross:
        raise ValueError('gross_accounting_mismatch')
    if point.buy_fraction is None:
        if any(v is not None for v in (point.buy_usd,point.sell_usd,point.net_usd)) or point.directionally_usable:
            raise ValueError('null_pressure_mismatch')
    else:
        fraction = _finite(point.buy_fraction, 'buy_fraction', nonnegative=True)
        if fraction > 1:
            raise ValueError('invalid_buy_fraction')
        buy = _finite(point.buy_usd, 'buy', nonnegative=True)
        sell = _finite(point.sell_usd, 'sell', nonnegative=True)
        net = _finite(point.net_usd, 'net')
        eq = lambda x,y: math.isclose(x,y,rel_tol=1e-12,abs_tol=1e-8)
        if (not eq(buy,gross*fraction) or not eq(buy+sell,gross)
                or not eq(buy-sell,net) or abs(net) > gross + max(1e-8,gross*1e-12)):
            raise ValueError('net_gross_accounting_mismatch')
    if point.directionally_usable:
        if point.state not in ('SIGNED','FLAT') or point.buy_fraction is None:
            raise ValueError('invalid_direction_state')
        _finite(point.sigma, 'sigma', positive=True)


def aggregate_factors(points: Sequence[PressurePoint],
                      memberships: Sequence[Membership]) -> MultiFactorPressure:
    """One-clock raw-dollar join, not a replacement membership/identity owner.

    Sum-of-factors is returned ONLY to expose duplicated inclusion. Union counts
    each supplied security once. Missing constituents and warmup stay visible.
    """
    by_id = {}
    clock = None
    for point in points:
        _validate_point(point)
        sid = point.bar.security_id
        if sid in by_id:
            raise ValueError('duplicate_security_observation')
        current = (point.bar.end_utc_s, point.bar.segment.session_id, point.bar.segment.phase,
                   point.bar.segment.session_class, point.bar.segment.calendar_ref,
                   point.estimator_id, point.mode)
        if clock is not None and current != clock:
            raise ValueError('incompatible_source_clock_or_estimator')
        clock = current
        by_id[sid] = point
    seen_factors = set()
    membership_of: dict[str, list[str]] = {}
    factors = []
    for membership in sorted(memberships, key=lambda m: m.factor_id):
        _text(membership.factor_id, 'factor_id')
        _text(membership.version, 'membership_version')
        if membership.factor_id in seen_factors:
            raise ValueError('duplicate_factor_identity')
        seen_factors.add(membership.factor_id)
        if membership.basis not in ('current_cohort', 'point_in_time'):
            raise ValueError('membership_basis_required')
        ids = tuple(sorted(membership.member_ids))
        if not ids:
            raise ValueError('empty_membership')
        if len(set(ids)) != len(ids):
            raise ValueError('duplicate_member')
        for sid in ids:
            _text(sid, 'member_id')
            membership_of.setdefault(sid, []).append(membership.factor_id)
        observed = [by_id[s] for s in ids if s in by_id]
        classified = [p for p in observed if p.directionally_usable]
        gross = math.fsum(p.gross_usd for p in observed)
        classified_gross = math.fsum(p.gross_usd for p in classified)
        net = math.fsum(p.net_usd for p in classified)
        covered = len(observed) == len(ids) and all(p.directionally_usable or p.gross_usd == 0 for p in observed)
        shares = [p.gross_usd/gross for p in observed] if gross else []
        contributions = tuple((sid, by_id[sid].gross_usd, by_id[sid].net_usd, by_id[sid].state)
                              if sid in by_id else (sid,None,None,'MISSING') for sid in ids)
        factors.append(FactorPressure(
            membership.factor_id, membership.version, membership.basis, len(ids), len(observed),
            len(observed)/len(ids), gross, classified_gross, net, net if covered else None,
            classified_gross/gross if gross else None, net/classified_gross if classified_gross else None,
            max(shares) if shares else None, 1/math.fsum(x*x for x in shares) if shares else None,
            contributions))
    union_gross = math.fsum(by_id[s].gross_usd for s in sorted(membership_of) if s in by_id)
    factor_gross = math.fsum(f.gross_usd_observed for f in factors)
    overlap = tuple((sid, tuple(sorted(names))) for sid,names in sorted(membership_of.items()) if len(names)>1)
    return MultiFactorPressure(tuple(factors), union_gross, factor_gross,
                               math.fsum(by_id[s].gross_usd * (len(names)-1) for s,names in membership_of.items() if s in by_id), overlap)
