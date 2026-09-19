"""Vintage-safe macro turnaround research evidence.

This module detects broad, early changes in macro direction without granting
forecast, ranking, gating, or trade authority.  Every observation carries both
an economic period and the date it became available.  Historical replays filter
on the latter, retain historical revisions, and therefore cannot silently use
information that was not known at the time.

The deterministic score is an input to research and product explanation.  It is
not a calibrated forecast.  Calibration, release-calendar replay, and forward
validation are separate promotion gates.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import date, datetime
from enum import Enum
from hashlib import sha256
import json
from math import exp, isfinite, log, sqrt
from statistics import mean, median, pstdev
from types import MappingProxyType
from typing import Mapping, Sequence


_EPSILON = 1e-12
_MODEL_VERSION = "macro-turnaround-research-v1.1-scale-qualified"


class Transform(str, Enum):
    LEVEL = "level"
    DIFF = "diff"
    PCT_CHANGE = "pct_change"
    YOY_DIFF = "yoy_diff"
    YOY_PCT_CHANGE = "yoy_pct_change"


class Phase(str, Enum):
    CONTRACTION = "contraction"
    TROUGHING = "troughing"
    EARLY_RECOVERY = "early_recovery"
    EXPANSION = "expansion"
    PEAKING = "peaking"
    SLOWDOWN = "slowdown"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True)
class Observation:
    period: date
    value: float
    available_at: date

    def __post_init__(self) -> None:
        object.__setattr__(self, "period", _coerce_date(self.period))
        object.__setattr__(self, "available_at", _coerce_date(self.available_at))
        object.__setattr__(self, "value", _finite_number(self.value, field="value"))

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "Observation":
        _require_mapping(payload, field="observation")
        expected = {"period", "value", "available_at"}
        unknown = set(payload) - expected
        missing = expected - set(payload)
        if unknown or missing:
            raise ValueError(
                f"observation fields mismatch; missing={sorted(missing)}, "
                f"unknown={sorted(unknown)}"
            )
        return cls(
            period=_coerce_date(payload["period"]),
            value=payload["value"],
            available_at=_coerce_date(payload["available_at"]),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "period": self.period.isoformat(),
            "value": self.value,
            "available_at": self.available_at.isoformat(),
        }


@dataclass(frozen=True)
class IndicatorSpec:
    key: str
    family: str
    weight: float = 1.0
    transform: Transform = Transform.LEVEL
    positive_when_rising: bool = True
    max_age_days: int = 100
    minimum_history: int = 18

    def __post_init__(self) -> None:
        object.__setattr__(self, "key", _nonempty_text(self.key, field="key"))
        object.__setattr__(self, "family", _nonempty_text(self.family, field="family"))
        object.__setattr__(self, "weight", _finite_number(self.weight, field="weight"))
        _strict_bool(self.positive_when_rising, field="positive_when_rising")
        _strict_integer(self.max_age_days, field="max_age_days")
        _strict_integer(self.minimum_history, field="minimum_history")
        object.__setattr__(self, "transform", Transform(self.transform))
        if not self.key:
            raise ValueError("indicator key must be non-empty")
        if not self.family:
            raise ValueError("indicator family must be non-empty")
        if self.weight <= 0:
            raise ValueError("indicator weight must be positive")
        if self.max_age_days <= 0:
            raise ValueError("max_age_days must be positive")
        if self.minimum_history < 8:
            raise ValueError("minimum_history must be at least 8")

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "IndicatorSpec":
        _require_mapping(payload, field="indicator spec")
        allowed = {
            "key",
            "family",
            "weight",
            "transform",
            "positive_when_rising",
            "max_age_days",
            "minimum_history",
        }
        unknown = set(payload) - allowed
        if unknown:
            raise ValueError(f"unknown indicator fields: {sorted(unknown)}")
        if "key" not in payload or "family" not in payload:
            raise ValueError("indicator key and family are required")
        return cls(
            key=payload["key"],
            family=payload["family"],
            weight=payload.get("weight", 1.0),
            transform=Transform(str(payload.get("transform", Transform.LEVEL.value))),
            positive_when_rising=_strict_bool(
                payload.get("positive_when_rising", True),
                field="positive_when_rising",
            ),
            max_age_days=payload.get("max_age_days", 100),
            minimum_history=payload.get("minimum_history", 18),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "family": self.family,
            "weight": self.weight,
            "transform": self.transform.value,
            "positive_when_rising": self.positive_when_rising,
            "max_age_days": self.max_age_days,
            "minimum_history": self.minimum_history,
        }


@dataclass(frozen=True)
class TurnaroundConfig:
    short_window: int = 3
    medium_window: int = 6
    robust_history: int = 60
    family_weight_cap: float = 0.35
    signal_temperature: float = 1.45
    enter_score: float = 0.64
    hold_score: float = 0.53
    minimum_coverage: float = 0.45
    top_driver_count: int = 5
    horizon_months: int = 6

    def __post_init__(self) -> None:
        for field in ("short_window", "medium_window", "robust_history", "top_driver_count", "horizon_months"):
            _strict_integer(getattr(self, field), field=field)
        for field in ("family_weight_cap", "signal_temperature", "enter_score", "hold_score", "minimum_coverage"):
            object.__setattr__(self, field, _finite_number(getattr(self, field), field=field))
        if self.short_window < 2:
            raise ValueError("short_window must be at least 2")
        if self.medium_window <= self.short_window:
            raise ValueError("medium_window must exceed short_window")
        if self.robust_history < self.medium_window * 2:
            raise ValueError("robust_history is too short")
        # Full diversity must require at least two independent families.  A
        # caller-configurable cap above one half would turn this safety control
        # into an on/off switch and let one family claim complete breadth.
        if not 0 < self.family_weight_cap <= 0.5:
            raise ValueError("family_weight_cap must be in (0, 0.5]")
        if self.signal_temperature <= 0:
            raise ValueError("signal_temperature must be positive")
        if not 0.5 <= self.enter_score < 1:
            raise ValueError("enter_score must be in [0.5, 1)")
        if not 0.5 <= self.hold_score <= self.enter_score:
            raise ValueError("hold_score must be between 0.5 and enter_score")
        if not 0 < self.minimum_coverage <= 1:
            raise ValueError("minimum_coverage must be in (0, 1]")
        if self.top_driver_count < 1:
            raise ValueError("top_driver_count must be positive")
        if self.horizon_months < 1:
            raise ValueError("horizon_months must be positive")

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "TurnaroundConfig":
        _require_mapping(payload, field="turnaround config")
        allowed = set(cls.__dataclass_fields__)
        unknown = set(payload) - allowed
        if unknown:
            raise ValueError(f"unknown turnaround config fields: {sorted(unknown)}")
        return cls(**payload)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, init=False)
class AuthorityBoundary:
    descriptive_context: bool = True
    research_priority: bool = True
    calibrated_forecast: bool = False
    ranking_authority: bool = False
    gating_authority: bool = False
    trade_authority: bool = False

    def to_dict(self) -> dict[str, bool]:
        return asdict(self)


@dataclass(frozen=True)
class IndicatorSignal:
    key: str
    family: str
    declared_weight: float
    effective_weight: float
    period: date
    available_at: date
    age_days: int
    period_age_days: int
    release_age_days: int
    level_z: float
    short_slope_z: float
    medium_slope_z: float
    acceleration_z: float
    recovery_evidence: float
    downturn_evidence: float
    directional_score: float
    recency_score: float
    history_score: float

    def to_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "family": self.family,
            "declared_weight": self.declared_weight,
            "effective_weight": self.effective_weight,
            "period": self.period.isoformat(),
            "available_at": self.available_at.isoformat(),
            "age_days": self.age_days,
            "period_age_days": self.period_age_days,
            "release_age_days": self.release_age_days,
            "level_z": self.level_z,
            "short_slope_z": self.short_slope_z,
            "medium_slope_z": self.medium_slope_z,
            "acceleration_z": self.acceleration_z,
            "recovery_evidence": self.recovery_evidence,
            "downturn_evidence": self.downturn_evidence,
            "directional_score": self.directional_score,
            "recency_score": self.recency_score,
            "history_score": self.history_score,
        }


@dataclass(frozen=True)
class Driver:
    key: str
    family: str
    direction: str
    contribution: float
    explanation: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DataQuality:
    coverage: float
    recency: float
    agreement: float
    history: float
    excluded: Mapping[str, str]
    flags: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "excluded", MappingProxyType(dict(self.excluded)))

    def to_dict(self) -> dict[str, object]:
        return {
            "coverage": self.coverage,
            "recency": self.recency,
            "agreement": self.agreement,
            "history": self.history,
            "excluded": dict(sorted(self.excluded.items())),
            "flags": list(self.flags),
        }


@dataclass(frozen=True)
class TurnaroundAssessment:
    as_of: date
    phase: Phase
    previous_phase: Phase | None
    horizon_months: int
    upturn_score: float
    downturn_score: float
    confidence: float
    composite_level: float
    composite_slope: float
    composite_acceleration: float
    breadth_improving: float
    breadth_deteriorating: float
    input_hash: str
    config_hash: str
    signals: tuple[IndicatorSignal, ...]
    drivers: tuple[Driver, ...]
    quality: DataQuality

    def to_dict(self) -> dict[str, object]:
        return {
            "as_of": self.as_of.isoformat(),
            "phase": self.phase.value,
            "previous_phase": self.previous_phase.value if self.previous_phase else None,
            "horizon_months": self.horizon_months,
            "raw_scores": {
                "upturn": self.upturn_score,
                "downturn": self.downturn_score,
            },
            "confidence": self.confidence,
            "composite": {
                "level": self.composite_level,
                "slope": self.composite_slope,
                "acceleration": self.composite_acceleration,
            },
            "breadth": {
                "improving": self.breadth_improving,
                "deteriorating": self.breadth_deteriorating,
            },
            "input_hash": self.input_hash,
            "config_hash": self.config_hash,
            "signals": [signal.to_dict() for signal in self.signals],
            "drivers": [driver.to_dict() for driver in self.drivers],
            "quality": self.quality.to_dict(),
        }


class MacroTurnaroundEngine:
    def __init__(self, config: TurnaroundConfig | None = None) -> None:
        if config is None:
            self.config = TurnaroundConfig()
        elif isinstance(config, TurnaroundConfig):
            self.config = config
        else:
            raise TypeError("config must be a TurnaroundConfig or None")

    def assess(
        self,
        observations: Mapping[str, Sequence[Observation | Mapping[str, object]]],
        specs: Sequence[IndicatorSpec | Mapping[str, object]],
        as_of: date | str,
        previous_phase: Phase | str | None = None,
    ) -> TurnaroundAssessment:
        as_of_date = _coerce_date(as_of)
        normalized_specs = tuple(
            spec if isinstance(spec, IndicatorSpec) else IndicatorSpec.from_dict(spec)
            for spec in specs
        )
        if not normalized_specs:
            raise ValueError("at least one indicator spec is required")
        keys = [spec.key for spec in normalized_specs]
        if len(keys) != len(set(keys)):
            raise ValueError("indicator spec keys must be unique")
        normalized_specs = tuple(sorted(normalized_specs, key=lambda item: item.key))
        _require_mapping(observations, field="observations")
        unknown = set(observations) - set(keys)
        if unknown:
            raise ValueError(f"unknown observation series: {sorted(unknown)}")
        normalized_observations = {
            spec.key: tuple(
                item if isinstance(item, Observation) else Observation.from_dict(item)
                for item in observations.get(spec.key, ())
            )
            for spec in normalized_specs
        }
        prior = Phase(previous_phase) if previous_phase is not None else None

        eligible_payload = _eligible_vintage_payload(normalized_observations, as_of_date)
        input_hash = _content_hash(eligible_payload)
        config_hash = _content_hash(
            {
                "model_version": _MODEL_VERSION,
                "config": self.config.to_dict(),
                "specs": [spec.to_dict() for spec in sorted(normalized_specs, key=lambda item: item.key)],
            }
        )

        _finite_number(sum(spec.weight for spec in normalized_specs), field="total indicator weight")
        raw_signals: list[IndicatorSignal] = []
        excluded: dict[str, str] = {}
        for spec in normalized_specs:
            series = normalized_observations[spec.key]
            signal, reason = self._indicator_signal(series, spec, as_of_date)
            if signal is None:
                excluded[spec.key] = reason or "unavailable"
            else:
                raw_signals.append(signal)

        # Coverage uses the configured family budget, not the number of related
        # series still present. Ten labor proxies cannot replace absent credit.
        coverage = self._family_coverage(raw_signals, normalized_specs)
        family_count = len({signal.family for signal in raw_signals})
        diversity = min(1.0, family_count * self.config.family_weight_cap)
        if not raw_signals or coverage < self.config.minimum_coverage:
            flags = ["insufficient_coverage"]
            if coverage < 1.0:
                flags.append("partial_coverage")
            if not raw_signals:
                flags.append("no_eligible_indicators")
            elif diversity < 1.0 - _EPSILON:
                flags.append("family_cap_infeasible")
            return TurnaroundAssessment(
                as_of=as_of_date,
                phase=Phase.INDETERMINATE,
                previous_phase=prior,
                horizon_months=self.config.horizon_months,
                upturn_score=0.5,
                downturn_score=0.5,
                confidence=0.0,
                composite_level=0.0,
                composite_slope=0.0,
                composite_acceleration=0.0,
                breadth_improving=0.0,
                breadth_deteriorating=0.0,
                input_hash=input_hash,
                config_hash=config_hash,
                signals=tuple(raw_signals),
                drivers=(),
                quality=DataQuality(
                    coverage=coverage,
                    recency=0.0,
                    agreement=0.0,
                    history=0.0,
                    excluded=excluded,
                    flags=tuple(flags),
                ),
            )

        effective_weights = self._family_capped_weights(raw_signals)
        signals = tuple(
            replace(signal, effective_weight=weight)
            for signal, weight in zip(raw_signals, effective_weights)
        )
        composite_level = _weighted_mean(
            [signal.level_z for signal in signals], effective_weights
        )
        composite_short = _weighted_mean(
            [signal.short_slope_z for signal in signals], effective_weights
        )
        composite_medium = _weighted_mean(
            [signal.medium_slope_z for signal in signals], effective_weights
        )
        composite_acceleration = _weighted_mean(
            [signal.acceleration_z for signal in signals], effective_weights
        )
        recovery = _weighted_mean(
            [signal.recovery_evidence for signal in signals], effective_weights
        )
        downturn = _weighted_mean(
            [signal.downturn_evidence for signal in signals], effective_weights
        )
        breadth_improving = sum(
            weight
            for signal, weight in zip(signals, effective_weights)
            if signal.short_slope_z > 0.15 and signal.acceleration_z > -0.15
        )
        breadth_deteriorating = sum(
            weight
            for signal, weight in zip(signals, effective_weights)
            if signal.short_slope_z < -0.15 and signal.acceleration_z < 0.15
        )
        slope = 0.65 * composite_short + 0.35 * composite_medium

        upturn_logit = (
            0.42 * recovery
            + 0.20 * composite_short
            + 0.13 * composite_medium
            + 0.15 * composite_acceleration
            + 0.10 * _symmetric_unit(breadth_improving - 0.5)
        ) / self.config.signal_temperature
        downturn_logit = (
            0.42 * downturn
            - 0.20 * composite_short
            - 0.13 * composite_medium
            - 0.15 * composite_acceleration
            + 0.10 * _symmetric_unit(breadth_deteriorating - 0.5)
        ) / self.config.signal_temperature
        upturn_score = _clip(_sigmoid(2.8 * upturn_logit), 0.01, 0.99)
        downturn_score = _clip(_sigmoid(2.8 * downturn_logit), 0.01, 0.99)

        recency = _weighted_mean(
            [signal.recency_score for signal in signals], effective_weights
        )
        history = _weighted_mean(
            [signal.history_score for signal in signals], effective_weights
        )
        dispersion = _weighted_std(
            [signal.directional_score for signal in signals], effective_weights
        )
        agreement = _clip(1.0 - dispersion / 2.5, 0.0, 1.0)
        confidence = _geometric_confidence(coverage, recency, agreement, history) * diversity
        flags: list[str] = []
        if diversity < 1.0 - _EPSILON:
            flags.append("family_cap_infeasible")
        if coverage < 0.70:
            flags.append("partial_coverage")
        if recency < 0.65:
            flags.append("stale_inputs")
        if agreement < 0.55:
            flags.append("low_cross_indicator_agreement")
        if history < 0.65:
            flags.append("limited_history")
        if abs(upturn_score - downturn_score) < 0.08:
            flags.append("two_sided_risk")

        candidate = self._candidate_phase(
            composite_level,
            slope,
            upturn_score,
            downturn_score,
        )
        phase = self._apply_hysteresis(
            candidate,
            prior,
            upturn_score,
            downturn_score,
        )
        drivers = self._drivers(signals)
        return TurnaroundAssessment(
            as_of=as_of_date,
            phase=phase,
            previous_phase=prior,
            horizon_months=self.config.horizon_months,
            upturn_score=upturn_score,
            downturn_score=downturn_score,
            confidence=confidence,
            composite_level=composite_level,
            composite_slope=slope,
            composite_acceleration=composite_acceleration,
            breadth_improving=breadth_improving,
            breadth_deteriorating=breadth_deteriorating,
            input_hash=input_hash,
            config_hash=config_hash,
            signals=signals,
            drivers=tuple(drivers),
            quality=DataQuality(
                coverage=coverage,
                recency=recency,
                agreement=agreement,
                history=history,
                excluded=excluded,
                flags=tuple(flags),
            ),
        )

    def walk_forward(
        self,
        observations: Mapping[str, Sequence[Observation | Mapping[str, object]]],
        specs: Sequence[IndicatorSpec | Mapping[str, object]],
        as_of_dates: Sequence[date | str],
    ) -> list[TurnaroundAssessment]:
        results: list[TurnaroundAssessment] = []
        previous: Phase | None = None
        dates = sorted(_coerce_date(value) for value in as_of_dates)
        if len(set(dates)) != len(dates):
            raise ValueError("walk-forward cutoff dates must be unique")
        for as_of in dates:
            assessment = self.assess(
                observations,
                specs,
                as_of,
                previous_phase=previous,
            )
            results.append(assessment)
            previous = assessment.phase
        return results

    def _indicator_signal(
        self,
        series: Sequence[Observation],
        spec: IndicatorSpec,
        as_of: date,
    ) -> tuple[IndicatorSignal | None, str | None]:
        ordered = _select_vintages(series, as_of)
        if not ordered:
            return None, "no_observation_available_as_of_date"
        latest = ordered[-1]
        release_age_days = (as_of - latest.available_at).days
        period_age_days = (as_of - latest.period).days
        age_days = max(release_age_days, period_age_days)
        if age_days < 0:
            return None, "future_release"
        if age_days > spec.max_age_days * 2:
            return None, "too_stale"

        if spec.transform in {Transform.YOY_DIFF, Transform.YOY_PCT_CHANGE}:
            months = [item.period.year * 12 + item.period.month for item in ordered]
            if any(right - left != 1 for left, right in zip(months, months[1:])):
                return None, "nonmonthly_yoy_history"
        try:
            transformed = _transform([observation.value for observation in ordered], spec.transform)
        except ValueError as exc:
            return None, str(exc)
        if not all(isfinite(value) for value in transformed):
            return None, "nonfinite_transformation"
        minimum = max(spec.minimum_history, self.config.medium_window * 2 + 2)
        if len(transformed) < minimum:
            return None, "insufficient_history"
        orientation = 1.0 if spec.positive_when_rising else -1.0
        values = [orientation * value for value in transformed]
        short_slopes = _rolling_slopes(values, self.config.short_window)
        medium_slopes = _rolling_slopes(values, self.config.medium_window)
        if len(short_slopes) < 3 or len(medium_slopes) < 2:
            return None, "insufficient_slope_history"
        accelerations = [
            short_slopes[index] - short_slopes[index - 1]
            for index in range(1, len(short_slopes))
        ]
        try:
            level_z = _robust_latest_z(values, self.config.robust_history)
            short_slope_z = _robust_latest_z(short_slopes, self.config.robust_history)
            medium_slope_z = _robust_latest_z(medium_slopes, self.config.robust_history)
            acceleration_z = _robust_latest_z(accelerations, self.config.robust_history)
        except ValueError as exc:
            if str(exc) != "unidentifiable_feature_scale":
                raise
            return None, "unidentifiable_feature_scale"
        if not all(isfinite(value) for value in (level_z, short_slope_z, medium_slope_z, acceleration_z)):
            return None, "nonfinite_features"
        weak_level = _clip(-level_z, 0.0, 3.0)
        strong_level = _clip(level_z, 0.0, 3.0)
        recovery_evidence = (
            0.40 * short_slope_z
            + 0.20 * medium_slope_z
            + 0.25 * acceleration_z
            + 0.15 * weak_level
        )
        downturn_evidence = (
            -0.40 * short_slope_z
            - 0.20 * medium_slope_z
            - 0.25 * acceleration_z
            + 0.15 * strong_level
        )
        directional_score = (
            0.55 * short_slope_z
            + 0.25 * medium_slope_z
            + 0.20 * acceleration_z
        )
        return (
            IndicatorSignal(
                key=spec.key,
                family=spec.family,
                declared_weight=spec.weight,
                effective_weight=0.0,
                period=latest.period,
                available_at=latest.available_at,
                age_days=age_days,
                period_age_days=period_age_days,
                release_age_days=release_age_days,
                level_z=level_z,
                short_slope_z=short_slope_z,
                medium_slope_z=medium_slope_z,
                acceleration_z=acceleration_z,
                recovery_evidence=recovery_evidence,
                downturn_evidence=downturn_evidence,
                directional_score=directional_score,
                recency_score=_clip(exp(-max(age_days, 0) / spec.max_age_days), 0.0, 1.0),
                history_score=_clip(
                    len(values) / max(float(spec.minimum_history * 2), 1.0),
                    0.0,
                    1.0,
                ),
            ),
            None,
        )

    def _family_coverage(
        self,
        signals: Sequence[IndicatorSignal],
        specs: Sequence[IndicatorSpec],
    ) -> float:
        configured: dict[str, float] = {}
        available: dict[str, float] = {}
        for spec in specs:
            configured[spec.family] = configured.get(spec.family, 0.0) + spec.weight
        for signal in signals:
            available[signal.family] = available.get(signal.family, 0.0) + signal.declared_weight
        total = sum(configured.values())
        shares = _cap_and_renormalize(
            {family: weight / total for family, weight in configured.items()},
            self.config.family_weight_cap,
        )
        return _clip(sum(
            shares[family] * (available.get(family, 0.0) / weight)
            for family, weight in configured.items()
        ), 0.0, 1.0)

    def _family_capped_weights(
        self,
        signals: Sequence[IndicatorSignal],
    ) -> list[float]:
        family_totals: dict[str, float] = {}
        for signal in signals:
            family_totals[signal.family] = (
                family_totals.get(signal.family, 0.0) + signal.declared_weight
            )
        total = sum(family_totals.values())
        family_shares = {
            family: weight / total for family, weight in family_totals.items()
        }
        capped = _cap_and_renormalize(
            family_shares,
            self.config.family_weight_cap,
        )
        weights = [
            capped[signal.family]
            * (signal.declared_weight / family_totals[signal.family])
            for signal in signals
        ]
        normalized_total = sum(weights)
        return [weight / normalized_total for weight in weights]

    def _candidate_phase(
        self,
        level: float,
        slope: float,
        upturn_score: float,
        downturn_score: float,
    ) -> Phase:
        enter = self.config.enter_score
        if upturn_score >= enter and level < -0.30:
            return Phase.TROUGHING
        if upturn_score >= enter and slope > 0.20:
            return Phase.EARLY_RECOVERY
        if downturn_score >= enter and level > 0.30:
            return Phase.PEAKING
        if downturn_score >= enter and slope < -0.20:
            return Phase.CONTRACTION
        if slope >= 0.10 and level >= -0.10:
            return Phase.EXPANSION
        if slope <= -0.10:
            return Phase.SLOWDOWN
        return Phase.INDETERMINATE

    def _apply_hysteresis(
        self,
        candidate: Phase,
        previous: Phase | None,
        upturn_score: float,
        downturn_score: float,
    ) -> Phase:
        if previous is None or previous is candidate:
            return candidate
        recovery = {Phase.TROUGHING, Phase.EARLY_RECOVERY, Phase.EXPANSION}
        contraction = {Phase.PEAKING, Phase.SLOWDOWN, Phase.CONTRACTION}
        if previous in recovery and candidate in contraction:
            return candidate if downturn_score >= self.config.enter_score else previous
        if previous in contraction and candidate in recovery:
            return candidate if upturn_score >= self.config.enter_score else previous
        if previous in {Phase.TROUGHING, Phase.EARLY_RECOVERY}:
            return candidate if upturn_score < self.config.hold_score else previous
        if previous in {Phase.PEAKING, Phase.CONTRACTION}:
            return candidate if downturn_score < self.config.hold_score else previous
        return candidate

    def _drivers(self, signals: Sequence[IndicatorSignal]) -> list[Driver]:
        ranked: list[tuple[float, Driver]] = []
        for signal in signals:
            contribution = signal.effective_weight * signal.directional_score
            direction = "improving" if contribution >= 0 else "deteriorating"
            ranked.append(
                (
                    abs(contribution),
                    Driver(
                        key=signal.key,
                        family=signal.family,
                        direction=direction,
                        contribution=contribution,
                        explanation=(
                            f"{signal.key} is {direction}: short slope z="
                            f"{signal.short_slope_z:.2f}, medium slope z="
                            f"{signal.medium_slope_z:.2f}, acceleration z="
                            f"{signal.acceleration_z:.2f}; evidence age="
                            f"{signal.age_days}d (period {signal.period_age_days}d; "
                            f"release {signal.release_age_days}d)."
                        ),
                    ),
                )
            )
        ranked.sort(key=lambda item: (-item[0], item[1].key))
        return [driver for _, driver in ranked[: self.config.top_driver_count]]


def build_research_artifact(
    assessment: TurnaroundAssessment,
) -> dict[str, object]:
    """Project one assessment into the authority-safe machine contract."""
    artifact = {
        "schema": "macro.turnaround_research.v1",
        "model_version": _MODEL_VERSION,
        "score_status": "available_research_only" if assessment.signals and assessment.confidence > 0 else "unavailable",
        "numeric_interpretation": {
            "standardized_slopes": "historical_anomaly_not_economic_direction",
            "phase": "unvalidated_research_phase_not_confirmed_economic_state",
            "confidence": "evidence_quality_not_calibrated_predictive_certainty",
            "horizon_months": "research_label_not_validated_forecast_horizon",
            "unavailable_numeric_placeholders_are_not_estimates": True,
        },
        "capability_state": "BUILT_NOT_PROVEN",
        "as_of": assessment.as_of.isoformat(),
        "horizon_months": assessment.horizon_months,
        "phase": assessment.phase.value,
        "previous_phase": (
            assessment.previous_phase.value if assessment.previous_phase else None
        ),
        "raw_scores": {
            "upturn": assessment.upturn_score,
            "downturn": assessment.downturn_score,
        },
        "confidence": assessment.confidence,
        "composite": {
            "level": assessment.composite_level,
            "slope": assessment.composite_slope,
            "acceleration": assessment.composite_acceleration,
        },
        "breadth": {
            "improving": assessment.breadth_improving,
            "deteriorating": assessment.breadth_deteriorating,
        },
        "drivers": [driver.to_dict() for driver in assessment.drivers],
        "quality": assessment.quality.to_dict(),
        "signals": [signal.to_dict() for signal in assessment.signals],
        "input_hash": assessment.input_hash,
        "config_hash": assessment.config_hash,
        "authority": AuthorityBoundary().to_dict(),
        "correction_policy": {
            "historical_artifacts_are_immutable": True,
            "new_release_or_revision_mints_new_input_hash": True,
            "period_and_available_at_are_distinct": True,
        },
        "promotion_gates": [
            "point_in_time_release_calendar_replay",
            "expanding_window_out_of_sample_validation",
            "held_out_score_calibration",
            "forward_shadow_observation",
            "separate_authority_review",
        ],
    }
    # Input/config identity alone does not bind recency or hysteresis state.
    artifact["artifact_hash"] = _content_hash(artifact)
    return artifact


def _select_vintages(series: Sequence[Observation], as_of: date) -> list[Observation]:
    eligible = sorted(
        (item for item in series if item.available_at <= as_of and item.period <= as_of),
        key=lambda item: (item.period, item.available_at),
    )
    vintages: dict[tuple[date, date], Observation] = {}
    by_period: dict[date, Observation] = {}
    for item in eligible:
        identity = (item.period, item.available_at)
        previous = vintages.get(identity)
        if previous is not None and previous.value != item.value:
            raise ValueError(f"conflicting observation vintage for period={item.period} available_at={item.available_at}")
        vintages[identity] = item
        by_period[item.period] = item
    return [by_period[period] for period in sorted(by_period)]


def _eligible_vintage_payload(
    observations: Mapping[str, Sequence[Observation | Mapping[str, object]]],
    as_of: date,
) -> dict[str, list[dict[str, object]]]:
    payload: dict[str, list[dict[str, object]]] = {}
    for key in sorted(observations):
        normalized = [
            item if isinstance(item, Observation) else Observation.from_dict(item)
            for item in observations[key]
        ]
        payload[key] = [item.to_dict() for item in _select_vintages(normalized, as_of)]
    return payload


def _coerce_date(value: object) -> date:
    # This contract is daily, not intraday. Never truncate a release timestamp
    # into knowledge at the start of that day. Timestamp adapters must explicitly
    # choose a daily boundary before supplying observations to this engine.
    if isinstance(value, datetime):
        raise ValueError("daily date required; datetime cutoffs are not supported")
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            pass
        else:
            if value == parsed.isoformat():
                return parsed
    raise ValueError("date must be a canonical YYYY-MM-DD daily date")


def _require_mapping(value: object, *, field: str) -> None:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")


def _nonempty_text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _finite_number(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite numeric value, not a boolean or string")
    try:
        number = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"{field} must be finite") from exc
    if not isfinite(number):
        raise ValueError(f"{field} must be finite")
    # Canonicalize IEEE signed zero so equal vintages have identical hashes.
    return 0.0 if number == 0.0 else number


def _strict_integer(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer, not a boolean or coerced value")
    return value


def _strict_bool(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be a boolean")
    return value


def _content_hash(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _transform(values: Sequence[float], transform: Transform) -> list[float]:
    normalized = [float(value) for value in values]
    if transform is Transform.LEVEL:
        return normalized
    if transform is Transform.DIFF:
        return [
            normalized[index] - normalized[index - 1]
            for index in range(1, len(normalized))
        ]
    if transform is Transform.PCT_CHANGE:
        if any(abs(value) <= _EPSILON for value in normalized[:-1]):
            raise ValueError("undefined_percentage_change")
        return [
            (normalized[index] / normalized[index - 1] - 1.0) * 100.0
            for index in range(1, len(normalized))
        ]
    if transform is Transform.YOY_DIFF:
        return [
            normalized[index] - normalized[index - 12]
            for index in range(12, len(normalized))
        ]
    if transform is Transform.YOY_PCT_CHANGE:
        if any(abs(value) <= _EPSILON for value in normalized[:-12]):
            raise ValueError("undefined_percentage_change")
        return [
            (normalized[index] / normalized[index - 12] - 1.0) * 100.0
            for index in range(12, len(normalized))
        ]
    raise ValueError(f"unsupported transform: {transform}")


def _rolling_slopes(values: Sequence[float], window: int) -> list[float]:
    if len(values) < window:
        return []
    x_mean = (window - 1) / 2.0
    denominator = sum((index - x_mean) ** 2 for index in range(window))
    slopes: list[float] = []
    for end in range(window, len(values) + 1):
        segment = values[end - window : end]
        y_mean = mean(segment)
        numerator = sum(
            (index - x_mean) * (value - y_mean)
            for index, value in enumerate(segment)
        )
        slopes.append(numerator / max(denominator, _EPSILON))
    return slopes


def _robust_latest_z(values: Sequence[float], history: int) -> float:
    if not values:
        return 0.0
    sample = list(values[-history:])
    current = sample[-1]
    baseline = sample[:-1] if len(sample) > 4 else sample
    center = median(baseline)
    mad = median(abs(value - center) for value in baseline)
    scale = 1.4826 * mad
    if scale < _EPSILON:
        scale = pstdev(baseline) if len(baseline) > 1 else 1.0
    if scale < _EPSILON:
        # Zero historical dispersion cannot distinguish a truly unchanged
        # observation from the first large shock. Do not invent neutral evidence.
        raise ValueError("unidentifiable_feature_scale")
    return _clip((current - center) / scale, -4.0, 4.0)


def _weighted_mean(values: Sequence[float], weights: Sequence[float]) -> float:
    if not values or len(values) != len(weights):
        raise ValueError("values and weights must be non-empty and equal length")
    total = sum(weights)
    return sum(value * weight for value, weight in zip(values, weights)) / max(
        total,
        _EPSILON,
    )


def _weighted_std(values: Sequence[float], weights: Sequence[float]) -> float:
    center = _weighted_mean(values, weights)
    variance = _weighted_mean(
        [(value - center) ** 2 for value in values],
        weights,
    )
    return sqrt(max(variance, 0.0))


def _clip(value: float, lower: float, upper: float) -> float:
    return min(max(value, lower), upper)


def _sigmoid(value: float) -> float:
    if value >= 0:
        inverse = exp(-value)
        return 1.0 / (1.0 + inverse)
    positive = exp(value)
    return positive / (1.0 + positive)


def _symmetric_unit(value: float) -> float:
    return _clip(value * 2.0, -1.0, 1.0)


def _geometric_confidence(*parts: float) -> float:
    normalized = [_clip(part, 0.0, 1.0) for part in parts]
    if any(part <= 0.0 for part in normalized):
        return 0.0
    return _clip(exp(sum(log(part) for part in normalized) / len(normalized)), 0.0, 1.0)


def _cap_and_renormalize(
    shares: Mapping[str, float],
    cap: float,
) -> dict[str, float]:
    if not shares:
        return {}
    count = len(shares)
    effective_cap = max(cap, 1.0 / count)
    remaining = dict(shares)
    output = {key: 0.0 for key in shares}
    mass = 1.0
    while remaining:
        denominator = sum(remaining.values())
        if denominator <= _EPSILON:
            equal = mass / len(remaining)
            for key in remaining:
                output[key] += equal
            break
        allocations = {
            key: mass * value / denominator for key, value in remaining.items()
        }
        above = [
            key
            for key, value in allocations.items()
            if value > effective_cap + _EPSILON
        ]
        if not above:
            for key, value in allocations.items():
                output[key] += value
            break
        for key in above:
            output[key] += effective_cap
            mass -= effective_cap
            del remaining[key]
        if mass <= _EPSILON:
            break
    total = sum(output.values())
    if total <= _EPSILON:
        return {key: 1.0 / count for key in shares}
    return {key: value / total for key, value in output.items()}
