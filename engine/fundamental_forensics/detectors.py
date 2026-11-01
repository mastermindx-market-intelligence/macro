"""Deterministic, evidence-linked forensic detectors for annual statement vintages."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Callable, Iterable

from .models import (
    Finding,
    FindingInput,
    FindingState,
    NormalizedObservation,
    StatementVintage,
    decimal_text,
    stable_id,
)
from .normalize import DetectorSpec, ForensicsRegistry


MIN_PERIOD_GAP_DAYS = 300
MAX_PERIOD_GAP_DAYS = 430

ISSUER_CLASSES: frozenset[str] = frozenset(
    {"industrial", "software", "bank", "insurance", "reit", "utility", "unknown"}
)
_INDUSTRIAL_OR_SOFTWARE: frozenset[str] = frozenset({"industrial", "software"})
DETECTOR_APPLICABILITY: dict[str, frozenset[str]] = {
    "margin_compression_despite_revenue_growth": _INDUSTRIAL_OR_SOFTWARE,
    "receivables_stretch": _INDUSTRIAL_OR_SOFTWARE,
    "inventory_build": _INDUSTRIAL_OR_SOFTWARE,
    "capital_intensity_rising": _INDUSTRIAL_OR_SOFTWARE,
    "accruals_trending_up": ISSUER_CLASSES - frozenset({"bank", "insurance"}),
}

NOT_EVALUABLE_REASON_NOT_APPLICABLE_FOR_ISSUER_CLASS = "not_applicable_for_issuer_class"
NOT_EVALUABLE_REASONS: frozenset[str] = frozenset(
    {
        "two_consecutive_annual_periods",
        "three_consecutive_annual_periods",
        "consecutive_annual_periods",
        "positive_revenue_required",
        "positive_revenue_and_nonzero_prior_balance_required",
        "nonzero_revenue_and_positive_capex_required",
        "nonzero_prior_operating_income_required",
        "positive_assets_required",
        "detector_rule_unavailable_at_as_of",
        NOT_EVALUABLE_REASON_NOT_APPLICABLE_FOR_ISSUER_CLASS,
    }
)


def issuer_class_for_sic(sic: str | int | None) -> str:
    """Map an SEC SIC code onto an issuer class.

    6020–6199 and 6710–6719 are bank; 6300–6411 insurance; 6798 reit;
    4900–4991 utility; 7370–7379 software; any other parseable code industrial;
    None or unparseable unknown.
    """
    code = _parse_sic(sic)
    if code is None:
        return "unknown"
    if 6020 <= code <= 6199 or 6710 <= code <= 6719:
        return "bank"
    if 6300 <= code <= 6411:
        return "insurance"
    if code == 6798:
        return "reit"
    if 4900 <= code <= 4991:
        return "utility"
    if 7370 <= code <= 7379:
        return "software"
    return "industrial"


def _parse_sic(sic: str | int | None) -> int | None:
    if sic is None or isinstance(sic, bool):
        return None
    if isinstance(sic, int):
        return sic if sic >= 0 else None
    text = str(sic).strip()
    if not text or not text.isdigit():
        return None
    return int(text)


def _gated_issuer_class(detector_id: str, issuer_sic: str | int | None) -> str | None:
    """Return the issuer class when this detector must not evaluate, else None.

    None SIC and class ``unknown`` gate nothing and record nothing new.
    """
    if issuer_sic is None:
        return None
    issuer_class = issuer_class_for_sic(issuer_sic)
    if issuer_class == "unknown":
        return None
    applicable = DETECTOR_APPLICABILITY.get(detector_id)
    if applicable is None or issuer_class in applicable:
        return None
    return issuer_class


def _decimal(observation: NormalizedObservation) -> Decimal:
    return Decimal(observation.value)


def _growth(current: Decimal, prior: Decimal) -> Decimal | None:
    if prior == 0:
        return None
    return (current - prior) / abs(prior) * Decimal("100")


def _change_exceeds_base(current: Decimal, prior: Decimal) -> bool:
    """A move larger than its own base: the percentage reading rests on a small base."""
    return abs(current - prior) > abs(prior)


def _materiality(
    metric: str, current: Decimal, prior: Decimal, current_revenue: Decimal
) -> tuple[dict[str, Decimal], tuple[str, ...]]:
    """A26: the amount behind a growth reading, sized against the revenue it is read beside.

    A percentage change alone hides whether the move matters; the absolute change and
    its share of current revenue let a reader judge materiality, and ``small_base``
    marks a move larger than its own base. Exposure only: no verdict changes here.
    """
    change = current - prior
    derived = {f"{metric}_change": change}
    if current_revenue > 0:
        derived[f"{metric}_change_share_of_revenue_pp"] = change / current_revenue * Decimal("100")
    caveats = (f"small_base:{metric}",) if _change_exceeds_base(current, prior) else ()
    return derived, caveats


def _basis_changes(source_observations: list[NormalizedObservation]) -> tuple[str, ...]:
    """A26: a metric read under different mapping rules, tiers or units across periods.

    A change between periods mapped on different bases may be a definition shift,
    not an economic one, so it is named beside the reading rather than hidden in it.
    """
    bases: dict[str, set[tuple[str, str, str]]] = {}
    for item in source_observations:
        bases.setdefault(item.metric, set()).add(
            (item.mapping_rule_id, item.mapping_tier, item.unit)
        )
    return tuple(sorted(f"basis_changed:{metric}" for metric, seen in bases.items() if len(seen) > 1))


def _periods_are_consecutive(vintages: tuple[StatementVintage, ...]) -> bool:
    if len(vintages) < 2:
        return False
    ends = [date.fromisoformat(item.period_end) for item in vintages]
    return all(
        MIN_PERIOD_GAP_DAYS <= (later - earlier).days <= MAX_PERIOD_GAP_DAYS
        for earlier, later in zip(ends, ends[1:])
    )


def _observation(
    vintage: StatementVintage,
    metric: str,
    observations: dict[str, NormalizedObservation],
) -> NormalizedObservation | None:
    observation_id = vintage.metrics().get(metric)
    return observations.get(observation_id) if observation_id else None


def _collect_inputs(
    pairs: Iterable[tuple[StatementVintage, str]],
    observations: dict[str, NormalizedObservation],
) -> tuple[tuple[FindingInput, ...], tuple[str, ...], list[NormalizedObservation]]:
    inputs: list[FindingInput] = []
    missing: list[str] = []
    source_observations: list[NormalizedObservation] = []
    for vintage, metric in pairs:
        item = _observation(vintage, metric, observations)
        if item is None:
            missing.append(f"{metric}@{vintage.period_end}")
            continue
        inputs.append(
            FindingInput(
                metric=metric,
                period_end=vintage.period_end,
                value=item.value,
                observation_id=item.observation_id,
                fact_ids=item.fact_ids,
            )
        )
        source_observations.append(item)
    inputs.sort(key=lambda item: (item.period_end, item.metric, item.observation_id))
    return tuple(inputs), tuple(sorted(missing)), source_observations


def _finding(
    spec: DetectorSpec,
    registry: ForensicsRegistry,
    *,
    entity_cik: str,
    state: FindingState,
    period_ends: tuple[str, ...],
    inputs: tuple[FindingInput, ...],
    source_observations: list[NormalizedObservation],
    missing_inputs: tuple[str, ...] = (),
    derived_values: dict[str, Decimal | str] | None = None,
    computed_at: datetime,
    limitations: tuple[str, ...] = (),
) -> Finding:
    evidence_observation_ids = tuple(sorted(item.observation_id for item in source_observations))
    evidence_fact_ids = tuple(
        sorted({fact_id for item in source_observations for fact_id in item.fact_ids})
    )
    all_source_ready = bool(source_observations) and all(
        item.source_event_at is not None for item in source_observations
    )
    source_ready_at = (
        max(item.source_event_at for item in source_observations if item.source_event_at)
        if all_source_ready
        else None
    )
    recorded_ready_at = (
        max(item.recorded_at for item in source_observations) if source_observations else None
    )
    derived = tuple(
        sorted(
            (key, decimal_text(value))
            for key, value in (derived_values or {}).items()
        )
    )
    finding_id = stable_id(
        "finding",
        spec.detector_id,
        registry.detector_pack_version,
        entity_cik,
        state.value,
        period_ends,
        evidence_observation_ids,
        missing_inputs,
        derived,
    )
    return Finding(
        finding_id=finding_id,
        detector_id=spec.detector_id,
        detector_version=registry.detector_pack_version,
        detector_rule_available_at=registry.detector_pack_available_at,
        entity_cik=entity_cik,
        state=state,
        applicability="insufficient_evidence" if state is FindingState.NOT_EVALUABLE else "applicable",
        formula=spec.formula,
        thresholds=spec.thresholds,
        derived_values=derived,
        period_ends=period_ends,
        inputs=inputs,
        missing_inputs=tuple(sorted(missing_inputs)),
        evidence_observation_ids=evidence_observation_ids,
        evidence_fact_ids=evidence_fact_ids,
        source_ready_at=source_ready_at,
        recorded_ready_at=recorded_ready_at,
        computed_at=computed_at,
        limitations=tuple(sorted(limitations)),
    )


def _not_evaluable(
    spec: DetectorSpec,
    registry: ForensicsRegistry,
    *,
    entity_cik: str,
    period_ends: tuple[str, ...],
    inputs: tuple[FindingInput, ...],
    source_observations: list[NormalizedObservation],
    missing_inputs: tuple[str, ...],
    computed_at: datetime,
    limitations: tuple[str, ...] = (),
) -> Finding:
    return _finding(
        spec,
        registry,
        entity_cik=entity_cik,
        state=FindingState.NOT_EVALUABLE,
        period_ends=period_ends,
        inputs=inputs,
        source_observations=source_observations,
        missing_inputs=missing_inputs,
        computed_at=computed_at,
        limitations=limitations,
    )


def _two_period_detector(
    spec: DetectorSpec,
    registry: ForensicsRegistry,
    selected: tuple[StatementVintage, ...],
    observations: dict[str, NormalizedObservation],
    *,
    metrics: tuple[str, ...],
    computed_at: datetime,
    compute: Callable[[dict[tuple[str, str], Decimal]], tuple[bool | None, dict[str, Decimal], tuple[str, ...], tuple[str, ...]]],
    entity_cik: str,
) -> Finding:
    if len(selected) < 2:
        return _not_evaluable(
            spec, registry, entity_cik=entity_cik, period_ends=tuple(v.period_end for v in selected),
            inputs=(), source_observations=[], missing_inputs=("two_consecutive_annual_periods",),
            computed_at=computed_at,
        )
    pair = selected[-2:]
    period_ends = tuple(item.period_end for item in pair)
    pairs = tuple((vintage, metric) for vintage in pair for metric in metrics)
    inputs, missing, source_items = _collect_inputs(pairs, observations)
    if not _periods_are_consecutive(pair):
        missing = tuple(sorted(set(missing) | {"consecutive_annual_periods"}))
    if missing:
        return _not_evaluable(
            spec, registry, entity_cik=entity_cik, period_ends=period_ends, inputs=inputs,
            source_observations=source_items, missing_inputs=missing, computed_at=computed_at,
        )
    values = {
        (item.period_end, item.metric): Decimal(item.value)
        for item in inputs
    }
    triggered, derived, failures, limitations = compute(values)
    limitations = tuple(limitations) + _basis_changes(source_items)
    if triggered is None:
        return _not_evaluable(
            spec, registry, entity_cik=entity_cik, period_ends=period_ends, inputs=inputs,
            source_observations=source_items, missing_inputs=failures, computed_at=computed_at,
            limitations=limitations,
        )
    return _finding(
        spec,
        registry,
        entity_cik=entity_cik,
        state=FindingState.TRIGGERED if triggered else FindingState.CLEAR,
        period_ends=period_ends,
        inputs=inputs,
        source_observations=source_items,
        derived_values=derived,
        computed_at=computed_at,
        limitations=limitations,
    )


def _margin_compute(spec: DetectorSpec, periods: tuple[str, str]):
    thresholds = spec.threshold_map()
    minimum_growth = Decimal(thresholds["min_revenue_growth_pp"])

    def compute(values):
        prior, current = periods
        prior_revenue, current_revenue = values[(prior, "revenue")], values[(current, "revenue")]
        # POSITIVE, not merely non-zero. Gross margin is gross_profit/revenue;
        # a negative denominator flips the ratio's sign, so comparing a
        # sign-flipped current margin against a prior margin answers a question
        # nobody asked while still emitting a TRIGGERED/CLEAR verdict. Absence
        # of a usable denominator is an evaluability failure, not a reading.
        if prior_revenue <= 0 or current_revenue <= 0:
            return None, {}, ("positive_revenue_required",), ()
        revenue_growth = _growth(current_revenue, prior_revenue)
        gross_margin_prior = values[(prior, "gross_profit")] / prior_revenue * Decimal("100")
        gross_margin_current = values[(current, "gross_profit")] / current_revenue * Decimal("100")
        fired = revenue_growth >= minimum_growth and gross_margin_current < gross_margin_prior
        caveats = ("small_base:revenue",) if _change_exceeds_base(current_revenue, prior_revenue) else ()
        return fired, {
            "revenue_growth_pp": revenue_growth,
            "gross_margin_prior_pp": gross_margin_prior,
            "gross_margin_current_pp": gross_margin_current,
            "gross_margin_change_pp": gross_margin_current - gross_margin_prior,
        }, (), caveats

    return compute


def _working_capital_compute(spec: DetectorSpec, periods: tuple[str, str], metric: str, threshold_key: str):
    gap_threshold = Decimal(spec.threshold_map()[threshold_key])

    def compute(values):
        prior, current = periods
        prior_revenue, current_revenue = values[(prior, "revenue")], values[(current, "revenue")]
        prior_metric, current_metric = values[(prior, metric)], values[(current, metric)]
        if prior_revenue == 0 or prior_metric == 0 or current_revenue <= 0:
            return None, {}, ("positive_revenue_and_nonzero_prior_balance_required",), ()
        revenue_growth = _growth(current_revenue, prior_revenue)
        metric_growth = _growth(current_metric, prior_metric)
        growth_gap = metric_growth - revenue_growth
        derived = {
            "revenue_growth_pp": revenue_growth,
            f"{metric}_growth_pp": metric_growth,
            "growth_gap_pp": growth_gap,
        }
        sized, caveats = _materiality(metric, current_metric, prior_metric, current_revenue)
        derived.update(sized)
        if _change_exceeds_base(current_revenue, prior_revenue):
            caveats += ("small_base:revenue",)
        return growth_gap > gap_threshold, derived, (), caveats

    return compute


def _capital_intensity_compute(spec: DetectorSpec, periods: tuple[str, str]):
    gap_threshold = Decimal(spec.threshold_map()["growth_gap_pp"])

    def compute(values):
        prior, current = periods
        prior_revenue, current_revenue = values[(prior, "revenue")], values[(current, "revenue")]
        prior_capex, current_capex = values[(prior, "capital_expenditures")], values[(current, "capital_expenditures")]
        prior_oi, current_oi = values[(prior, "operating_income")], values[(current, "operating_income")]
        if prior_revenue == 0 or prior_capex == 0 or current_capex <= 0:
            return None, {}, ("nonzero_revenue_and_positive_capex_required",), ()
        revenue_growth = _growth(current_revenue, prior_revenue)
        capex_growth = _growth(current_capex, prior_capex)
        capex_revenue_gap = capex_growth - revenue_growth
        derived = {
            "revenue_growth_pp": revenue_growth,
            "capital_expenditures_growth_pp": capex_growth,
            "capex_revenue_growth_gap_pp": capex_revenue_gap,
        }
        sized, caveats = _materiality(
            "capital_expenditures", current_capex, prior_capex, current_revenue
        )
        derived.update(sized)
        if _change_exceeds_base(current_revenue, prior_revenue):
            caveats += ("small_base:revenue",)
        if current_oi <= 0:
            return capex_revenue_gap > gap_threshold, derived, (), caveats + (
                "nonpositive_operating_income_revenue_only_branch",
            )
        if prior_oi == 0:
            return None, {}, ("nonzero_prior_operating_income_required",), ()
        operating_income_growth = _growth(current_oi, prior_oi)
        capex_oi_gap = capex_growth - operating_income_growth
        derived.update({
            "operating_income_growth_pp": operating_income_growth,
            "capex_operating_income_growth_gap_pp": capex_oi_gap,
        })
        if _change_exceeds_base(current_oi, prior_oi):
            caveats += ("small_base:operating_income",)
        fired = capex_revenue_gap > gap_threshold and capex_oi_gap > gap_threshold
        return fired, derived, (), caveats

    return compute


def _accruals_detector(
    spec: DetectorSpec,
    registry: ForensicsRegistry,
    selected: tuple[StatementVintage, ...],
    observations: dict[str, NormalizedObservation],
    *,
    computed_at: datetime,
    entity_cik: str,
) -> Finding:
    if len(selected) < 3:
        return _not_evaluable(
            spec, registry, entity_cik=entity_cik, period_ends=tuple(v.period_end for v in selected),
            inputs=(), source_observations=[], missing_inputs=("three_consecutive_annual_periods",),
            computed_at=computed_at,
        )
    window = selected[-3:]
    period_ends = tuple(item.period_end for item in window)
    pairs = tuple(
        (vintage, metric)
        for vintage in window
        for metric in ("net_income", "operating_cash_flow", "assets")
    )
    inputs, missing, source_items = _collect_inputs(pairs, observations)
    if not _periods_are_consecutive(window):
        missing = tuple(sorted(set(missing) | {"consecutive_annual_periods"}))
    if missing:
        return _not_evaluable(
            spec, registry, entity_cik=entity_cik, period_ends=period_ends, inputs=inputs,
            source_observations=source_items, missing_inputs=missing, computed_at=computed_at,
        )
    values = {(item.period_end, item.metric): Decimal(item.value) for item in inputs}
    ratios: list[Decimal] = []
    for period_end in period_ends:
        assets = values[(period_end, "assets")]
        if assets <= 0:
            return _not_evaluable(
                spec, registry, entity_cik=entity_cik, period_ends=period_ends, inputs=inputs,
                source_observations=source_items, missing_inputs=("positive_assets_required",),
                computed_at=computed_at,
            )
        ratios.append(
            (values[(period_end, "net_income")] - values[(period_end, "operating_cash_flow")])
            / assets
        )
    change = ratios[-1] - ratios[0]
    threshold = Decimal(spec.threshold_map()["min_three_period_increase"])
    fired = change >= threshold and ratios[-1] > ratios[0]
    derived = {f"accrual_ratio_{period}": ratio for period, ratio in zip(period_ends, ratios)}
    derived["accrual_ratio_change"] = change
    return _finding(
        spec,
        registry,
        entity_cik=entity_cik,
        state=FindingState.TRIGGERED if fired else FindingState.CLEAR,
        period_ends=period_ends,
        inputs=inputs,
        source_observations=source_items,
        derived_values=derived,
        computed_at=computed_at,
        limitations=_basis_changes(source_items),
    )


def evaluate_detectors(
    normalized_observations: tuple[NormalizedObservation, ...],
    selected_vintages: tuple[StatementVintage, ...],
    registry: ForensicsRegistry,
    *,
    computed_at: datetime,
    detector_rules_eligible: bool = True,
    entity_cik: str,
    issuer_sic: str | int | None = None,
) -> tuple[Finding, ...]:
    """Evaluate every registered detector; absence always becomes an explicit state."""
    observations = {item.observation_id: item for item in normalized_observations}
    selected = tuple(sorted(selected_vintages, key=lambda item: item.period_end))
    results: list[Finding] = []
    for spec in registry.detectors:
        if not detector_rules_eligible:
            results.append(
                _not_evaluable(
                    spec,
                    registry,
                    entity_cik=entity_cik,
                    period_ends=tuple(item.period_end for item in selected),
                    inputs=(),
                    source_observations=[],
                    missing_inputs=("detector_rule_unavailable_at_as_of",),
                    computed_at=computed_at,
                )
            )
            continue
        gated_class = _gated_issuer_class(spec.detector_id, issuer_sic)
        if gated_class is not None:
            results.append(
                _not_evaluable(
                    spec,
                    registry,
                    entity_cik=entity_cik,
                    period_ends=tuple(item.period_end for item in selected),
                    inputs=(),
                    source_observations=[],
                    missing_inputs=(NOT_EVALUABLE_REASON_NOT_APPLICABLE_FOR_ISSUER_CLASS,),
                    computed_at=computed_at,
                    limitations=(f"issuer_class:{gated_class}",),
                )
            )
            continue
        if spec.detector_id == "accruals_trending_up":
            results.append(
                _accruals_detector(
                    spec, registry, selected, observations, computed_at=computed_at,
                    entity_cik=entity_cik,
                )
            )
            continue
        pair_periods = (
            tuple(item.period_end for item in selected[-2:])
            if len(selected) >= 2 else ("", "")
        )
        if spec.detector_id == "margin_compression_despite_revenue_growth":
            metrics = ("revenue", "gross_profit")
            compute = _margin_compute(spec, pair_periods)
        elif spec.detector_id == "receivables_stretch":
            metrics = ("revenue", "accounts_receivable")
            compute = _working_capital_compute(
                spec, pair_periods, "accounts_receivable", "growth_gap_pp"
            )
        elif spec.detector_id == "inventory_build":
            metrics = ("revenue", "inventory")
            compute = _working_capital_compute(spec, pair_periods, "inventory", "growth_gap_pp")
        elif spec.detector_id == "capital_intensity_rising":
            metrics = ("revenue", "capital_expenditures", "operating_income")
            compute = _capital_intensity_compute(spec, pair_periods)
        else:
            raise ValueError(f"unknown detector in registry: {spec.detector_id}")
        results.append(
            _two_period_detector(
                spec,
                registry,
                selected,
                observations,
                metrics=metrics,
                computed_at=computed_at,
                compute=compute,
                entity_cik=entity_cik,
            )
        )
    return tuple(sorted(results, key=lambda item: item.detector_id))
