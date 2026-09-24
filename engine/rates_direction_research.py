"""RIC research-only chronological yield forecasts; no IO or live authority.

Cached observations do not certify historical availability. This consumer uses
existing source rows and validation math, not a new source/evaluation store.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping
import math

import numpy as np
import pandas as pd

from engine.validation import newey_west_tstat

TENORS = ('2y', '5y', '10y', '30y')
MODELS = ('no_change', 'momentum_5', 'ridge_curve', 'ridge_curve_real')
FEATURES = ('change_5_bp', 'change_22_bp', 'change_63_bp', 'vol_20_bp',
            'curve_10y_2y_bp', 'curve_30y_5y_bp',
            'real_10y_change_5_bp', 'breakeven_10y_change_5_bp')


@dataclass(frozen=True)
class ForecastSpec:
    train_min: int = 504
    train_max: int = 1260
    calibration_min: int = 126
    calibration_max: int = 252
    refit_every: int = 20
    ridge_penalty: float = 10.0
    max_gap_days: int = 4
    flat_band_bp: float = 1.0
    jump_sigma: float = 2.0
    jump_floor_bp: float = 10.0

    def __post_init__(self):
        integers = (self.train_min, self.train_max, self.calibration_min,
                    self.calibration_max, self.refit_every, self.max_gap_days)
        if any(type(v) is not int or v < 1 for v in integers):
            raise ValueError('window lengths must be positive integers')
        if self.train_min > self.train_max or self.calibration_min > self.calibration_max:
            raise ValueError('minimum window exceeds maximum')
        numbers = (self.ridge_penalty, self.flat_band_bp,
                   self.jump_sigma, self.jump_floor_bp)
        if any(not np.isfinite(v) or v <= 0 for v in numbers):
            raise ValueError('penalties and thresholds must be finite and positive')


def prepare_panel(sources: Mapping[str, pd.Series]) -> pd.DataFrame:
    """Preserve the DGS10 observation grid, never fill or compact other inputs."""
    clean = {}
    for key, series in sources.items():
        index = series.index
        if (not isinstance(index, pd.DatetimeIndex) or index.hasnans
                or not index.is_unique or index.tz is not None
                or not index.equals(index.normalize())):
            raise ValueError('sources require unique timezone-naive daily date labels')
        clean[key] = pd.to_numeric(series.sort_index(), errors='coerce').replace(
            [np.inf, -np.inf], np.nan)
    if '10y' not in clean or clean['10y'].dropna().empty:
        raise ValueError('DGS10 observed-date anchor is unavailable')
    index = clean['10y'].dropna().index
    return pd.DataFrame({key: clean.get(key, pd.Series(dtype=float)).reindex(index)
                         for key in (*TENORS, 'real10y')}, index=index)


def build_features(panel: pd.DataFrame, tenor: str, max_gap_days: int = 4) -> pd.DataFrame:
    if tenor not in TENORS:
        raise ValueError('unsupported tenor')
    nominal, real = panel[tenor], panel['real10y']
    gaps = panel.index.to_series().diff().dt.days.fillna(0)
    path = (gaps.rolling(63).max() <= max_gap_days) & (nominal.rolling(64).count() == 64)
    real_path = real.rolling(6).count() == 6
    result = pd.DataFrame({
        FEATURES[0]: nominal.diff(5) * 100,
        FEATURES[1]: nominal.diff(22) * 100,
        FEATURES[2]: nominal.diff(63) * 100,
        FEATURES[3]: nominal.diff().rolling(20).std(ddof=1) * 100,
        FEATURES[4]: (panel['10y'] - panel['2y']) * 100,
        FEATURES[5]: (panel['30y'] - panel['5y']) * 100,
        FEATURES[6]: (real.diff(5) * 100).where(real_path),
        FEATURES[7]: ((panel['10y'] - real).diff(5) * 100).where(real_path),
    }, index=panel.index)
    return result.where(path, np.nan).replace([np.inf, -np.inf], np.nan)


def _ridge(x: np.ndarray, y: np.ndarray, penalty: float):
    mean, scale = x.mean(axis=0), x.std(axis=0)
    scale = np.where(scale > 1e-10, scale, 1.0)
    z, center = (x - mean) / scale, float(y.mean())
    beta = np.linalg.solve(z.T @ z + penalty * np.eye(x.shape[1]), z.T @ (y - center))
    return lambda values: center + ((values - mean) / scale) @ beta


def walk_forward(panel: pd.DataFrame, tenor: str, horizon: int,
                 spec: ForecastSpec | None = None) -> dict:
    """Purged fit -> held-back residual calibration -> later forecast origins.

    Refits are on a fixed observation cadence, never selected by outcomes.
    Model inputs are common-panel qualified for fair ablation comparisons.
    """
    spec = spec or ForecastSpec()
    if tenor not in TENORS or type(horizon) is not int or horizon < 1:
        raise ValueError('unsupported tenor or nonpositive horizon')
    features = build_features(panel, tenor, spec.max_gap_days)
    x, n = features.to_numpy(dtype=float), len(panel)
    values = panel[tenor]
    y = ((values.shift(-horizon) - values) * 100).to_numpy(dtype=float, copy=True)
    gaps = panel.index.to_series().diff().dt.days.fillna(0)
    target_ok = ((values.rolling(horizon + 1).count().shift(-horizon) == horizon + 1)
                 & (gaps.rolling(horizon).max().shift(-horizon) <= spec.max_gap_days))
    y[~target_ok.to_numpy()] = np.nan
    feature_ok = np.isfinite(x).all(axis=1)
    scale = np.maximum(x[:, 3] * math.sqrt(horizon), 1.0)
    indices = np.arange(n)
    dated = [str(d.date()) for d in panel.index]
    rows, state, last_fit = [], None, -spec.refit_every
    for i in range(n):
        if not feature_ok[i]:
            continue
        if state is None or i - last_fit >= spec.refit_every:
            matured = np.flatnonzero(feature_ok & np.isfinite(y) & (indices + horizon < i))
            calibration = matured[-spec.calibration_max:]
            if len(calibration) < spec.calibration_min:
                continue
            fit = matured[matured + horizon < calibration[0]][-spec.train_max:]
            if len(fit) < spec.train_min:
                continue
            base_fit = _ridge(x[fit, :6], y[fit], spec.ridge_penalty)
            real_fit = _ridge(x[fit], y[fit], spec.ridge_penalty)
            predictors = {
                'no_change': lambda a: np.zeros(len(a)),
                'momentum_5': lambda a: a[:, 0] * horizon / 5,
                'ridge_curve': lambda a, p=base_fit: p(a[:, :6]),
                'ridge_curve_real': real_fit,
            }
            residuals = {key: (y[calibration] - predict(x[calibration])) / scale[calibration]
                         for key, predict in predictors.items()}
            state = (predictors, residuals, fit, calibration)
            last_fit = i
        predictors, residuals, fit, calibration = state
        threshold = max(spec.jump_floor_bp, spec.jump_sigma * scale[i])
        for key, predict in predictors.items():
            point = float(predict(x[i:i + 1])[0])
            samples = point + residuals[key] * scale[i]
            denominator = len(samples) + 3
            up = float((np.sum(samples > spec.flat_band_bp) + 1) / denominator)
            down = float((np.sum(samples < -spec.flat_band_bp) + 1) / denominator)
            rows.append({
                'origin': dated[i], 'origin_position': i,
                'target_end': dated[i + horizon] if i + horizon < n else None,
                'target_end_position': i + horizon, 'tenor': tenor, 'horizon': horizon,
                'horizon_basis': 'DGS10_observed_date_intervals_not_certified_sessions',
                'model': key, 'forecast_bp': point,
                'lower_bp': float(np.quantile(samples, 0.1)),
                'upper_bp': float(np.quantile(samples, 0.9)),
                'p_up': up, 'p_down': down, 'p_flat': 1.0 - up - down,
                'p_jump_up': float((np.sum(samples > threshold) + 1) / denominator),
                'p_jump_down': float((np.sum(samples < -threshold) + 1) / denominator),
                'jump_threshold_bp': float(threshold),
                'observed_change_bp': float(y[i]) if np.isfinite(y[i]) else None,
                'fit_start': dated[fit[0]], 'fit_target_end': dated[fit[-1] + horizon],
                'calibration_start': dated[calibration[0]],
                'calibration_target_end': dated[calibration[-1] + horizon],
                'fit_n': int(len(fit)), 'calibration_n': int(len(calibration)),
                'fit_origin': dated[last_fit], 'forecast_available_at': None,
                'historical_availability_qualified': False, 'authority': False,
            })
    return {'schema': 'ric.rates_direction.research.v1',
            'evidence_tier': 'corrected_history_chronological_research_only',
            'settings': asdict(spec), 'authority': False, 'can_rank': False, 'can_gate': False,
            'can_size': False, 'can_trade': False, 'rows': rows,
            'coverage': {'source_grid_rows': n,
                         'eligible_feature_origins': int(feature_ok.sum()),
                         'matured_qualified_targets': int(np.isfinite(y).sum()),
                         'forecast_origins': len(rows) // len(MODELS),
                         'missing_values_by_series': {k: int(panel[k].isna().sum()) for k in panel},
                         'source_gaps_gt_limit': int((gaps > spec.max_gap_days).sum())},
            'limitations': ['Date labels and hashes do not certify historical knowledge.',
                           'No transaction-cost or executable-instrument backtest.',
                           'Common-panel diagnostics abstain when real-rate inputs are absent.',
                           'Intervals are empirical calibration estimates, not coverage guarantees.',
                           'Daily overlapping origins are not independent episodes.']}


def summarize(result: dict, *, start: str, end: str) -> dict:
    """Use incumbent HAC math; report every model, including losing baselines."""
    selected = [r for r in result['rows'] if start <= r['origin'] <= end
                and r['target_end'] is not None and r['target_end'] <= end
                and r['observed_change_bp'] is not None]
    out = {'period': [start, end], 'models': {}, 'authority': False,
           'promotion': 'withheld', 'paired_ridge_vs_no_change': {'n': 0},
           'inference_limit': 'HAC is diagnostic; no selection-adjusted promotion claim.'}
    groups = {key: [r for r in selected if r['model'] == key] for key in MODELS}
    for key, group in groups.items():
        if not group:
            out['models'][key] = {'n': 0, 'status': 'insufficient_qualified_history'}
            continue
        y = np.array([r['observed_change_bp'] for r in group])
        predicted = np.array([r['forecast_bp'] for r in group])
        probabilities = np.array([[r['p_down'], r['p_flat'], r['p_up']] for r in group])
        band = result['settings']['flat_band_bp']
        classes = np.where(y > band, 2, np.where(y < -band, 0, 1))
        jump = np.abs(y) > np.array([r['jump_threshold_bp'] for r in group])
        jump_p = np.array([r['p_jump_up'] + r['p_jump_down'] for r in group])
        alerts, true_alerts = jump_p >= 0.5, (jump_p >= 0.5) & jump
        nonoverlap, next_origin = 0, -1
        for row in group:
            if row['origin_position'] >= next_origin:
                nonoverlap += 1
                next_origin = row['target_end_position']
        out['models'][key] = {
            'n': len(group), 'nonoverlapping_windows': nonoverlap,
            'mse_bp2': float(np.mean((predicted - y) ** 2)),
            'mae_bp': float(np.mean(np.abs(predicted - y))),
            'interval_80_coverage': float(np.mean([(r['lower_bp'] <= value <= r['upper_bp'])
                                                  for r, value in zip(group, y)])),
            'interval_80_mean_width_bp': float(np.mean([r['upper_bp'] - r['lower_bp'] for r in group])),
            'direction_brier': float(np.mean(np.sum((probabilities - np.eye(3)[classes]) ** 2, axis=1))),
            'direction_log_loss': float(-np.mean(np.log(np.maximum(probabilities[np.arange(len(y)), classes], 1e-12)))),
            'jump_brier': float(np.mean((jump_p - jump) ** 2)),
            'jump_events': int(jump.sum()), 'jump_alerts': int(alerts.sum()),
            'false_alert_fraction': float((alerts & ~jump).sum() / alerts.sum()) if alerts.any() else None,
            'jump_recall': float(true_alerts.sum() / jump.sum()) if jump.any() else None,
        }
    challenger = groups['ridge_curve_real']
    if challenger:
        for baseline in ('no_change', 'momentum_5', 'ridge_curve'):
            comparison = groups[baseline]
            if [r['origin'] for r in comparison] != [r['origin'] for r in challenger]:
                raise ValueError('comparison panels do not match')
            loss_delta = [(b['observed_change_bp'] - b['forecast_bp']) ** 2
                          - (r['observed_change_bp'] - r['forecast_bp']) ** 2
                          for b, r in zip(comparison, challenger)]
            out['paired_ridge_vs_' + baseline] = newey_west_tstat(
                loss_delta, lags=max(20, 2 * challenger[0]['horizon']))
            base_mse = out['models'][baseline]['mse_bp2']
            out['paired_ridge_vs_' + baseline]['relative_mse_reduction'] = (
                float(np.mean(loss_delta) / base_mse) if base_mse > 0 else None)
    return out
