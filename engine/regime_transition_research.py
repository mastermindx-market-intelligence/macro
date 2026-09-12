"""Research estimators downstream of Regime One; never a replacement classifier.

The caller supplies the EXISTING owner's dated categorical target and feature panel.
This module owns no source, label, ledger, scheduler, risk score or capital policy.
All estimators are experimental until evaluated on an admissible point-in-time panel.

Three distinct objects are returned: future-date state occupancy, first-exit
survival, and probability of ever visiting each state. Duration-sensitive
propagation is exact conditional on the supplied feature trajectory. Marginal
forecasts integrate that calculation over reproducible bootstrap VAR trajectories.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import hashlib
import json
import math
import re
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp

SCHEMA = "regime_one.transition_research.v1"
METHOD = "regularized_tvtp_duration_var_bootstrap_v1"
STATES = ("Q1", "Q2", "Q3", "Q4")
BASES = ("RELEASE_VINTAGE_ATTESTED", "LATEST_REVISED_EXPLORATORY", "SYNTHETIC_SOFTWARE_TEST")
AUTHORITY = {"can_rank": False, "can_gate": False, "can_size": False,
             "can_trade": False, "can_originate_signal": False, "can_execute": False}


class PanelError(ValueError):
    """An invalid panel is not an economic state or a missing-data forecast."""


def month_number(value: str) -> int:
    if not isinstance(value, str) or re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", value) is None:
        raise PanelError("Periods must have exact YYYY-MM month precision")
    year, month = map(int, value.split("-"))
    if not 1 <= year <= 9999:
        raise PanelError("Year outside supported range")
    return year * 12 + month - 1


def month_after(value: str, offset: int) -> str:
    if isinstance(offset, bool) or not isinstance(offset, (int, np.integer)) or offset < 0:
        raise PanelError("Month offset must be a nonnegative integer")
    year, month0 = divmod(month_number(value) + int(offset), 12)
    if not 1 <= year <= 9999:
        raise PanelError("Forecast target outside supported calendar")
    return f"{year:04d}-{month0 + 1:02d}"


def _matrix(value: Any, *, name: str, allow_nan: bool = True) -> np.ndarray:
    raw = np.asarray(value, dtype=object) if not isinstance(value, np.ndarray) else value
    if raw.ndim != 2 or raw.dtype.kind == "b":
        raise PanelError(f"{name} must be a two-dimensional numeric matrix, not booleans")
    if raw.dtype.kind not in "fi":
        # Object arrays need this check before coercion: True is numerically 1.0.
        if any(isinstance(v, (bool, np.bool_)) for v in raw.ravel()):
            raise PanelError(f"{name} contains booleans")
    try:
        x = np.asarray(value, dtype=float).copy()
    except (ValueError, TypeError, OverflowError) as exc:
        raise PanelError(f"{name} is not numeric") from exc
    if np.isinf(x).any() or (not allow_nan and np.isnan(x).any()):
        raise PanelError(f"{name} contains non-finite values")
    return x


def _digest(value: Mapping[str, Any]) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class MonthlyPanel:
    """A finite monthly research input, with source limitations retained.

    Periods are closed month identities, not a claim of release availability.
    Attested mode additionally requires a knowable-at month for EVERY present
    feature and target. Exact source receipts are caller-owned and mandatory.
    Latest-revised panels may be studied but never become PIT-certified here.
    """
    periods: tuple[str, ...]
    values: np.ndarray
    labels: tuple[str | None, ...]
    feature_names: tuple[str, ...]
    target_name: str
    source_basis: str
    source_receipts: tuple[str, ...]
    feature_known_at: np.ndarray | None = None
    target_known_at: tuple[str | None, ...] | None = None
    states: tuple[str, ...] = STATES

    def __post_init__(self) -> None:
        periods = tuple(self.periods)
        numbers = np.array([month_number(p) for p in periods], dtype=np.int64)
        if not len(periods) or np.any(np.diff(numbers) <= 0):
            raise PanelError("Periods must be nonempty, unique and strictly increasing")
        names, states = tuple(self.feature_names), tuple(self.states)
        if not names or len(set(names)) != len(names) or not all(isinstance(x, str) and x for x in names):
            raise PanelError("Feature identities must be unique nonempty strings")
        if len(states) < 2 or len(set(states)) != len(states) or not all(isinstance(s, str) and s for s in states):
            raise PanelError("At least two unique target states are required")
        x = _matrix(self.values, name="values")
        if x.shape != (len(periods), len(names)) or len(self.labels) != len(periods):
            raise PanelError("Panel dimensions disagree")
        labels = tuple(self.labels)
        if any(v is not None and v not in states for v in labels):
            raise PanelError("Unknown target label; do not silently add a fifth state")
        if self.source_basis not in BASES or not self.target_name:
            raise PanelError("Explicit target and source basis are required")
        if not self.source_receipts or not all(isinstance(v, str) and v for v in self.source_receipts):
            raise PanelError("Actual source receipt identities are required")
        known = None
        if self.feature_known_at is not None:
            known = np.asarray(self.feature_known_at, dtype=object).copy()
            if known.shape != x.shape:
                raise PanelError("Feature availability dimensions disagree")
        target_known = None if self.target_known_at is None else tuple(self.target_known_at)
        if target_known is not None and len(target_known) != len(periods):
            raise PanelError("Target availability dimensions disagree")
        if self.source_basis == "RELEASE_VINTAGE_ATTESTED":
            if known is None or target_known is None:
                raise PanelError("Attested mode requires feature and target availability receipts")
            for i, period_num in enumerate(numbers):
                for j in range(x.shape[1]):
                    if np.isfinite(x[i, j]) and month_number(known[i, j]) > period_num:
                        raise PanelError("A feature was not yet available at its historical origin")
                if labels[i] is not None and month_number(target_known[i]) > period_num:
                    raise PanelError("A target was not yet available at its historical origin")
        x.setflags(write=False)
        if known is not None:
            known.setflags(write=False)
        object.__setattr__(self, "periods", periods)
        object.__setattr__(self, "feature_names", names)
        object.__setattr__(self, "states", states)
        object.__setattr__(self, "source_receipts", tuple(self.source_receipts))
        object.__setattr__(self, "values", x)
        object.__setattr__(self, "labels", labels)
        object.__setattr__(self, "feature_known_at", known)
        object.__setattr__(self, "target_known_at", target_known)

    def through(self, index: int) -> "MonthlyPanel":
        if isinstance(index, bool) or not 0 <= index < len(self.periods):
            raise PanelError("Training cutoff outside panel")
        end = int(index) + 1
        return MonthlyPanel(self.periods[:end], self.values[:end], self.labels[:end],
                            self.feature_names, self.target_name, self.source_basis,
                            self.source_receipts,
                            None if self.feature_known_at is None else self.feature_known_at[:end],
                            None if self.target_known_at is None else self.target_known_at[:end],
                            self.states)

    @property
    def fingerprint(self) -> str:
        return _digest({"periods": self.periods, "values": [
            [None if np.isnan(v) else float(v) for v in row] for row in self.values],
            "labels": self.labels, "feature_names": self.feature_names,
            "target_name": self.target_name, "source_basis": self.source_basis,
            "source_receipts": self.source_receipts,
            "feature_known_at": None if self.feature_known_at is None else self.feature_known_at.tolist(),
            "target_known_at": self.target_known_at, "states": self.states})


def observed_durations(panel: MonthlyPanel) -> tuple[np.ndarray, np.ndarray]:
    """Do not bridge a missing month/label, or call a left-censored spell complete."""
    durations = np.zeros(len(panel.periods), dtype=int)
    exact = np.zeros(len(panel.periods), dtype=bool)
    months = [month_number(p) for p in panel.periods]
    for i, label in enumerate(panel.labels):
        if label is None:
            continue
        contiguous = i > 0 and months[i] == months[i - 1] + 1 and panel.labels[i - 1] is not None
        if contiguous and label == panel.labels[i - 1]:
            durations[i] = durations[i - 1] + 1
            exact[i] = exact[i - 1]
        else:
            durations[i] = 1
            exact[i] = bool(contiguous)
    return durations, exact


@dataclass(frozen=True)
class FitConfig:
    prior_strength: float = 4.0
    ridge: float = 8.0
    min_source_transitions: int = 24
    min_exits: int = 4
    min_feature_coverage: float = 0.60
    max_iterations: int = 300
    duration_sensitive: bool = True
    feature_clip: float = 6.0

    def __post_init__(self) -> None:
        if not math.isfinite(self.prior_strength) or self.prior_strength <= 0:
            raise PanelError("Positive finite prior strength is required")
        if not math.isfinite(self.ridge) or self.ridge <= 0:
            raise PanelError("Positive finite regularization is required")
        if not 0 < self.min_feature_coverage <= 1:
            raise PanelError("Feature coverage must be in (0, 1]")
        for value in (self.min_source_transitions, self.min_exits, self.max_iterations):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise PanelError("Fit counts must be positive integers")
        if not math.isfinite(self.feature_clip) or self.feature_clip <= 0:
            raise PanelError("Feature clipping bound must be positive")


@dataclass
class TransitionModel:
    """Regularized state-dependent multinomial transition model.

    The empirical matrix is always retained. Sparse source states fall back to
    a globally-shrunk empirical row; nonconverged fits are not accepted silently.
    Feature selection is fixed by caller, preprocessing is training-only.
    """
    states: tuple[str, ...]
    feature_names: tuple[str, ...]
    median: np.ndarray
    scale: np.ndarray
    feature_seen: np.ndarray
    duration_center: float
    duration_scale: float
    empirical: np.ndarray
    unconditional: np.ndarray
    coefficients: list[np.ndarray | None]
    row_evidence: list[dict[str, Any]]
    config: FitConfig
    training_period: str
    training_fingerprint: str
    target_name: str
    source_basis: str
    source_receipts: tuple[str, ...]

    def _design(self, values: np.ndarray, durations: np.ndarray) -> np.ndarray:
        x = _matrix(values, name="forecast features")
        if x.shape[1] != len(self.feature_names):
            raise PanelError("Forecast feature order/dimensions differ from training")
        ages = np.asarray(durations, dtype=float)
        if ages.shape != (len(x),) or not np.isfinite(ages).all() or (ages < 1).any():
            raise PanelError("Positive finite observed durations are required")
        missing = np.isnan(x)
        filled = np.where(missing, self.median, x)
        z = np.clip((filled - self.median) / self.scale,
                    -self.config.feature_clip, self.config.feature_clip)
        z[:, ~self.feature_seen] = 0
        # Missingness is explicit. It does not become a zero-valued observation.
        parts = [np.ones((len(x), 1)), z, missing.astype(float)]
        if self.config.duration_sensitive:
            age_z = (np.log1p(ages) - self.duration_center) / self.duration_scale
            parts.append(np.clip(age_z, -self.config.feature_clip,
                                 self.config.feature_clip).reshape(-1, 1))
        return np.concatenate(parts, axis=1)

    def row(self, state_index: int, values: Sequence[float], durations: np.ndarray,
            *, empirical_only: bool = False) -> np.ndarray:
        if not 0 <= state_index < len(self.states):
            raise PanelError("Unknown origin state")
        x = _matrix([values], name="forecast feature row")
        if x.shape[1] != len(self.feature_names):
            raise PanelError("Forecast feature dimensions disagree")
        seen_n = int(self.feature_seen.sum())
        coverage = float(np.isfinite(x[:, self.feature_seen]).sum()) / max(1, seen_n)
        if not empirical_only and (seen_n == 0 or coverage < self.config.min_feature_coverage):
            raise PanelError("INSUFFICIENT_CURRENT_FEATURE_COVERAGE")
        ages = np.asarray(durations)
        if ages.ndim != 1 or ages.dtype.kind == "b" or not np.isfinite(ages).all() or (ages < 1).any():
            raise PanelError("Positive finite observed durations are required")
        coef = self.coefficients[state_index]
        if empirical_only or coef is None:
            return np.tile(self.empirical[state_index], (len(ages), 1))
        design = self._design(np.repeat(x, len(ages), axis=0), ages)
        logits = design @ coef
        probs = np.exp(logits - logsumexp(logits, axis=1, keepdims=True))
        if not np.isfinite(probs).all():
            raise PanelError("Non-finite transition probability")
        return probs

    def receipt(self) -> dict[str, Any]:
        return {"method": METHOD, "target_name": self.target_name,
                "states": list(self.states), "step_unit": "calendar_month",
                "feature_names": list(self.feature_names),
                "training_through": self.training_period,
                "training_fingerprint": self.training_fingerprint,
                "source_basis": self.source_basis,
                "source_receipts": list(self.source_receipts),
                "row_evidence": self.row_evidence,
                "authority": dict(AUTHORITY), "status": "EXPERIMENTAL",
                "pit_certified_by_model": False,
                "empirical_matrix": self.empirical.tolist(),
                "preprocessing": {"center": "training_median", "scale": "training_MAD_or_std",
                                  "missing_indicators": True, "clip": self.config.feature_clip}}


def fit_transition_model(panel: MonthlyPanel, config: FitConfig | None = None) -> TransitionModel:
    cfg = config or FitConfig()
    x, n, d, k = panel.values, len(panel.periods), len(panel.feature_names), len(panel.states)
    if n < 3:
        raise PanelError("At least three monthly rows are required")
    y = np.array([-1 if v is None else panel.states.index(v) for v in panel.labels], dtype=int)
    months = np.array([month_number(p) for p in panel.periods])
    adjacent = np.diff(months) == 1
    origins = np.flatnonzero(adjacent & (y[:-1] >= 0) & (y[1:] >= 0))
    if not len(origins):
        raise PanelError("No adjacent observed transitions")
    durations, duration_exact = observed_durations(panel)
    observed = np.isfinite(x[origins])
    feature_seen = observed.any(axis=0)
    median, scale = np.zeros(d), np.ones(d)
    for j in np.flatnonzero(feature_seen):
        values = x[origins, j][observed[:, j]]
        median[j] = np.median(values)
        mad = 1.4826 * float(np.median(np.abs(values - median[j])))
        std = float(np.std(values))
        scale[j] = mad if mad > 1e-10 else std if std > 1e-10 else 1.0
    counts = np.zeros((k, k), dtype=float)
    np.add.at(counts, (y[origins], y[origins + 1]), 1.0)
    state_counts = np.bincount(y[y >= 0], minlength=k).astype(float)
    global_probs = (state_counts + 0.5) / (state_counts.sum() + 0.5 * k)
    empirical = (counts + cfg.prior_strength * global_probs[None, :]) / (
        counts.sum(axis=1, keepdims=True) + cfg.prior_strength)
    age_values = np.log1p(durations[origins][duration_exact[origins]])
    age_center = float(np.median(age_values)) if len(age_values) else 0.0
    age_scale = max(float(np.std(age_values)), 1.0) if len(age_values) else 1.0
    model = TransitionModel(panel.states, panel.feature_names, median, scale, feature_seen,
                            age_center, age_scale, empirical, global_probs, [None] * k, [], cfg,
                            panel.periods[-1], panel.fingerprint, panel.target_name,
                            panel.source_basis, panel.source_receipts)
    for state in range(k):
        idx = origins[y[origins] == state]
        raw_n = len(idx)
        left_censored = int((~duration_exact[idx]).sum())
        if cfg.duration_sensitive:
            idx = idx[duration_exact[idx]]
        cover = np.isfinite(x[idx][:, feature_seen]).sum(axis=1) / max(1, int(feature_seen.sum()))
        idx = idx[cover >= cfg.min_feature_coverage]
        exits = int((y[idx + 1] != state).sum())
        receipt: dict[str, Any] = {"source_state": panel.states[state],
            "observed_transitions": raw_n, "fit_transitions": len(idx), "exits": exits,
            "left_censored_rows": left_censored, "fit_status": "SHRUNK_EMPIRICAL_FALLBACK"}
        if len(idx) < cfg.min_source_transitions or exits < cfg.min_exits or len(np.unique(y[idx + 1])) < 2:
            receipt["reason"] = "insufficient_source_state_or_exit_samples"
            model.row_evidence.append(receipt)
            continue
        design = model._design(x[idx], durations[idx])
        target = np.eye(k)[y[idx + 1]]
        prior_logits = np.log(empirical[state])
        prior_logits -= prior_logits.mean()
        anchor = np.zeros((design.shape[1], k))
        anchor[0] = prior_logits
        penalty = np.full_like(anchor, cfg.ridge)
        penalty[0] = cfg.prior_strength

        def objective(flat: np.ndarray) -> tuple[float, np.ndarray]:
            coef = flat.reshape(anchor.shape)
            logits = design @ coef
            log_probs = logits - logsumexp(logits, axis=1, keepdims=True)
            delta = coef - anchor
            loss = -float((target * log_probs).sum()) + 0.5 * float((penalty * delta * delta).sum())
            gradient = design.T @ (np.exp(log_probs) - target) + penalty * delta
            return loss, gradient.ravel()

        fit = minimize(objective, anchor.ravel(), jac=True, method="L-BFGS-B",
                       options={"maxiter": cfg.max_iterations, "ftol": 1e-10, "gtol": 1e-6})
        if fit.success and np.isfinite(fit.x).all() and np.isfinite(fit.fun):
            model.coefficients[state] = fit.x.reshape(anchor.shape)
            receipt.update(fit_status="FITTED", iterations=int(fit.nit), objective=float(fit.fun))
        else:
            receipt["reason"] = "optimizer_did_not_converge"
            receipt["optimizer_status"] = int(fit.status)
        model.row_evidence.append(receipt)
    return model


def propagate(model: TransitionModel, initial_state: str, initial_duration: int,
              feature_path: np.ndarray, *, empirical_only: bool = False,
              duration_is_lower_bound: bool = False) -> dict[str, Any]:
    """Exact finite-horizon state/duration recursion conditional on covariates.

    feature_path[t] is the evidence assumed available BEFORE transition t -> t+1.
    'Ever visited' includes the origin. 'First exit' means exit from the origin
    spell, not simply occupying a different state at the horizon.
    """
    path = _matrix(feature_path, name="conditional feature path")
    if len(path) < 1 or len(path) > 120 or path.shape[1] != len(model.feature_names):
        raise PanelError("Conditional path needs 1..120 month rows in training feature order")
    if initial_state not in model.states or isinstance(initial_duration, bool) or not isinstance(initial_duration, (int, np.integer)) or initial_duration < 1:
        raise PanelError("Origin state and positive integer duration are required")
    if initial_duration > 1200:
        raise PanelError("Unreasonable observed regime duration")
    k, origin, horizon = len(model.states), model.states.index(initial_state), len(path)
    max_age = initial_duration + horizon
    joint = np.zeros((k, max_age + 1))
    joint[origin, initial_duration] = 1.0
    # One killed chain per target state retains only paths which never visited it.
    killed = np.repeat(joint[None, :, :], k, axis=0)
    killed[origin] = 0.0
    survival, expected_transitions = 1.0, 0.0
    survival_sum = 0.0
    results = []
    ages = np.arange(1, max_age + 1)
    for step, features in enumerate(path, start=1):
        transitions = np.stack([model.row(s, features, ages, empirical_only=empirical_only) for s in range(k)])
        if duration_is_lower_bound and not empirical_only:
            # A censored origin spell has unknown true age. Do not substitute
            # its observed lower bound into a fitted duration hazard as exact.
            # Its unique no-exit mass uses the empirical row until first exit;
            # subsequent spells have known age and use the conditional model.
            unknown_age = initial_duration + step - 2
            transitions[origin, unknown_age] = model.row(origin, features, np.array([1]), empirical_only=True)[0]
        next_joint = np.zeros_like(joint)
        next_killed = np.zeros_like(killed)
        for source in range(k):
            mass = joint[source, 1:]
            expected_transitions += float((mass * (1 - transitions[source, :, source])).sum())
            for destination in range(k):
                weighted = mass * transitions[source, :, destination]
                kmass = killed[:, source, 1:] * transitions[source, :, destination][None, :]
                if destination == source:
                    # At this step no mass can occupy the last storage age.
                    next_joint[destination, 2:] += weighted[:-1]
                    next_killed[:, destination, 2:] += kmass[:, :-1]
                else:
                    next_joint[destination, 1] += weighted.sum()
                    next_killed[:, destination, 1] += kmass.sum(axis=1)
        for target in range(k):
            next_killed[target, target] = 0
        previous_survival = survival
        survival_sum += previous_survival
        survival *= float(transitions[origin, initial_duration + step - 2, origin])
        joint, killed = next_joint, next_killed
        total = float(joint.sum())
        if not np.isfinite(total) or abs(total - 1.0) > 1e-9:
            raise PanelError("State/duration probability mass was not conserved")
        occupancy = joint.sum(axis=1)
        ever = np.clip(1.0 - killed.sum(axis=(1, 2)), 0.0, 1.0)
        results.append({"horizon_months": step,
            "target_period": month_after(model.training_period, step),
            "occupancy": dict(zip(model.states, map(float, occupancy))),
            "ever_visited_including_origin": dict(zip(model.states, map(float, ever))),
            "origin_spell_survival": float(survival),
            "first_exit_by_horizon": float(1.0 - survival),
            "first_exit_during_step": float(previous_survival - survival),
            "expected_transitions_by_horizon": float(expected_transitions),
            "restricted_mean_steps_to_first_exit": float(survival_sum),
            "expected_observed_duration_at_horizon": float((joint * np.arange(max_age + 1)).sum())})
    return {"schema": SCHEMA, "kind": "CONDITIONAL_TRAJECTORY",
            "origin_period": model.training_period, "initial_state": initial_state,
            "initial_observed_duration_months": int(initial_duration),
            "duration_is_lower_bound": bool(duration_is_lower_bound),
            "origin_spell_method": "empirical_until_first_exit" if duration_is_lower_bound else "conditional_observed_duration",
            "assumption": "provided_covariates_before_each_transition",
            "fit": model.receipt(), "horizons": results, "authority": dict(AUTHORITY)}


# Domain links are declared only for the named, unit-bound owner features.
# They are not a winsorization of outcomes or a macro judgement. A transformed
# VAR cannot create a claims/price-index change below -100% or an axis outside
# its owner's [-1, 1] support. Exact axis endpoints use a disclosed epsilon.
_AXIS_FEATURES = frozenset(("growth_score", "inflation_score"))
_RATIO_FEATURES = frozenset(("broad_usd_3m_pct", "claims_yoy_pct",
                            "core_pce_3m_annualized_pct", "oil_3m_pct"))
_LINK_EPS = 1e-6


def _feature_links(names: Sequence[str]) -> tuple[str, ...]:
    return tuple("atanh_owner_axis" if n in _AXIS_FEATURES else
                 "log1p_percent_ratio" if n in _RATIO_FEATURES else "identity" for n in names)


def _link_features(values: np.ndarray, links: Sequence[str], *, inverse: bool = False) -> np.ndarray:
    output = np.array(values, dtype=float, copy=True)
    for j, link in enumerate(links):
        v = output[..., j]
        finite = np.isfinite(v)
        if link == "atanh_owner_axis":
            if inverse:
                output[..., j] = np.tanh(v)
            else:
                if np.any(np.abs(v[finite]) > 1):
                    raise PanelError("Owner axis outside declared [-1, 1] support")
                output[..., j] = np.arctanh(np.clip(v, -1 + _LINK_EPS, 1 - _LINK_EPS))
        elif link == "log1p_percent_ratio":
            if inverse:
                with np.errstate(over="ignore", invalid="ignore"):
                    output[..., j] = 100 * np.expm1(v)
            else:
                if np.any(v[finite] <= -100):
                    raise PanelError("Percentage ratio outside declared greater-than -100 support")
                output[..., j] = np.log1p(v / 100)
        elif link != "identity":
            raise PanelError("Unknown feature-domain link")
    return output


@dataclass
class JointFeatureVAR:
    """Training-only ridge VAR for coherent conditioning-variable trajectories.

    This is a research distribution, not a structural causal model. Residual
    block resampling preserves within-month covariance and some serial dependence.
    Spectral shrinkage is disclosed. Parameter uncertainty is NOT covered.
    Caller-selected features must have the correct stationary/level construction.
    """
    feature_names: tuple[str, ...]
    center: np.ndarray
    scale: np.ndarray
    coefficients: np.ndarray
    intercept: np.ndarray
    residuals: np.ndarray
    residual_origin_months: np.ndarray
    fitted_pairs: int
    spectral_radius_before: float
    spectral_radius_after: float
    ridge: float
    training_period: str
    training_fingerprint: str
    domain_links: tuple[str, ...] = ()

    def simulate(self, initial_values: Sequence[float], horizon: int, *, paths: int = 128,
                 block_months: int = 3, seed: int = 20260912) -> np.ndarray:
        if any(isinstance(v, bool) or not isinstance(v, int) or v < 1 for v in (horizon, paths, block_months)):
            raise PanelError("Positive integer simulation dimensions required")
        if horizon > 120 or paths > 4096 or block_months > 24:
            raise PanelError("Simulation exceeds bounded research budget")
        x0 = _matrix([initial_values], name="VAR initial state", allow_nan=False)[0]
        if len(x0) != len(self.feature_names):
            raise PanelError("VAR initial feature dimensions disagree")
        # A block cannot jump across a missing month in the training sample.
        starts = [i for i in range(len(self.residuals) - block_months + 1)
                  if np.all(np.diff(self.residual_origin_months[i:i + block_months]) == 1)]
        if not starts:
            raise PanelError("No complete residual block for requested resampling length")
        rng = np.random.default_rng(seed)
        output = np.empty((paths, horizon, len(x0)))
        linked = _link_features(x0[None, :], self.domain_links)[0]
        z = np.repeat(((linked - self.center) / self.scale)[None, :], paths, axis=0)
        for block_start in range(0, horizon, block_months):
            sampled = rng.choice(starts, size=paths, replace=True)
            for offset in range(min(block_months, horizon - block_start)):
                z = self.intercept + z @ self.coefficients + self.residuals[sampled + offset]
                values = _link_features(z * self.scale + self.center, self.domain_links, inverse=True)
                if not np.isfinite(values).all():
                    raise PanelError("Non-finite feature path; no silent clipping")
                output[:, block_start + offset] = values
        return output

    def receipt(self) -> dict[str, Any]:
        return {"method": "ridge_VAR1_residual_block_bootstrap_v1",
            "training_through": self.training_period, "training_fingerprint": self.training_fingerprint,
            "fitted_adjacent_complete_pairs": self.fitted_pairs,
            "spectral_radius_before": self.spectral_radius_before,
            "spectral_radius_after": self.spectral_radius_after,
            "ridge": self.ridge, "parameter_uncertainty_included": False,
            "structurally_identified": False,
            "domain_links": dict(zip(self.feature_names, self.domain_links)),
            "axis_endpoint_epsilon": _LINK_EPS}


def fit_joint_feature_var(panel: MonthlyPanel, *, ridge: float = 8.0,
                          min_pairs: int = 60, max_radius: float = 0.98) -> JointFeatureVAR:
    if not math.isfinite(ridge) or ridge <= 0 or not 0 < max_radius < 1:
        raise PanelError("VAR regularization and stability bounds are invalid")
    if isinstance(min_pairs, bool) or not isinstance(min_pairs, int) or min_pairs < 3:
        raise PanelError("VAR minimum sample must be at least three pairs")
    links = _feature_links(panel.feature_names)
    x = _link_features(panel.values, links)
    months = np.array([month_number(p) for p in panel.periods])
    complete = np.isfinite(x).all(axis=1)
    origins = np.flatnonzero((np.diff(months) == 1) & complete[:-1] & complete[1:])
    if len(origins) < max(min_pairs, x.shape[1] + 2):
        raise PanelError("INSUFFICIENT_COMPLETE_ADJACENT_VAR_PAIRS")
    # Fit center/scale only on training origins, not on test/future rows.
    center = x[origins].mean(axis=0)
    scale = x[origins].std(axis=0)
    scale = np.where(scale > 1e-10, scale, 1.0)
    a, b = (x[origins] - center) / scale, (x[origins + 1] - center) / scale
    coefficients = np.linalg.solve(a.T @ a + ridge * np.eye(a.shape[1]), a.T @ b)
    radius_before = float(np.max(np.abs(np.linalg.eigvals(coefficients))))
    if radius_before > max_radius:
        coefficients *= max_radius / radius_before
    radius_after = float(np.max(np.abs(np.linalg.eigvals(coefficients))))
    intercept = (b - a @ coefficients).mean(axis=0)
    residuals = b - intercept - a @ coefficients
    residuals -= residuals.mean(axis=0)
    return JointFeatureVAR(panel.feature_names, center, scale, coefficients, intercept,
                          residuals, months[origins], len(origins), radius_before, radius_after,
                          ridge, panel.periods[-1], panel.fingerprint, links)


def forecast_ensemble(model: TransitionModel, var: JointFeatureVAR, panel: MonthlyPanel,
                      *, horizons: tuple[int, ...] = (1, 3, 6, 12), paths: int = 128,
                      seed: int = 20260912, block_months: int = 3) -> dict[str, Any]:
    if model.training_fingerprint != panel.fingerprint or var.training_fingerprint != panel.fingerprint:
        raise PanelError("Model/VAR/panel training generations differ")
    if not horizons or tuple(sorted(set(horizons))) != horizons or any(isinstance(h, bool) or not isinstance(h, int) or h < 1 for h in horizons):
        raise PanelError("Horizons must be sorted distinct positive month counts")
    state = panel.labels[-1]
    if state is None:
        raise PanelError("Current target label unavailable")
    durations, exact = observed_durations(panel)
    h = max(horizons)
    future = var.simulate(panel.values[-1], h, paths=paths, seed=seed, block_months=block_months)
    # The first transition conditions on information at the forecast origin.
    # Drawn future values start conditioning transitions only one step later.
    conditioning = np.concatenate([np.repeat(panel.values[-1][None, None, :], paths, axis=0), future[:, :-1]], axis=1)
    projections = [propagate(model, state, int(durations[-1]), p,
                             duration_is_lower_bound=not bool(exact[-1])) for p in conditioning]
    result = []
    for horizon in horizons:
        cells = [p["horizons"][horizon - 1] for p in projections]
        probabilities = np.array([[c["occupancy"][s] for s in model.states] for c in cells])
        ever = np.array([[c["ever_visited_including_origin"][s] for s in model.states] for c in cells])
        features = future[:, horizon - 1]
        result.append({"horizon_months": horizon, "target_period": month_after(panel.periods[-1], horizon),
            "occupancy": dict(zip(model.states, map(float, probabilities.mean(axis=0)))),
            "conditioning_probability_dispersion": {
                s: {"p10": float(np.quantile(probabilities[:, j], .1)),
                    "p90": float(np.quantile(probabilities[:, j], .9))} for j, s in enumerate(model.states)},
            "ever_visited_including_origin": dict(zip(model.states, map(float, ever.mean(axis=0)))),
            "first_exit_by_horizon": float(np.mean([c["first_exit_by_horizon"] for c in cells])),
            "expected_transitions_by_horizon": float(np.mean([c["expected_transitions_by_horizon"] for c in cells])),
            "restricted_mean_steps_to_first_exit": float(np.mean([c["restricted_mean_steps_to_first_exit"] for c in cells])),
            "conditioning_features": {name: {
                "p10": float(np.quantile(features[:, j], .1)),
                "p50": float(np.quantile(features[:, j], .5)),
                "p90": float(np.quantile(features[:, j], .9))} for j, name in enumerate(panel.feature_names)}})
    return {"schema": SCHEMA, "kind": "EXPERIMENTAL_MODEL_FORECAST",
            "origin_period": panel.periods[-1], "target_name": panel.target_name,
            "initial_state": state, "initial_duration_months": int(durations[-1]),
            "duration_is_lower_bound": not bool(exact[-1]), "fit": model.receipt(),
            "conditioning_model": var.receipt(), "simulation": {
                "paths": paths, "block_months": block_months, "seed": seed,
                "probability_dispersion_is_calibration_interval": False},
            "horizons": result, "authority": dict(AUTHORITY),
            "limitations": ["No capital or signal authority.",
                "Forecasting an operational house label is not proof of forecasting the economy.",
                "Bootstrap intervals require out-of-sample calibration; parameter uncertainty is omitted.",
                "A latest-revised panel is exploratory, not point-in-time forecasting evidence."]}


def probability_scores(probabilities: np.ndarray, targets: Sequence[int]) -> dict[str, float]:
    p = _matrix(probabilities, name="probabilities", allow_nan=False)
    raw = np.asarray(targets)
    if raw.ndim != 1 or len(raw) != len(p) or raw.dtype.kind not in "iu" or raw.dtype.kind == "b":
        raise PanelError("Targets must be one integer class per prediction")
    if not len(p) or (p < 0).any() or (p > 1).any() or not np.allclose(p.sum(axis=1), 1, atol=1e-8):
        raise PanelError("Invalid probability simplex")
    y = raw.astype(int)
    if (y < 0).any() or (y >= p.shape[1]).any():
        raise PanelError("Target outside state vocabulary")
    one_hot = np.eye(p.shape[1])[y]
    selected = p[np.arange(len(y)), y]
    return {"brier": float(np.mean(np.sum((p - one_hot) ** 2, axis=1))),
            "log_loss": float(-np.mean(np.log(np.clip(selected, 1e-12, 1.0)))),
            "log_probability_floor": 1e-12,
            "zero_probability_misses": int((selected == 0).sum()), "n": len(y)}


def paired_block_interval(differences: Sequence[float], *, block_size: int,
                          draws: int = 1000, seed: int = 20260912) -> dict[str, Any]:
    d = np.asarray(differences, dtype=float)
    if d.ndim != 1 or not len(d) or not np.isfinite(d).all():
        raise PanelError("Paired score differences must be finite")
    if any(isinstance(v, bool) or not isinstance(v, int) or v < 1 for v in (block_size, draws)):
        raise PanelError("Bootstrap counts must be positive integers")
    if len(d) < 2 * block_size:
        return {"status": "INSUFFICIENT_BLOCKS", "mean": float(d.mean()),
                "n_forecasts": len(d), "block_size": block_size, "interval": None}
    rng = np.random.default_rng(seed)
    count = math.ceil(len(d) / block_size)
    starts = rng.integers(0, len(d) - block_size + 1, size=(draws, count))
    indices = (starts[..., None] + np.arange(block_size)).reshape(draws, -1)[:, :len(d)]
    means = d[indices].mean(axis=1)
    return {"status": "EXPLORATORY_BLOCK_BOOTSTRAP", "mean": float(d.mean()),
            "n_forecasts": len(d), "block_size": block_size, "draws": draws,
            "interval": [float(np.quantile(means, .025)), float(np.quantile(means, .975))],
            "negative_favors_challenger": True}


def walk_forward(panel: MonthlyPanel, *, min_train_months: int = 120,
                 horizons: tuple[int, ...] = (1, 3, 6, 12), stride: int = 1,
                 paths: int = 64, config: FitConfig | None = None,
                 seed: int = 20260912) -> dict[str, Any]:
    """Expanding-window evaluation with untouched future labels.

    Fits one-step models only on transitions fully observed by each origin.
    Every transform and VAR is re-fitted inside that training window. No
    hyperparameter search is performed. Overlapping outcome windows remain
    dependent; paired block uncertainty and origin counts disclose that fact.
    """
    if any(isinstance(v, bool) or not isinstance(v, int) or v < 1 for v in (min_train_months, stride, paths)):
        raise PanelError("Invalid walk-forward dimensions")
    if not horizons or tuple(sorted(set(horizons))) != horizons or any(isinstance(h, bool) or not isinstance(h, int) or h < 1 for h in horizons):
        raise PanelError("Invalid evaluation horizons")
    months = np.array([month_number(p) for p in panel.periods])
    lookup = {p: i for i, p in enumerate(panel.periods)}
    records, abstentions = [], []
    for origin in range(min_train_months - 1, len(panel.periods) - 1, stride):
        matured = {h: lookup.get(month_after(panel.periods[origin], h)) for h in horizons}
        matured = {h: i for h, i in matured.items() if i is not None and panel.labels[i] is not None}
        if not matured:
            continue
        training = panel.through(origin)
        try:
            model = fit_transition_model(training, config)
            var = fit_joint_feature_var(training)
            pred = forecast_ensemble(model, var, training, horizons=tuple(matured), paths=paths,
                                     seed=seed + origin)
            duration, _ = observed_durations(training)
            state = training.labels[-1]
            base = propagate(model, state, int(duration[-1]),
                             np.repeat(training.values[-1][None, :], max(matured), axis=0),
                             empirical_only=True)
        except (PanelError, np.linalg.LinAlgError) as exc:
            abstentions.append({"origin": training.periods[-1], "reason": str(exc)})
            continue
        for h, target_index in matured.items():
            p = next(cell["occupancy"] for cell in pred["horizons"] if cell["horizon_months"] == h)
            markov = base["horizons"][h - 1]["occupancy"]
            truth = panel.labels[target_index]
            persistence = [float(s == state) for s in model.states]
            records.append({"origin": training.periods[-1], "target_period": panel.periods[target_index],
                "horizon_months": h, "target_index": model.states.index(truth),
                "origin_state": state, "target_state": truth,
                "challenger": [p[s] for s in model.states],
                "markov": [markov[s] for s in model.states],
                "unconditional": model.unconditional.tolist(), "persistence": persistence,
                "training_through": training.periods[-1], "training_fingerprint": training.fingerprint,
                "fit_source_states": sum(r["fit_status"] == "FITTED" for r in model.row_evidence)})
    summaries = []
    for h in horizons:
        rows = [r for r in records if r["horizon_months"] == h]
        if not rows:
            summaries.append({"horizon_months": h, "status": "NO_MATURED_EVALUATIONS"})
            continue
        y = np.array([r["target_index"] for r in rows], dtype=int)
        scores = {name: probability_scores(np.array([r[name] for r in rows]), y)
                  for name in ("challenger", "markov", "unconditional", "persistence")}
        truth = np.eye(len(panel.states))[y]
        challenger_loss = ((np.array([r["challenger"] for r in rows]) - truth) ** 2).sum(axis=1)
        comparisons = {}
        for baseline in ("markov", "unconditional", "persistence"):
            baseline_loss = ((np.array([r[baseline] for r in rows]) - truth) ** 2).sum(axis=1)
            interval = paired_block_interval(challenger_loss - baseline_loss,
                                            block_size=max(1, math.ceil(h / stride)), seed=seed + h)
            denom = scores[baseline]["brier"]
            comparisons[baseline] = {"brier_skill": None if denom == 0 else 1 - scores["challenger"]["brier"] / denom,
                                     "paired_brier_difference": interval}
        origin_months = np.array([month_number(r["origin"]) for r in rows])
        separated, last = 0, -10**9
        for origin_month in origin_months:
            if origin_month - last >= h:
                separated += 1
                last = int(origin_month)
        summaries.append({"horizon_months": h, "status": "EXPLORATORY_EVALUATION",
            "scores": scores, "comparisons": comparisons, "n_origins": len(rows),
            "nonoverlapping_origin_windows": separated,
            "nonoverlapping_windows_are_independent_crises": False})
    return {"schema": "regime_one.transition_evaluation.v1", "method": METHOD,
            "source_basis": panel.source_basis, "target_name": panel.target_name,
            "panel_fingerprint": panel.fingerprint, "config": {
                "min_train_months": min_train_months, "horizons": horizons,
                "stride_months": stride, "simulation_paths": paths, "seed": seed},
            "tuning_on_evaluation": False, "historical_live_issuance_claimed": False,
            "summaries": summaries, "forecasts": records, "abstentions": abstentions,
            "authority": dict(AUTHORITY)}
