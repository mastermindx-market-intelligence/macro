"""Industry-first research forecasts. No live ranking or execution authority.

All transforms are prefix-safe. Industry states are observations, not ex-post
bottom labels. Models fit only matured labels and calibrate on a later disjoint
historical window. Reconstructed history is an allowed, explicitly named input.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize, minimize_scalar
from scipy.special import expit, logsumexp

SCHEMA = "prophet.industry_transition.v1"
CLASSES = ("upside_first", "downside_first", "timeout")
PRICE_FEATURES = (
    "relative21", "relative63", "relative126", "relative252", "return21",
    "return63", "vol63", "vol_ratio", "drawdown126", "distance21low",
)
CONTEXT_FEATURES = PRICE_FEATURES + (
    "beta", "residual21", "market21", "market126", "market_vol63",
    "market_vol_ratio", "participation21", "participation_change",
    "dispersion21", "residual_dispersion21", "leader_rollover",
    "relative_acceleration", "trend_stress", "repair_stress", "beta_market",
    "relative_breadth", "repair_volatility", "cash_rate", "cash_rate_change",
    "smb63", "hml63",
)


@dataclass(frozen=True)
class Config:
    horizon: int = 63
    entry_delay: int = 1
    target: float = 0.10
    loss: float = 0.10
    cost: float = 0.002
    regularization: float = 0.05
    calibration_months: int = 36
    min_fit_months: int = 120
    selection_fraction: float = 0.20
    seed: int = 20261114

    def __post_init__(self) -> None:
        if any(type(v) is not int or v < 1 for v in (self.horizon, self.entry_delay, self.calibration_months, self.min_fit_months)):
            raise ValueError("positive horizon and executable entry delay required")
        if not (0 < self.target < 1 and 0 < self.loss < 1):
            raise ValueError("target and loss must be fractions in (0,1)")
        if not (0 <= self.cost < 1 and self.regularization > 0):
            raise ValueError("invalid cost or regularization")
        if not (0 < self.selection_fraction <= 1):
            raise ValueError("invalid selection fraction")


def _validate_returns(frame: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise ValueError("DatetimeIndex required")
    if frame.index.tz is not None or frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError("unique sorted timezone-naive session dates required")
    if frame.columns.has_duplicates or frame.empty:
        raise ValueError("nonempty unique series required")
    out = frame.astype(float)
    a = out.to_numpy()
    if np.isinf(a).any() or np.any(a[np.isfinite(a)] <= -1):
        raise ValueError("returns must be fractions greater than -1; missing is NaN")
    return out


def make_features(returns: pd.DataFrame, market: pd.Series,
                  factors: pd.DataFrame | None = None) -> pd.DataFrame:
    """Produce daily industry context; caller chooses decision dates separately.

    Market/factors must have exactly the same session calendar. No forward fill,
    current constituent substitution or future cross-sectional standardization.
    """
    r = _validate_returns(returns)
    if not market.index.equals(r.index):
        raise ValueError("market calendar differs")
    m = _validate_returns(market.to_frame("market"))["market"]
    z, mz = np.log1p(r), np.log1p(m)
    if mz.isna().any():
        raise ValueError("market returns cannot be missing")
    sums = {h: z.rolling(h, min_periods=h).sum() for h in (21, 63, 126, 252)}
    ms = {h: mz.rolling(h, min_periods=h).sum() for h in (21, 63, 126, 252)}
    relative = {h: sums[h].sub(ms[h], axis=0) for h in sums}
    vol = z.rolling(63, min_periods=63).std(ddof=1)
    vr = z.rolling(21, min_periods=21).std(ddof=1) / vol.replace(0, np.nan)
    mv = mz.rolling(63, min_periods=63).std(ddof=1)
    mvr = mz.rolling(21, min_periods=21).std(ddof=1) / mv.replace(0, np.nan)
    # Frozen exposure uses 252 sessions ending before the recent21 window.
    variance = mz.rolling(252, min_periods=252).var(ddof=1).shift(21)
    beta = z.rolling(252, min_periods=252).cov(mz).shift(21).div(variance, axis=0)
    intercept = z.rolling(252, min_periods=252).mean().shift(21).sub(
        beta.mul(mz.rolling(252, min_periods=252).mean().shift(21), axis=0))
    residual = sums[21] - 21 * intercept - beta.mul(ms[21], axis=0)
    # Cumulative sums provide ratios only across complete rolling windows.
    levels = z.fillna(0).cumsum()
    dd = levels - levels.rolling(126, min_periods=126).max()
    low = levels - levels.rolling(21, min_periods=21).min()
    dd = dd.where(z.rolling(126, min_periods=126).count() == 126)
    low = low.where(z.rolling(21, min_periods=21).count() == 21)
    valid = relative[21].notna().sum(axis=1)
    participation = relative[21].gt(0).sum(axis=1) / valid.replace(0, np.nan)
    participation = participation.where(valid >= 20)
    disp = relative[21].std(axis=1, ddof=1).where(valid >= 20)
    rdisp = residual.std(axis=1, ddof=1).where(residual.notna().sum(axis=1) >= 20)
    old_strength = relative[252].shift(21)
    leaders = old_strength.rank(axis=1, pct=True).ge(2 / 3) & old_strength.notna()
    old_leader_return = relative[21].where(leaders)
    leader_sum = old_leader_return.sum(axis=1, min_count=1)
    leader_n = old_leader_return.notna().sum(axis=1)
    f = pd.DataFrame(index=r.index)
    if factors is not None:
        if not factors.index.equals(r.index):
            raise ValueError("factor calendar differs")
        if not {"RF", "SMB", "HML"}.issubset(factors):
            raise ValueError("RF, SMB, HML factors required when factors supplied")
        for name in ("RF", "SMB", "HML"):
            _validate_returns(factors[[name]])
        f["cash_rate"] = np.expm1(np.log1p(factors.RF).rolling(21, min_periods=21).mean() * 252)
        f["cash_rate_change"] = f.cash_rate - f.cash_rate.shift(126)
        f["smb63"] = np.log1p(factors.SMB).rolling(63, min_periods=63).sum()
        f["hml63"] = np.log1p(factors.HML).rolling(63, min_periods=63).sum()
    else:
        for name in ("cash_rate", "cash_rate_change", "smb63", "hml63"):
            f[name] = np.nan
    pieces = []
    for industry in r.columns:
        q = pd.DataFrame(index=r.index)
        q["industry"] = str(industry)
        for h in relative:
            q[f"relative{h}"] = relative[h][industry]
        q["return21"], q["return63"] = sums[21][industry], sums[63][industry]
        q["vol63"], q["vol_ratio"] = vol[industry], vr[industry]
        q["drawdown126"], q["distance21low"] = dd[industry], low[industry]
        q["beta"], q["residual21"] = beta[industry], residual[industry]
        q["market21"], q["market126"] = ms[21], ms[126]
        q["market_vol63"], q["market_vol_ratio"] = mv, mvr
        q["participation21"] = participation
        q["participation_change"] = participation - participation.shift(21)
        q["dispersion21"], q["residual_dispersion21"] = disp, rdisp
        own = old_leader_return[industry]
        q["leader_rollover"] = -(leader_sum - own.fillna(0)) / (leader_n - own.notna().astype(int)).replace(0, np.nan)
        q["relative_acceleration"] = q.relative21 - q.relative63 / 3
        q["trend_stress"] = q.relative126 * q.market126
        q["repair_stress"] = q.relative21 * q.market126
        q["beta_market"] = q.beta * q.market21
        q["relative_breadth"] = q.relative21 * (q.participation21 - 0.5)
        q["repair_volatility"] = q.relative21 * (q.market_vol_ratio - 1)
        for name in f:
            q[name] = f[name]
        long_up, short_up = q.relative126.ge(0), q.relative21.ge(0)
        q["state"] = np.select(
            [long_up & short_up, ~long_up & short_up, long_up & ~short_up],
            ["continuation", "reversal_attempt", "deterioration"],
            default="persistent_weakness")
        q.loc[q.relative126.isna() | q.relative21.isna(), "state"] = "unavailable"
        q.index.name = "decision_date"
        pieces.append(q.reset_index())
    return pd.concat(pieces, ignore_index=True).sort_values(["decision_date", "industry"]).reset_index(drop=True)


def make_events(returns: pd.DataFrame, market: pd.Series, features: pd.DataFrame,
                config: Config = Config()) -> pd.DataFrame:
    """Month-end features plus future labels; never used by feature production."""
    r = _validate_returns(returns)
    if not market.index.equals(r.index):
        raise ValueError("market calendar differs")
    dates = pd.Series(r.index, index=r.index).groupby(r.index.to_period("M")).last()
    # An incomplete final calendar month is not an eligible historical decision.
    dates = dates.loc[dates.dt.to_period("M") < r.index[-1].to_period("M")]
    if features.duplicated(["decision_date", "industry"]).any():
        raise ValueError("duplicate feature identities")
    lookup = features.set_index(["decision_date", "industry"])
    rows = []
    for dt in dates:
        i = r.index.get_loc(dt)
        entry, end = i + config.entry_delay, i + config.entry_delay + config.horizon
        if end >= len(r):
            continue
        mf = market.iloc[entry + 1:end + 1].to_numpy(float)
        if not np.isfinite(mf).all():
            continue
        market_return = float(np.prod(1 + mf) - 1)
        for industry in r:
            key = (dt, str(industry))
            if key not in lookup.index:
                continue
            row = lookup.loc[key].to_dict()
            if not np.isfinite([row[k] for k in PRICE_FEATURES]).all():
                continue
            # Entry close must exist, and every following close-to-close return.
            path_r = r[industry].iloc[entry:end + 1].to_numpy(float)
            if not np.isfinite(path_r).all():
                continue
            path = np.cumprod(1 + path_r[1:]) - 1
            up, down = np.flatnonzero(path >= config.target), np.flatnonzero(path <= -config.loss)
            tu = int(up[0]) if len(up) else config.horizon
            td = int(down[0]) if len(down) else config.horizon
            outcome = 0 if tu < td else 1 if td < tu else 2
            row.update(decision_date=dt, industry=str(industry),
                       entry_date=r.index[entry], label_end=r.index[end],
                       outcome=outcome, bad_loss=int(path.min() <= -config.loss),
                       terminal_gross=float(path[-1]), terminal_net=float(path[-1] - config.cost),
                       excess_net=float(path[-1] - market_return - config.cost),
                       adverse_excursion=float(min(0., path.min())), market_return=market_return)
            rows.append(row)
    if not rows:
        return pd.DataFrame(columns=list(features.columns) + ["entry_date", "label_end", "outcome", "bad_loss", "terminal_gross", "terminal_net", "excess_net", "adverse_excursion", "market_return"])
    return pd.DataFrame(rows).sort_values(["decision_date", "industry"]).reset_index(drop=True)


def month_weights(frame: pd.DataFrame) -> np.ndarray:
    n = frame.groupby("decision_date")["industry"].transform("size").to_numpy(float)
    w = 1. / n
    return w / w.sum()


class ResearchModel:
    """Regularized probabilistic estimator with transparent fixed interactions."""
    def __init__(self, feature_names: tuple[str, ...], config: Config = Config()):
        self.features, self.config = feature_names, config
        self.temperature = 1.
        self.fitted = False

    def _x(self, frame: pd.DataFrame) -> np.ndarray:
        a = frame.loc[:, self.features].to_numpy(float)
        if not np.isfinite(a).all():
            raise ValueError("missing or nonfinite required model inputs")
        a = np.clip((a - self.mean) / self.scale, -8, 8)
        return np.c_[np.ones(len(a)), a]

    def fit(self, fit: pd.DataFrame, calibration: pd.DataFrame,
            prediction_start: pd.Timestamp) -> "ResearchModel":
        if fit.empty or calibration.empty:
            raise ValueError("fit and calibration data required")
        if fit.label_end.max() >= calibration.decision_date.min():
            raise ValueError("fitting outcomes overlap calibration decisions")
        if calibration.label_end.max() >= prediction_start or fit.label_end.max() >= prediction_start:
            raise ValueError("outcomes not matured before prediction")
        if fit.decision_date.nunique() < self.config.min_fit_months:
            raise ValueError("insufficient fitting months")
        a = fit.loc[:, self.features].to_numpy(float)
        if not np.isfinite(a).all():
            raise ValueError("nonfinite fitting features")
        w = month_weights(fit)
        self.mean = np.sum(w[:, None] * a, axis=0)
        self.scale = np.sqrt(np.sum(w[:, None] * (a - self.mean) ** 2, axis=0))
        self.scale[self.scale < 1e-8] = 1.
        self.support_low, self.support_high = np.quantile(a, [.01, .99], axis=0)
        x = self._x(fit); y = fit.outcome.to_numpy(int)
        if not set(np.unique(y)).issubset({0, 1, 2}):
            raise ValueError("invalid outcome class")
        onehot = np.eye(3)[y]; d = x.shape[1]; lam = self.config.regularization
        def objective(flat):
            b = flat.reshape(d, 3); z = x @ b
            lp = z - logsumexp(z, axis=1, keepdims=True)
            value = -np.sum(w[:, None] * onehot * lp) + .5 * lam * np.sum(b[1:] ** 2)
            grad = x.T @ (w[:, None] * (np.exp(lp) - onehot))
            grad[1:] += lam * b[1:]
            return value, grad.ravel()
        fit_result = minimize(objective, np.zeros(d * 3), jac=True, method="L-BFGS-B",
                              options={"maxiter": 500, "ftol": 1e-11})
        if not fit_result.success:
            raise RuntimeError("multiclass optimization failed: " + str(fit_result.message))
        self.coef = fit_result.x.reshape(d, 3)
        zc = self._x(calibration) @ self.coef
        yc, wc = calibration.outcome.to_numpy(int), month_weights(calibration)
        def calibration_loss(log_t):
            z = zc / np.exp(log_t)
            return float(np.sum(wc * (logsumexp(z, axis=1) - z[np.arange(len(yc)), yc])))
        temp = minimize_scalar(calibration_loss, bounds=(np.log(.5), np.log(3.)), method="bounded")
        if not temp.success:
            raise RuntimeError("temperature calibration failed")
        self.temperature = float(np.exp(temp.x))
        bad = fit.bad_loss.to_numpy(float)
        def bad_objective(b):
            z = x @ b
            loss = np.sum(w * (np.logaddexp(0, z) - bad * z)) + .5 * lam * np.sum(b[1:] ** 2)
            grad = x.T @ (w * (expit(z) - bad)); grad[1:] += lam * b[1:]
            return loss, grad
        br = minimize(bad_objective, np.zeros(d), jac=True, method="L-BFGS-B",
                      options={"maxiter": 500, "ftol": 1e-11})
        if not br.success:
            raise RuntimeError("bad-loss optimization failed")
        self.bad_coef = br.x
        # Calibrate the bad-loss intercept on the disjoint calibration window.
        bz, by = self._x(calibration) @ self.bad_coef, calibration.bad_loss.to_numpy(float)
        shift = minimize_scalar(lambda v: float(np.sum(wc * (np.logaddexp(0, bz + v) - by * (bz + v)))),
                                bounds=(-3., 3.), method="bounded")
        if not shift.success:
            raise RuntimeError("bad-loss calibration failed")
        self.bad_offset = float(shift.x)
        # Ridge expectation is a separate target, not a rescaling of hit probability.
        penalty = np.eye(d) * lam; penalty[0, 0] = 0
        self.return_coef = np.linalg.solve(x.T @ (w[:, None] * x) + penalty,
                                          x.T @ (w * fit.excess_net.to_numpy(float)))
        self.prediction_start = pd.Timestamp(prediction_start)
        self.fit_end, self.calibration_end = fit.label_end.max(), calibration.label_end.max()
        self.fit_months, self.calibration_months = fit.decision_date.nunique(), calibration.decision_date.nunique()
        self.fitted = True
        return self

    def predict(self, frame: pd.DataFrame) -> pd.DataFrame:
        if not self.fitted:
            raise ValueError("model not fitted")
        if frame.decision_date.min() < self.prediction_start:
            raise ValueError("model cannot predict before its frozen prediction boundary")
        x = self._x(frame); z = x @ self.coef / self.temperature
        p = np.exp(z - logsumexp(z, axis=1, keepdims=True))
        out = frame.copy()
        for j, name in enumerate(CLASSES): out["p_" + name] = p[:, j]
        out["p_bad_loss"] = expit(x @ self.bad_coef + self.bad_offset)
        out["expected_excess_net"] = x @ self.return_coef
        out["score"] = p[:, 0] - p[:, 1]
        a = frame.loc[:, self.features].to_numpy(float)
        out["outside_support_share"] = ((a < self.support_low) | (a > self.support_high)).mean(axis=1)
        return out

    def explain(self, row: pd.DataFrame, limit: int = 5) -> list[dict[str, Any]]:
        x = self._x(row)[0, 1:]
        contributions = x * (self.coef[1:, 0] - self.coef[1:, 1]) / self.temperature
        order = np.argsort(-np.abs(contributions), kind="stable")[:limit]
        return [{"feature": self.features[j], "log_odds_contribution": float(contributions[j]),
                 "interpretation": "model association, not a causal effect"} for j in order]

    def to_artifact(self) -> dict:
        """Portable numeric JSON, never executable pickle or provider credentials."""
        if not self.fitted: raise ValueError("model not fitted")
        out = {"schema": "prophet.industry_research_model.v1", "authority": "research_only",
               "financial_influence": False, "metadata": self.metadata(),
               "arrays": {name: getattr(self, name).tolist() for name in
                          ("mean", "scale", "support_low", "support_high", "coef", "bad_coef", "return_coef")},
               "bad_offset": self.bad_offset}
        out["artifact_id"] = sha256(json.dumps(out, sort_keys=True, allow_nan=False).encode()).hexdigest()
        return out

    @classmethod
    def from_artifact(cls, artifact: dict) -> "ResearchModel":
        if artifact.get("schema") != "prophet.industry_research_model.v1" or artifact.get("financial_influence") is not False or artifact.get("authority") != "research_only":
            raise ValueError("invalid research model artifact")
        body = {k: v for k, v in artifact.items() if k != "artifact_id"}
        if sha256(json.dumps(body, sort_keys=True, allow_nan=False).encode()).hexdigest() != artifact.get("artifact_id"):
            raise ValueError("model artifact digest mismatch")
        meta = artifact["metadata"]; names = tuple(meta["features"])
        if not names or len(set(names)) != len(names): raise ValueError("invalid model features")
        obj = cls(names, Config(**meta["label_contract"]))
        n = len(names)
        shapes = {"mean": (n,), "scale": (n,), "support_low": (n,), "support_high": (n,),
                  "coef": (n + 1, 3), "bad_coef": (n + 1,), "return_coef": (n + 1,)}
        for name, shape in shapes.items():
            value = np.asarray(artifact["arrays"][name], dtype=float)
            if value.shape != shape or not np.isfinite(value).all(): raise ValueError("invalid model array: " + name)
            setattr(obj, name, value)
        if (obj.scale <= 0).any() or (obj.support_high < obj.support_low).any():
            raise ValueError("invalid model scaling/support")
        obj.temperature = float(meta["temperature"]); obj.bad_offset = float(artifact["bad_offset"])
        if not np.isfinite([obj.temperature, obj.bad_offset]).all() or obj.temperature <= 0:
            raise ValueError("invalid calibration parameters")
        obj.prediction_start = pd.Timestamp(meta["prediction_start"])
        obj.fit_end, obj.calibration_end = pd.Timestamp(meta["fit_label_end"]), pd.Timestamp(meta["calibration_label_end"])
        if pd.isna(obj.prediction_start) or pd.isna(obj.fit_end) or pd.isna(obj.calibration_end) or not obj.fit_end < obj.calibration_end < obj.prediction_start:
            raise ValueError("invalid model time boundary")
        obj.fit_months, obj.calibration_months = int(meta["fit_months"]), int(meta["calibration_months"])
        obj.fitted = True
        return obj

    def metadata(self) -> dict:
        return {"features": list(self.features), "temperature": self.temperature, "label_contract": asdict(self.config),
                "fit_label_end": str(self.fit_end.date()), "calibration_label_end": str(self.calibration_end.date()),
                "prediction_start": str(self.prediction_start.date()), "fit_months": int(self.fit_months),
                "calibration_months": int(self.calibration_months), "regularization": self.config.regularization}


def walk_forward(events: pd.DataFrame, config: Config = Config(),
                 first_year: int = 1950, last_year: int = 2002,
                 block_years: int = 5) -> tuple[pd.DataFrame, list[dict]]:
    """Fixed all-model sample; no fitting or calibration on prediction-block labels."""
    required = list(CONTEXT_FEATURES)
    eligible = events.loc[np.isfinite(events[required].to_numpy(float)).all(axis=1)].copy()
    outputs, receipts = [], []
    for year in range(first_year, last_year + 1, block_years):
        start, finish = pd.Timestamp(year, 1, 1), pd.Timestamp(min(last_year + 1, year + block_years), 1, 1)
        test = eligible[(eligible.decision_date >= start) & (eligible.decision_date < finish)]
        if test.empty: continue
        matured = eligible[eligible.label_end < start]
        cut = start - pd.DateOffset(months=config.calibration_months)
        calibration = matured[matured.decision_date >= cut]
        fit = matured[matured.label_end < cut]
        if fit.decision_date.nunique() < config.min_fit_months or calibration.decision_date.nunique() < 12:
            continue
        weights = month_weights(matured)
        probs = np.bincount(matured.outcome.astype(int), weights=weights, minlength=3)
        probs = (probs + 1 / len(matured)) / (probs.sum() + 3 / len(matured))
        base = test.copy()
        for j, name in enumerate(CLASSES): base["p_" + name] = probs[j]
        base["p_bad_loss"] = np.average(matured.bad_loss, weights=weights)
        base["expected_excess_net"] = np.average(matured.excess_net, weights=weights)
        base["score"] = probs[0] - probs[1]
        base["outside_support_share"] = np.nan
        base["model"], base["fold"] = "base_rate", year
        outputs.append(base)
        for name, columns in (("price", PRICE_FEATURES), ("context", CONTEXT_FEATURES)):
            model = ResearchModel(columns, config).fit(fit, calibration, start)
            pred = model.predict(test); pred["model"], pred["fold"] = name, year
            outputs.append(pred); receipts.append({"model": name, "fold": year, "test_events": len(test), **model.metadata()})
        momentum = test.copy()
        momentum["model"], momentum["fold"], momentum["score"] = "momentum126", year, momentum.relative126
        for name in CLASSES: momentum["p_" + name] = np.nan
        momentum["p_bad_loss"] = momentum["expected_excess_net"] = momentum["outside_support_share"] = np.nan
        outputs.append(momentum)
    if not outputs:
        raise ValueError("no qualified chronological folds")
    return pd.concat(outputs, ignore_index=True), receipts


def selected(frame: pd.DataFrame, fraction: float = .2) -> pd.DataFrame:
    """Identical per-date coverage; ties resolved by immutable industry key."""
    if not 0 < fraction <= 1: raise ValueError("invalid selection fraction")
    out = []
    for _, group in frame.groupby("decision_date", sort=True):
        k = max(1, int(np.ceil(len(group) * fraction)))
        out.append(group.sort_values(["score", "industry"], ascending=[False, True], kind="stable").head(k))
    return pd.concat(out, ignore_index=True) if out else frame.iloc[:0].copy()


def summarize(frame: pd.DataFrame) -> dict:
    if frame.empty: return {"events": 0, "months": 0}
    month = frame.groupby("decision_date")
    # Equal-month means, not an annualized tradable portfolio return.
    out = {"events": len(frame), "months": frame.decision_date.nunique(),
           "win": float(month.terminal_net.apply(lambda x: (x > 0).mean()).mean()),
           "bad_loss": float(month.bad_loss.mean().mean()),
           "terminal_net": float(month.terminal_net.mean().mean()),
           "excess_net": float(month.excess_net.mean().mean()),
           "adverse_excursion": float(month.adverse_excursion.mean().mean())}
    for j, name in enumerate(CLASSES):
        out[name] = float(month.outcome.apply(lambda x: (x == j).mean()).mean())
    if {"p_" + x for x in CLASSES}.issubset(frame) and frame.p_upside_first.notna().all():
        p = frame[["p_" + x for x in CLASSES]].to_numpy(float)
        y = frame.outcome.to_numpy(int); w = month_weights(frame)
        out["brier_multiclass"] = float(np.sum(w * np.sum((p - np.eye(3)[y]) ** 2, axis=1)))
        out["log_loss"] = float(-np.sum(w * np.log(np.clip(p[np.arange(len(y)), y], 1e-12, 1))))
        out["mean_predicted_bad_loss"] = float(np.average(frame.p_bad_loss, weights=w))
        out["bad_loss_brier"] = float(np.average((frame.p_bad_loss - frame.bad_loss) ** 2, weights=w))
    return out


def forecast_record(model: ResearchModel, feature_row: pd.DataFrame,
                    source_ref: str, evidence_mode: str) -> dict:
    if len(feature_row) != 1: raise ValueError("exactly one industry/date required")
    if evidence_mode not in {"RECONSTRUCTED_DISCOVERY", "OBSERVED_SHADOW"}:
        raise ValueError("explicit evidence mode required")
    p = model.predict(feature_row).iloc[0]
    payload = {"schema": SCHEMA, "industry": str(p.industry),
               "decision_date": str(pd.Timestamp(p.decision_date).date()), "state": str(p.state),
               "probabilities": {name: float(p["p_" + name]) for name in CLASSES},
               "p_bad_loss": float(p.p_bad_loss), "expected_excess_net": float(p.expected_excess_net),
               "outside_support_share": float(p.outside_support_share),
               "model": model.metadata(), "evidence_mode": evidence_mode, "source_ref": source_ref,
               "explanation": model.explain(feature_row), "authority": "research_only",
               "financial_influence": False, "calibration_claim": "historical_fold_calibrated_not_live_validated"}
    payload["record_id"] = sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()
    return payload
