"""Industry-first research extension of leadership_rotation_context.

Pure computations: no collectors, stores, timers, live ranking or trade authority.
Historical price reconstructions are useful research inputs, not PIT attestations.
Every window is backward-looking. Labels are isolated from feature construction.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import logsumexp, softmax

from engine.leadership_rotation_context import classify_coordinate

SCHEMA = "prophet.industry_transition_research.v1"
BASIS = {"reconstructed_price_history", "original_retained", "synthetic_fixture"}
REL_WINDOWS = (5, 21, 63, 126, 252)
BASE_FEATURES = ("rel21", "rel126", "rel252", "sigma63")
CONTEXT_FEATURES = BASE_FEATURES + (
    "rel5", "rel63", "impulse21", "drawdown126", "distance21low", "beta_old",
    "residual21", "market21", "market63", "market252", "stress_ratio",
    "dispersion_raw", "dispersion_adjusted", "participation", "participation_change",
    "donor_rollover", "state_age", "leading", "weakening", "improving", "lagging",
)
INTERACTIONS = (
    ("rel126", "market63"), ("rel21", "drawdown126"),
    ("sigma63", "stress_ratio"), ("rel21", "donor_rollover"),
    ("improving", "dispersion_adjusted"), ("leading", "participation_change"),
    ("lagging", "stress_ratio"), ("beta_old", "market63"),
    ("weakening", "impulse21"), ("improving", "participation_change"),
)
MODEL_FEATURES = {
    "momentum_information": BASE_FEATURES,
    "additive_context": CONTEXT_FEATURES,
    "conditional_interactions": CONTEXT_FEATURES + tuple(a + "__x__" + b for a, b in INTERACTIONS),
}
CLASSES = ("upside_first", "downside_first", "unresolved")


def validate_panel(returns: pd.DataFrame, market: pd.Series) -> tuple[pd.DataFrame, pd.Series]:
    if not isinstance(returns, pd.DataFrame) or returns.empty:
        raise ValueError("nonempty returns DataFrame required")
    if not isinstance(returns.index, pd.DatetimeIndex):
        raise ValueError("DatetimeIndex required")
    if not returns.index.is_unique or not returns.index.is_monotonic_increasing:
        raise ValueError("sessions must be unique and strictly increasing")
    if not returns.columns.is_unique or not all(isinstance(x, str) and x for x in returns.columns):
        raise ValueError("unique nonempty industry identities required")
    if not isinstance(market, pd.Series) or not market.index.equals(returns.index):
        raise ValueError("market and industry session grids must match exactly")
    r, m = returns.astype(float).copy(), market.astype(float).copy()
    for values in (r.to_numpy(), m.to_numpy()):
        if np.isinf(values).any() or (values[np.isfinite(values)] <= -1).any():
            raise ValueError("simple return must be finite or missing and strictly above -1")
    return r, m


def feature_panel(returns: pd.DataFrame, market: pd.Series, *,
                  basis: str = "reconstructed_price_history",
                  decision_dates: pd.DatetimeIndex | None = None,
                  min_industries: int = 20) -> pd.DataFrame:
    """Backward-only features on an explicitly supplied session calendar.

    Omitted sessions are not inferable from returns. Internal NaNs invalidate
    required windows. Cumulative log indices are used only in complete masked
    local windows. The incomplete final month is not implicitly selected.
    """
    if basis not in BASIS:
        raise ValueError("unsupported evidence basis")
    if min_industries < 2:
        raise ValueError("at least two industries required")
    r, m = validate_panel(returns, market)
    lr, lm = np.log1p(r), np.log1p(m)
    relative = lr.sub(lm, axis=0)
    rel = {w: relative.rolling(w, min_periods=w).sum() for w in REL_WINDOWS}
    own21 = lr.rolling(21, min_periods=21).sum()
    m21 = lm.rolling(21, min_periods=21).sum()
    m63 = lm.rolling(63, min_periods=63).sum()
    sigma = lr.rolling(63, min_periods=63).std(ddof=1)
    market_var = lm.rolling(252, min_periods=252).var(ddof=1).shift(21)
    beta = lr.rolling(252, min_periods=252).cov(lm).shift(21).div(market_var, axis=0)
    beta = beta.where(market_var > 1e-16, np.nan)
    alpha = lr.rolling(252, min_periods=252).mean().shift(21).sub(
        beta.mul(lm.rolling(252, min_periods=252).mean().shift(21), axis=0))
    residual21 = own21 - 21 * alpha - beta.mul(m21, axis=0)
    cumulative = lr.cumsum()
    drawdown = np.expm1(cumulative - cumulative.rolling(126, min_periods=126).max())
    distance = cumulative - cumulative.rolling(21, min_periods=21).min()
    valid21 = own21.notna()
    participation = own21.gt(0).sum(axis=1).div(valid21.sum(axis=1).replace(0, np.nan))
    participation = participation.where(valid21.sum(axis=1) >= min_industries)
    dispersion = own21.std(axis=1, ddof=1).where(valid21.sum(axis=1) >= min_industries)
    adjusted = residual21.std(axis=1, ddof=1).where(residual21.notna().sum(axis=1) >= min_industries)
    old_strength = relative.rolling(231, min_periods=231).sum().shift(21)
    winners = old_strength.rank(axis=1, pct=True, method="average") > (2 / 3)
    leaders_valid = winners & rel[21].notna()
    leader_sum = rel[21].where(leaders_valid).sum(axis=1)
    leader_n = leaders_valid.sum(axis=1)
    donor = -(pd.DataFrame(np.repeat(leader_sum.to_numpy()[:, None], r.shape[1], axis=1),
                          index=r.index, columns=r.columns) - rel[21].where(leaders_valid, 0))
    donor = donor.div(pd.DataFrame(np.repeat(leader_n.to_numpy()[:, None], r.shape[1], axis=1),
                                  index=r.index, columns=r.columns) - leaders_valid.astype(int))
    donor = donor.where(np.isfinite(donor))
    common = pd.DataFrame({
        "market21": m21, "market63": m63,
        "market252": lm.rolling(252, min_periods=252).sum(),
        "stress_ratio": lm.rolling(21, min_periods=21).std(ddof=1) /
                        lm.rolling(63, min_periods=63).std(ddof=1).replace(0, np.nan),
        "dispersion_raw": dispersion, "dispersion_adjusted": adjusted,
        "participation": participation, "participation_change": participation - participation.shift(21),
    })
    if decision_dates is None:
        periods = r.index.to_period("M")
        chosen = r.index[np.r_[periods[:-1] != periods[1:], False]]
    else:
        chosen = pd.DatetimeIndex(decision_dates)
        if not chosen.is_unique or not chosen.is_monotonic_increasing or not chosen.isin(r.index).all():
            raise ValueError("decision dates must be ordered unique panel sessions")
    frames = []
    for industry in r.columns:
        f = pd.DataFrame({"rel" + str(w): rel[w][industry] for w in REL_WINDOWS})
        f["impulse21"] = rel[21][industry] - rel[21][industry].shift(21)
        f["drawdown126"], f["distance21low"] = drawdown[industry], distance[industry]
        f["sigma63"], f["beta_old"] = sigma[industry], beta[industry]
        f["residual21"], f["donor_rollover"] = residual21[industry], donor[industry]
        f = f.join(common)
        state = pd.Series([classify_coordinate(a, b) for a, b in zip(f.rel126, f.rel21)], index=f.index)
        change = state.ne(state.shift()).cumsum()
        age = state.groupby(change).cumcount() + 1
        f["state_age"] = age.where(state != "unmeasured").clip(upper=252)
        for name in ("leading", "weakening", "improving", "lagging"):
            f[name] = (state == name).astype(float)
        f["state"] = state
        complete = lr[industry].rolling(273, min_periods=273).count().eq(273)
        complete &= lm.rolling(273, min_periods=273).count().eq(273)
        f = f.loc[chosen].loc[complete.loc[chosen]]
        f = f.loc[np.isfinite(f[list(CONTEXT_FEATURES)].to_numpy()).all(axis=1)].copy()
        for a, b in INTERACTIONS:
            f[a + "__x__" + b] = f[a] * f[b]
        f["industry"], f["basis"] = industry, basis
        f["as_of"] = f.index
        frames.append(f)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).sort_values(["as_of", "industry"]).reset_index(drop=True)


def label_panel(features: pd.DataFrame, returns: pd.DataFrame, market: pd.Series, *,
                horizon: int = 63, entry_delay: int = 1, barrier: float = .10,
                round_trip_cost: float = .002) -> pd.DataFrame:
    """Fixed-risk outcomes, separate from feature construction.

    Entry at close t+entry_delay; returns start next session. Closing first passage
    is not intraday stop execution or an executable gap-fill model. Field suffix63
    is reserved for the canonical horizon; other horizons require another schema.
    """
    if horizon != 63 or entry_delay < 1 or not 0 < barrier < 1 or not 0 <= round_trip_cost < 1:
        raise ValueError("invalid label convention; canonical horizon is 63")
    r, m = validate_panel(returns, market)
    positions = {t: k for k, t in enumerate(r.index)}
    records = []
    for row in features.to_dict("records"):
        i = positions[pd.Timestamp(row["as_of"])]
        entry, end = i + entry_delay, i + entry_delay + horizon
        if end >= len(r):
            continue
        path_r = r[row["industry"]].iloc[entry + 1:end + 1].to_numpy()
        path_m = m.iloc[entry + 1:end + 1].to_numpy()
        if not np.isfinite(path_r).all() or not np.isfinite(path_m).all():
            continue
        path = np.expm1(np.log1p(path_r).cumsum())
        up, down = np.flatnonzero(path >= barrier), np.flatnonzero(path <= -barrier)
        u = int(up[0]) if len(up) else horizon + 1
        d = int(down[0]) if len(down) else horizon + 1
        outcome = 0 if u < d else 1 if d < u else 2
        market_total = float(np.expm1(np.log1p(path_m).sum()))
        records.append({**row, "entry_date": r.index[entry], "label_end": r.index[end],
                        "net63": float(path[-1] - round_trip_cost),
                        "excess63": float(path[-1] - round_trip_cost - market_total),
                        "mae63": float(min(0, path.min())), "bad10": float(path.min() <= -barrier),
                        "outcome": outcome, "win": float(path[-1] > round_trip_cost),
                        "upside_first": float(outcome == 0), "downside_first": float(outcome == 1),
                        "unresolved": float(outcome == 2)})
    return pd.DataFrame.from_records(records)


@dataclass
class ConditionalModel:
    """Regularized multi-head model; estimated, not validated, probabilities.

    scipy owns optimization. One fixed l2 penalty, no hyperparameter search.
    Equal-date objective weights prevent dense dates dominating the objective.
    """
    features: tuple[str, ...]
    l2: float = .03
    mean_: np.ndarray | None = None
    scale_: np.ndarray | None = None
    return_coef_: np.ndarray | None = None
    class_coef_: np.ndarray | None = None
    tail_coef_: np.ndarray | None = None
    fit_end_: str | None = None
    train_rows_: int = 0
    train_months_: int = 0

    def _design(self, frame: pd.DataFrame) -> np.ndarray:
        if self.mean_ is None or self.scale_ is None:
            raise ValueError("model not fitted")
        x = frame[list(self.features)].to_numpy(dtype=float)
        if not np.isfinite(x).all():
            raise ValueError("missing/nonfinite model input")
        return np.column_stack([np.ones(len(x)), np.clip((x - self.mean_) / self.scale_, -8, 8)])

    def fit(self, train: pd.DataFrame, *, prediction_start: pd.Timestamp) -> "ConditionalModel":
        if len(train) < 100 or train.as_of.nunique() < 24:
            raise ValueError("insufficient training rows or decision months")
        if not (pd.to_datetime(train.label_end) < prediction_start).all():
            raise ValueError("unmatured training label crosses prediction boundary")
        if train.duplicated(["as_of", "industry"]).any():
            raise ValueError("duplicate training decisions")
        if not train.outcome.isin([0, 1, 2]).all() or not train.bad10.isin([0, 1]).all():
            raise ValueError("invalid categorical or tail target")
        x = train[list(self.features)].to_numpy(dtype=float)
        if not np.isfinite(x).all() or not math.isfinite(self.l2) or self.l2 <= 0:
            raise ValueError("invalid training input or penalty")
        self.mean_, self.scale_ = x.mean(axis=0), x.std(axis=0)
        self.scale_[self.scale_ < 1e-10] = 1
        design = self._design(train)
        dates = pd.to_datetime(train.as_of)
        counts = dates.value_counts()
        weights = dates.map(1 / counts).to_numpy(dtype=float, copy=True)
        weights /= weights.sum()
        penalty = np.eye(design.shape[1]); penalty[0, 0] = 0
        y = train[["net63", "excess63"]].to_numpy(dtype=float)
        if not np.isfinite(y).all():
            raise ValueError("nonfinite target")
        self.return_coef_ = np.linalg.solve(design.T @ (weights[:, None] * design) + self.l2 * penalty,
                                             design.T @ (weights[:, None] * y))
        targets = np.eye(3)[train.outcome.to_numpy(dtype=int)]
        def objective(flat: np.ndarray) -> tuple[float, np.ndarray]:
            coef = flat.reshape(design.shape[1], 3)
            logits = design @ coef
            loss = np.sum(weights * (logsumexp(logits, axis=1) - (targets * logits).sum(axis=1)))
            loss += .5 * self.l2 * np.square(coef[1:]).sum()
            grad = design.T @ (weights[:, None] * (softmax(logits, axis=1) - targets))
            grad[1:] += self.l2 * coef[1:]
            return float(loss), grad.ravel()
        optimum = minimize(objective, np.zeros(design.shape[1] * 3), jac=True, method="L-BFGS-B",
                           options={"maxiter": 350, "ftol": 1e-11, "gtol": 1e-7})
        if not optimum.success:
            raise RuntimeError("class optimization did not converge: " + optimum.message)
        self.class_coef_ = optimum.x.reshape(design.shape[1], 3)
        tail = train.bad10.to_numpy(float)
        def tail_objective(coef: np.ndarray) -> tuple[float, np.ndarray]:
            z = design @ coef
            p = 1 / (1 + np.exp(-np.clip(z, -700, 700)))
            loss = np.sum(weights * (np.logaddexp(0, z) - tail * z)) + .5 * self.l2 * np.square(coef[1:]).sum()
            grad = design.T @ (weights * (p - tail)); grad[1:] += self.l2 * coef[1:]
            return float(loss), grad
        tail_fit = minimize(tail_objective, np.zeros(design.shape[1]), jac=True, method="L-BFGS-B",
                            options={"maxiter": 350, "ftol": 1e-11, "gtol": 1e-7})
        if not tail_fit.success:
            raise RuntimeError("tail optimization did not converge: " + tail_fit.message)
        self.tail_coef_ = tail_fit.x
        self.fit_end_ = str(pd.to_datetime(train.label_end).max().date())
        self.train_rows_, self.train_months_ = len(train), int(dates.nunique())
        return self

    def predict(self, frame: pd.DataFrame) -> pd.DataFrame:
        if self.return_coef_ is None or self.class_coef_ is None or self.tail_coef_ is None:
            raise ValueError("unfitted model")
        if self.fit_end_ is None or not (pd.to_datetime(frame.as_of) > pd.Timestamp(self.fit_end_)).all():
            raise ValueError("prediction must follow matured training labels")
        design = self._design(frame)
        probability = softmax(design @ self.class_coef_, axis=1)
        values = design @ self.return_coef_
        out = frame[["as_of", "industry", "state", "basis"]].copy()
        for j, name in enumerate(CLASSES):
            out["p_" + name] = probability[:, j]
        out["p_bad10"] = 1 / (1 + np.exp(-np.clip(design @ self.tail_coef_, -700, 700)))
        out["expected_net63"], out["expected_excess63"] = values[:, 0], values[:, 1]
        standardized = (frame[list(self.features)].to_numpy(float) - self.mean_) / self.scale_
        out["extrapolation_features"] = (np.abs(standardized) > 4).sum(axis=1)
        out["probability_status"] = "UNCALIBRATED_RESEARCH_ESTIMATE"
        return out

    def explain(self, frame: pd.DataFrame, top_n: int = 5) -> list[dict[str, Any]]:
        """Exact linear expected-excess decomposition; not causal feature attribution."""
        self.predict(frame)
        if not 1 <= top_n <= len(self.features):
            raise ValueError("invalid explanation length")
        contributions = self._design(frame)[:, 1:] * self.return_coef_[1:, 1]
        out = []
        for k, row in enumerate(frame.to_dict("records")):
            ordering = np.argsort(-np.abs(contributions[k]))[:top_n]
            out.append({"industry": row["industry"], "as_of": str(pd.Timestamp(row["as_of"]).date()),
                        "intercept": float(self.return_coef_[0, 1]),
                        "terms": [{"feature": self.features[j], "contribution": float(contributions[k, j])} for j in ordering],
                        "remaining_contribution": float(contributions[k].sum() - contributions[k, ordering].sum()),
                        "interpretation": "Predictive model arithmetic, not independent causal evidence."})
        return out

    def to_dict(self) -> dict[str, Any]:
        if self.class_coef_ is None:
            raise ValueError("unfitted model")
        return {"schema": SCHEMA, "features": list(self.features), "l2": self.l2,
                "mean": self.mean_.tolist(), "scale": self.scale_.tolist(),
                "return_coef": self.return_coef_.tolist(), "class_coef": self.class_coef_.tolist(),
                "tail_coef": self.tail_coef_.tolist(), "fit_end": self.fit_end_,
                "training_rows": self.train_rows_, "training_months": self.train_months_,
                "financial_influence": False, "probability_status": "UNCALIBRATED_RESEARCH_ESTIMATE"}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ConditionalModel":
        if (payload.get("schema") != SCHEMA or payload.get("financial_influence") is not False
                or payload.get("probability_status") != "UNCALIBRATED_RESEARCH_ESTIMATE"):
            raise ValueError("unsupported model envelope")
        names = tuple(payload.get("features", []))
        if names not in MODEL_FEATURES.values():
            raise ValueError("unsupported feature contract")
        model = cls(names, l2=float(payload["l2"]))
        n = len(names)
        for name, shape in (("mean", (n,)), ("scale", (n,)), ("return_coef", (n + 1, 2)),
                            ("class_coef", (n + 1, 3)), ("tail_coef", (n + 1,))):
            array = np.asarray(payload[name], dtype=float)
            if array.shape != shape or not np.isfinite(array).all():
                raise ValueError("invalid model array " + name)
            setattr(model, name + "_", array)
        if (model.scale_ <= 0).any() or not math.isfinite(model.l2) or model.l2 <= 0:
            raise ValueError("invalid model scaling or penalty")
        model.fit_end_ = str(pd.Timestamp(payload["fit_end"]).date())
        model.train_rows_ = int(payload["training_rows"])
        model.train_months_ = int(payload["training_months"])
        if model.train_rows_ < 100 or model.train_months_ < 24:
            raise ValueError("invalid training support")
        return model
