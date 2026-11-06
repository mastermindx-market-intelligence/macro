"""Fixed comparison of genuine typed owner projections, without corpus claims."""
from __future__ import annotations

import copy
import json
from decimal import Decimal, Inexact, Rounded, ROUND_DOWN, ROUND_HALF_EVEN, getcontext, localcontext

import pytest

from engine.neuralweb import market_memory_episode_comparison as comparison
from engine.neuralweb import market_memory_episode_features as features
from engine.neuralweb import market_memory_trusted as trusted
from engine.neuralweb import market_memory_projection as projection
from tests.test_market_memory_trusted import _candidate, _capture, _raw_regime, DEPLOYED_COMMIT
from tests.test_market_memory_episode_features import Policy


def capture(tmp_path, monkeypatch, growth=0.133, cutoff="2026-08-10T10:00:10Z", state_overrides=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    candidate = _candidate(monkeypatch, tmp_path, growth_score=growth)
    if state_overrides:
        raw = _raw_regime(growth_score=growth)
        raw.update(state_overrides)
        body = (json.dumps(raw, sort_keys=True) + "\n").encode()
        candidate.source.write_bytes(body)
        snapshot = projection.build_macro_regime_snapshot(candidate.source)
        stored = trusted.capture_trusted_regime_context(candidate.public, candidate.private,
            snapshot=snapshot, identity_evidence=candidate.identity_evidence,
            raw_source_body=body, deployed_commit=DEPLOYED_COMMIT)
    else:
        stored = _capture(candidate)
    reader = trusted.TrustedFileAsKnownAtReader(candidate.public)
    return features.read_episode_feature_capability(
        reader, reader.read_pinned_generation(),
        query_id=stored.capture_receipt["query_id"],
        subject_id=stored.packet["subject"]["subject_id"],
        query_cutoff=cutoff, policy=Policy())


def test_declared_q18_coordinate_conversion_precedes_final_rounding(tmp_path, monkeypatch):
    left = capture(tmp_path / "query", monkeypatch, growth=-0.998)
    right = capture(tmp_path / "candidate", monkeypatch, growth=0.133)
    result = comparison.compare_episode_features(left, right, policy=Policy())
    assert result["distance_q18"] == "0.113100000000000000"
    # This is a discriminating counterexample: the alternative unrounded
    # binary64 arithmetic changes the last q18 digit and is not our protocol.
    with localcontext() as context:
        context.prec = 80
        alternative = (abs(Decimal.from_float(-0.998) - Decimal.from_float(0.133)) / 10).quantize(
            Decimal("1e-18"), rounding=ROUND_HALF_EVEN)
    assert format(alternative, ".18f") == "0.113100000000000001"
    assert result["fit_status"] == "not_performed"
    assert result["fit_eligible"] is False
    assert result["authority"]["may_trade"] is False
    assert result["query_owner"]["generation_id"]
    assert result["candidate_feature_snapshot"]["content_sha256"]


def test_equal_and_extreme_domain_components(tmp_path, monkeypatch):
    low = capture(tmp_path / "low", monkeypatch, growth=-1.0)
    high = capture(tmp_path / "high", monkeypatch, growth=1.0)
    same = comparison.compare_episode_features(low, low, policy=Policy())
    assert same["distance_q18"] == "0.000000000000000000"
    opposite = comparison.compare_episode_features(low, high, policy=Policy())
    assert Decimal(opposite["components_exact_decimal"]["growth_score"]) == 1
    assert opposite["distance_q18"] == "0.200000000000000000"


@pytest.mark.parametrize("name,value", [("quad", "Q4"), ("liquidity_overlay", "expanding"), ("cycle_tag", "early")])
def test_category_mismatch_is_one_not_ordinal(tmp_path, monkeypatch, name, value):
    left = capture(tmp_path / "left", monkeypatch)
    right = capture(tmp_path / "right", monkeypatch, state_overrides={name: value})
    result = comparison.compare_episode_features(left, right, policy=Policy())
    assert result["components_exact_decimal"][name] == "1"
    assert result["distance_q18"] == "0.200000000000000000"


def test_q18_provenance_validation_rejects_corrupt_coordinate(tmp_path, monkeypatch):
    capability = capture(tmp_path, monkeypatch)
    value = features.disclose_episode_features(capability, policy=Policy(), for_comparison=True)
    value["coordinates"][0]["value_q18"] = "0.133000000000000999"
    with pytest.raises(comparison.EpisodeComparisonError, match="provenance"):
        comparison._coordinates(value, features.fixed_comparison_descriptor())


def test_current_rights_before_math_and_final_response(tmp_path, monkeypatch):
    left = capture(tmp_path / "left", monkeypatch)
    right = capture(tmp_path / "right", monkeypatch, growth=0.5)
    with pytest.raises(features.EpisodeFeatureAccessError):
        comparison.compare_episode_features(left, right,
            policy=Policy({"compare_retained_macro_feature"}))

    class RevokeBeforeReturn(Policy):
        def __init__(self):
            super().__init__()
            self.comparisons = 0

        def check(self, action, resource):
            if action == "compare_retained_macro_feature":
                self.comparisons += 1
                if self.comparisons >= 3:
                    raise PermissionError("revoked during computation")
            return super().check(action, resource)

    policy = RevokeBeforeReturn()
    with pytest.raises(features.EpisodeFeatureAccessError):
        comparison.compare_episode_features(left, right, policy=policy)
    assert policy.comparisons == 3


def test_no_outcomes_dicts_or_cross_cutoff_inputs(tmp_path, monkeypatch):
    left = capture(tmp_path / "left", monkeypatch)
    late = capture(tmp_path / "late", monkeypatch, cutoff="2026-08-10T10:00:11Z")
    with pytest.raises(comparison.EpisodeComparisonError, match="cutoff"):
        comparison.compare_episode_features(left, late, policy=Policy())
    with pytest.raises(features.EpisodeFeatureError):
        comparison.compare_episode_features({}, left, policy=Policy())
    with pytest.raises(TypeError):
        comparison.compare_episode_features(left, left, policy=Policy(), outcomes={"return": 1})


def test_stable_tie_rule_does_not_depend_on_input_iteration():
    first = {"distance_q18": "0.200000000000000000", "candidate": {"context_id": "mmctx_" + "1" * 64}}
    second = {"distance_q18": "0.200000000000000000", "candidate": {"context_id": "mmctx_" + "2" * 64}}
    assert sorted([second, first], key=comparison.comparison_order_key) == [first, second]
    with pytest.raises(comparison.EpisodeComparisonError):
        comparison.comparison_order_key({"distance_q18": float("nan"), "candidate": first["candidate"]})


def test_descriptor_mismatch_refuses_without_reinterpreting_coordinates(tmp_path, monkeypatch):
    left = capture(tmp_path / "left", monkeypatch)
    descriptor = features.fixed_comparison_descriptor()
    descriptor["content_sha256"] = "f" * 64
    monkeypatch.setattr(features, "fixed_comparison_descriptor", lambda: copy.deepcopy(descriptor))
    with pytest.raises(comparison.EpisodeComparisonError, match="descriptor"):
        comparison.compare_episode_features(left, left, policy=Policy())


def test_decimal_arithmetic_independent_of_ambient_context(tmp_path, monkeypatch):
    left = capture(tmp_path / "left", monkeypatch, growth=-0.998)
    right = capture(tmp_path / "right", monkeypatch)
    original = getcontext().prec
    try:
        getcontext().prec = 6
        first = comparison.compare_episode_features(left, right, policy=Policy())
        getcontext().prec = 30
        assert comparison.compare_episode_features(left, right, policy=Policy()) == first
    finally:
        getcontext().prec = original


def test_hostile_decimal_settings_do_not_change_capability_or_comparison(tmp_path, monkeypatch):
    left = capture(tmp_path / "left", monkeypatch, growth=-0.998)
    right = capture(tmp_path / "right", monkeypatch)
    expected_capability = features.disclose_episode_features(left, policy=Policy())
    expected_comparison = comparison.compare_episode_features(left, right, policy=Policy())
    with localcontext() as hostile:
        hostile.prec = 6
        hostile.rounding = ROUND_DOWN
        hostile.Emin = -3
        hostile.Emax = 3
        hostile.clamp = 1
        hostile.capitals = 0
        hostile.traps[Inexact] = True
        hostile.traps[Rounded] = True
        hostile.flags[Inexact] = True
        before = getcontext().copy()
        # Re-mint a genuine owner capability under hostile caller settings.
        repeated = capture(tmp_path / "left", monkeypatch, growth=-0.998)
        assert features.disclose_episode_features(repeated, policy=Policy()) == expected_capability
        assert comparison.compare_episode_features(left, right, policy=Policy()) == expected_comparison
        after = getcontext()
        assert (after.prec, after.rounding, after.Emin, after.Emax, after.clamp, after.capitals) == (
            before.prec, before.rounding, before.Emin, before.Emax, before.clamp, before.capitals)
        assert after.traps == before.traps and after.flags == before.flags
