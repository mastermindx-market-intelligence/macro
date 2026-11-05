"""Whole-batch synthetic staging -> prefix -> diagnostic -> review composition.

The owner supplies invented inputs and an explicit test transport. There is no
runtime issuer, candidate registration, publication, holdout or production path.
Absence of that test seam refuses before accounting. All actual transport remains
in the existing prefix driver; returned engineering observations grant nothing.
"""
from dataclasses import dataclass, field, replace
import hashlib

from engine.research_codegen import bridge, prefix_driver, staging_accounting, plan_engine_provider
from engine.research_factory.review_queue import diagnostic_review_packet


class StagedCycleRefused(ValueError):
    pass


@dataclass(frozen=True)
class StagedVariant:
    variant_id: str
    source: bridge.BoundBytes
    run: bridge.SyntheticRun
    spec: prefix_driver.PrefixTransportSpec
    # A scripted malformed-output control is not a temporal-bias experiment.
    expected: str = "diagnostic"


@dataclass(frozen=True)
class StagedVariantResult:
    variant_id: str
    status: str
    run: bridge.SyntheticRun
    outcome: prefix_driver.PrefixDriverOutcome | None
    diagnostic: bytes | None
    review_packet: dict | None
    reason: str | None = None


@dataclass(frozen=True)
class StagedCycleResult:
    status: str
    staged: staging_accounting.StagedAccountingReadback
    variants: tuple[StagedVariantResult, ...]
    scope: str = field(default="SYNTHETIC_ENGINEERING_ONLY", init=False)
    physical_acceptance: bool = field(default=False, init=False)
    scientific_acceptance: str = field(default="UNQUALIFIED", init=False)
    authority_granted: bool = field(default=False, init=False)


def _require(condition, reason):
    if not condition:
        raise StagedCycleRefused(reason)


def _preflight(variants, configurations, expected_generation, commission, engines, *, providers=False):
    _require(type(commission) is bridge.SyntheticTestCommission,
             "SYNTHETIC_COMMISSION_REQUIRED")
    expected = staging_accounting._load_bound_json(expected_generation, "EXPECTED")
    family, _, _, _, emitted, _, _ = staging_accounting._validate_expected(expected, commission)
    _require(type(variants) is tuple and len(variants) == len(emitted), "WHOLE_BATCH_REQUIRED")
    _require(type(engines) is tuple and len(engines) == len(variants), "TEST_ENGINE_MAP_INVALID")
    _require(type(configurations) is tuple, "CONFIG_MAP_INVALID")
    configured = set()
    for config in configurations:
        _require(type(config) is staging_accounting.ScientificConfigBinding,
                 "CONFIG_BINDING_INVALID")
        staging_accounting._scientific_doc(config, family, emitted)
        _require(config.variant_id not in configured, "DUPLICATE_CONFIG_BINDING")
        configured.add(config.variant_id)
    _require(configured == set(emitted), "WHOLE_CONFIG_MAP_REQUIRED")
    seen, diagnostics = set(), set()
    for variant, engine in zip(variants, engines):
        _require(type(variant) is StagedVariant, "EXACT_VARIANT_REQUIRED")
        _require(variant.variant_id in emitted and variant.variant_id not in seen,
                 "VARIANT_SET_MISMATCH")
        seen.add(variant.variant_id)
        _require(variant.expected in ("diagnostic", "scripted_malformed_output"),
                 "UNKNOWN_ENGINEERING_EXPECTATION")
        if providers:
            _require(type(engine) is plan_engine_provider.PlanBoundEngineProvider, "EXACT_TEST_PROVIDER_REQUIRED")
        else:
            _require(engine is not None and not callable(engine)
                     and callable(getattr(engine, "run", None)), "TEST_ENGINE_REQUIRED")
        run = variant.run
        _require(type(run) is bridge.SyntheticRun and run.outputs == (), "EMPTY_RUN_REQUIRED")
        _require(run.expected_generation == expected_generation, "GENERATION_BINDING_MISMATCH")
        source_sha, config_sha, _ = emitted[variant.variant_id]
        _require(run.identity.source_sha256 == source_sha
                 and run.identity.config_sha256 == config_sha, "VARIANT_IDENTITY_MISMATCH")
        staging_accounting._bound(variant.source, "SOURCE")
        _require(variant.source.sha256 == source_sha
                 and 0 < variant.source.size <= prefix_driver.MAX_SOURCE_BYTES,
                 "SOURCE_IDENTITY_MISMATCH")
        try:
            variant.source.raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise StagedCycleRefused("SOURCE_UTF8_REQUIRED") from exc
        _require(type(variant.spec) is prefix_driver.PrefixTransportSpec,
                 "EXACT_TRANSPORT_SPEC_REQUIRED")
        _require(run.identity.diagnostic_id not in diagnostics, "DUPLICATE_DIAGNOSTIC")
        diagnostics.add(run.identity.diagnostic_id)
    _require(seen == set(emitted), "VARIANT_SET_MISMATCH")


def run_staged_cycle(*, commission, run_id, expected_generation, configurations,
                     history_anchor, variants, synthetic_test_engines=None,
                     synthetic_test_providers=None):
    """Account the entire frozen emitted set once, then join every owner consumer.

    ``synthetic_test_engines`` is a dependency-injection seam for engineering
    fixtures, never a qualified-runtime switch. Real/default invocation remains
    dormant. The ledger owner keeps its original history and budget. The caller's
    input readbacks are never trusted; every run is rebound to the actual durable
    staging return. All causal inputs/plans are then validated before the first
    transport call. An invalid input remains charged, with no attempted variants.
    Any unexpected refusal or unknown effect
    stops later variants; all charged variants remain represented in the result.
    """
    _require(synthetic_test_engines is not None or synthetic_test_providers is not None,
             "RUNTIME_QUALIFICATION_UNAVAILABLE")
    _require((synthetic_test_engines is None) != (synthetic_test_providers is None),
             "ONE_TEST_TRANSPORT_SOURCE_REQUIRED")
    providers = synthetic_test_providers is not None
    sources = synthetic_test_providers if providers else synthetic_test_engines
    _preflight(variants, configurations, expected_generation, commission, sources, providers=providers)
    staged = staging_accounting.stage_synthetic_generation(commission=commission, run_id=run_id,
        expected_generation=expected_generation, configurations=configurations,
        history_anchor=history_anchor)
    runs = tuple(replace(variant.run, expected_generation=staged.expected_generation,
                         trial_readback=staged.trial_readback) for variant in variants)
    # This is a first-use adapter, not a retained-outcome reconciliation owner.
    # Existing (including partially existing) generation may already have run.
    # A new receipt/run_id never authorizes replay of its deterministic effects.
    if staged.newly_recorded_count != len(variants):
        return StagedCycleResult("RECONCILIATION_REQUIRED", staged, tuple(
            StagedVariantResult(variant.variant_id, "NOT_ATTEMPTED_EXISTING_GENERATION", run,
                                None, None, None, "RETAINED_OUTCOME_RECONCILIATION_REQUIRED")
            for variant, run in zip(variants, runs)))
    prepared_runs, operations = [], set()
    try:
        for variant, run in zip(variants, runs):
            prepared = bridge.prepare_synthetic_inputs(run, commission=commission)
            plans = prefix_driver.prepare_prefix_plans(prepared, source=variant.source,
                spec=variant.spec, config_sha256=run.identity.config_sha256)
            _require(bool(plans), "EMPTY_PREFIX_PLAN")
            for plan in plans:
                _require(plan[4] not in operations, "DUPLICATE_PREFIX_OPERATION")
                operations.add(plan[4])
            prepared_runs.append(prepared)
    except (bridge.BridgeRefused, prefix_driver.PrefixDriverRefused, StagedCycleRefused):
        return StagedCycleResult("REFUSED", staged, tuple(
            StagedVariantResult(variant.variant_id, "NOT_ATTEMPTED_INVALID_BATCH", run,
                                None, None, None, "BATCH_INPUT_PREFLIGHT_REFUSED")
            for variant, run in zip(variants, runs)))
    results, stopped, unknown = [], False, False
    for variant, run, prepared, engine in zip(variants, runs, prepared_runs, sources):
        if stopped:
            results.append(StagedVariantResult(variant.variant_id, "NOT_ATTEMPTED_AFTER_REFUSAL",
                                               run, None, None, None))
            continue
        selected = {"engine_provider" if providers else "engine": engine}
        outcome = prefix_driver.run_prefix_driver(prepared, source=variant.source,
            **selected, spec=variant.spec, config_sha256=run.identity.config_sha256)
        unsettled = any(attempt.execution_uncertain or attempt.reconciliation_required
                        or not attempt.cleanup_confirmed for attempt in outcome.attempts)
        raw = None
        try:
            raw = (prefix_driver.connect_prepared_outputs(run, outcome, commission=commission)
                   if outcome.completed else bridge.compute_synthetic_diagnostic(run, commission=commission))
            identity = replace(run.identity, artifact_sha256=hashlib.sha256(raw).hexdigest(),
                               artifact_bytes=len(raw))
            public = bridge.public_diagnostic(bridge.decode_bound_artifact(raw, expected=identity,
                                                                          commission=commission))
            packet = diagnostic_review_packet(public, engineering_receipts=dict(run=run,
                commission=commission, source=variant.source, staged=staged, outcome=outcome))
        except ValueError:
            # Retain the actual attempt even when a later pure consumer rejects.
            # Never turn a reporting failure into another transport invocation.
            results.append(StagedVariantResult(variant.variant_id,
                "EFFECT_UNKNOWN" if unsettled else "REFUSED", run, outcome, raw, None,
                "DIAGNOSTIC_COMPOSITION_REFUSED"))
            unknown, stopped = unknown or unsettled, True
            continue
        matched = (outcome.completed and public["status"] == "DIAGNOSTIC_ONLY"
                   and variant.expected == "diagnostic")
        if variant.expected == "scripted_malformed_output":
            matched = (not outcome.completed and bool(outcome.attempts) and not unsettled
                       and len(outcome.refusal_reasons) == 1 and outcome.refusal_reasons[0] in
                       ("OUTPUT_CONTRACT_REFUSED", "INVALID_OUTPUT_JSON", "NONFINITE_JSON")
                       and outcome.attempts[-1].workload_confirmed
                       and public["status"] == "REFUSED")
        status = "EFFECT_UNKNOWN" if unsettled else ("EXPECTED_ENGINEERING_RESULT" if matched else "REFUSED")
        results.append(StagedVariantResult(variant.variant_id, status, run, outcome, raw, packet))
        unknown = unknown or unsettled
        stopped = unsettled or not matched
    return StagedCycleResult("EFFECT_UNKNOWN" if unknown else
                            ("REFUSED" if stopped else "DIAGNOSTIC_CYCLE_COMPLETE"),
                            staged, tuple(results))
