"""Synthetic PTSE conformance tests; never source or empirical qualification."""
from __future__ import annotations

import copy
import hashlib
import json
import unittest

from research.options_estate.ptse_contract import (
    ACTIONS, AUTHORITY_KEYS, ContractViolation, ConsumerBinding,
    build_context, canonical_json, reconcile_observation, read_optional_context,
    validate_context,
)

DECISION = "2026-10-02T20:00:00Z"
NOW = "2026-10-02T20:04:00Z"


def ref(name: str, owner: str = "fixture-owner") -> dict:
    return {"owner_ref": owner, "artifact_id": "fixture:" + name,
            "sha256": hashlib.sha256(name.encode()).hexdigest()}


def inputs(action: str = "NEW_ENTRY", applicability: str = "APPLICABLE") -> tuple[dict, dict]:
    observation = {
        "market": "US", "instrument_id": "fixture:SPY",
        "market_session": "2026-10-02", "cadence": "DAILY", "session_scope": "REGULAR", "decision_at": DECISION,
        "issued_at": "2026-10-02T20:02:00Z", "valid_until": "2026-10-02T21:00:00Z",
        "calendar_ref": ref("calendar"), "freshness_ref": ref("freshness"),
        "source_manifest_ref": ref("manifest"), "calculation_receipt_ref": ref("calculation"),
        "producer_revision": "a" * 40, "feature_version": "fixture-features-v1",
        "evidence_grade": "SYNTHETIC", "reconstructed_at": None,
        "supersedes_ref": None, "correction_reason": None,
        "facts": [{
            "feature_id": "fixture.price.log_v20", "owner_ref": "fixture-price-owner",
            "source_artifact_ref": ref("price-fact", "fixture-price-owner"),
            "economic_time": "2026-10-02T19:59:00Z", "economic_time_role": "OBSERVATION",
            "known_at": {"earliest": "2026-10-02T19:59:30Z", "latest": "2026-10-02T19:59:30Z",
                         "precision": "EXACT", "evidence_ref": ref("availability")},
            "valid_until": "2026-10-02T21:00:00Z",
            "value": 0.0, "unit": "DIMENSIONLESS", "status": "OBSERVED",
            "method_kind": "DETERMINISTIC_COMPUTATION", "calculation_version": "fixture-calc-v1",
            "evidence_grade": "SYNTHETIC",
            "coverage": {"numerator": 1, "denominator": 1, "missing_count": 0,
                         "population_ref": ref("population")},
            "source_scope": {"instrument_id": "fixture:SPY", "session_scope": "REGULAR",
                             "population_ref": ref("population"), "position_scope": "NOT_APPLICABLE",
                             "side_semantics": "NOT_APPLICABLE"},
            "limitations": ["Synthetic conformance fixture; not market evidence."], "null_reason": None,
        }],
    }
    assessment = {
        "episode_id": "fixture:episode-1", "security_id": "fixture:AMD",
        "company_id": "fixture:company-AMD", "identity_epoch": "fixture:epoch-1",
        "candidate_generation_id": "fixture:generation-1",
        "cohort_ref": ref("full-candidate-cohort", "fixture-prophet-owner"),
        "strategy_id": "fixture:swing", "strategy_version": "fixture-strategy-v1",
        "holding_horizon_ref": ref("holding-horizon", "fixture-strategy-owner"),
        "action": action, "decision_at": DECISION, "issued_at": "2026-10-02T20:03:00Z",
        "forecast_horizon_sessions": 5, "forecast_end_session": "2026-10-09",
        "calendar_ref": ref("calendar"), "target_version": "fixture-action-target-v1",
        "applicability": applicability, "applicability_reason": "Fixture incumbent eligibility.",
        "eligibility_ref": ref("eligibility", "fixture-prophet-owner") if applicability != "UNKNOWN" else None,
        "position_ref": None, "geometry_ref": None, "risk_budget_ref": None, "prior_exit_episode_ref": None,
        "evidence_status": "OBSERVED_CONTEXT_ONLY", "estimate_status": "NOT_FITTED", "estimate": None,
        "drivers": ["fixture.price.log_v20"], "contradictions": [],
        "authority": {key: False for key in AUTHORITY_KEYS},
    }
    if applicability == "APPLICABLE":
        if action in {"CONTINUATION", "ADD", "DERISK"}:
            assessment["position_ref"] = ref("position", "fixture-portfolio-owner")
        if action in {"PULLBACK_BUY", "ADD"}:
            assessment["geometry_ref"] = ref("geometry", "fixture-prophet-owner")
        if action == "ADD":
            assessment["risk_budget_ref"] = ref("risk-budget", "fixture-portfolio-owner")
        if action == "REENTRY":
            assessment["prior_exit_episode_ref"] = ref("paired-derisk-episode", "fixture-portfolio-owner")
    return observation, assessment


def binding(artifact, *, lane: str = "TEST", **updates) -> ConsumerBinding:
    p = artifact.to_dict(); o, a = p["observation"], p["assessment"]
    kw = dict(artifact_sha256=artifact.sha256, producer_revision=o["producer_revision"],
              source_manifest_sha256=o["source_manifest_ref"]["sha256"],
              market=o["market"], cadence=o["cadence"], session_scope=o["session_scope"],
              observation_instrument_id=o["instrument_id"],
              episode_id=a["episode_id"], security_id=a["security_id"],
              company_id=a["company_id"], identity_epoch=a["identity_epoch"],
              candidate_generation_id=a["candidate_generation_id"],
              cohort_sha256=a["cohort_ref"]["sha256"], strategy_id=a["strategy_id"],
              strategy_version=a["strategy_version"], holding_horizon_sha256=a["holding_horizon_ref"]["sha256"],
              action=a["action"], decision_at=a["decision_at"],
              forecast_horizon_sessions=a["forecast_horizon_sessions"], forecast_end_session=a["forecast_end_session"],
              calendar_sha256=a["calendar_ref"]["sha256"], target_version=a["target_version"],
              accepted_grades=frozenset({o["evidence_grade"]}), lane=lane)
    kw.update(updates)
    return ConsumerBinding(**kw)


class PTSEContractTest(unittest.TestCase):
    def setUp(self):
        self.incumbent = {"episode_id": "fixture:episode-1", "security_id": "fixture:AMD",
                          "company_id": "fixture:company-AMD", "identity_epoch": "fixture:epoch-1",
                          "candidate_generation_id": "fixture:generation-1", "rank": 7, "score": 62.5,
                          "admitted": True, "entry_available": True, "plan": {"entry": 99, "size": 3},
                          "alerts": ["incumbent-alert"], "portfolio": {"units": 12}}
        self.before = canonical_json(self.incumbent)

    def artifact(self, action="NEW_ENTRY", applicability="APPLICABLE"):
        return build_context(*inputs(action, applicability))

    def consume(self, artifact=None, *, raw=None, scope=None, **kwargs):
        if artifact is None:
            artifact = self.artifact()
        result = read_optional_context(
            self.incumbent, artifact.canonical_bytes if raw is None else raw,
            scope or binding(artifact), now=NOW, response_request_id="r1", active_request_id="r1", **kwargs)
        self.assertIs(result.incumbent, self.incumbent)
        self.assertEqual(canonical_json(self.incumbent), self.before)
        return result

    def assert_bad(self, section, key, value, code=None):
        o, a = inputs(); target = o if section == "observation" else a if section == "assessment" else o["facts"][0]
        target[key] = value
        with self.assertRaises(ContractViolation) as caught:
            build_context(o, a)
        if code:
            self.assertEqual(caught.exception.code, code)

    def test_round_trip_and_immutable_copies(self):
        art = self.artifact(); parsed = validate_context(art.canonical_bytes)
        self.assertEqual(art, parsed)
        decoded = parsed.to_dict(); decoded["assessment"]["authority"]["rank"] = True
        self.assertFalse(parsed.to_dict()["assessment"]["authority"]["rank"])
        with self.assertRaises(Exception):
            parsed.canonical_bytes = b"tamper"

    def test_reordered_keys_and_equivalent_numeric_zero_have_same_identity(self):
        o, a = inputs(); x = build_context(o, a)
        o["facts"][0]["value"] = 0
        o = dict(reversed(list(o.items()))); a = dict(reversed(list(a.items())))
        y = build_context(o, a)
        self.assertEqual(x, y)

    def test_equivalent_aware_timestamps_canonicalize(self):
        o, a = inputs(); x = build_context(o, a)
        o["decision_at"] = a["decision_at"] = "2026-10-02T16:00:00-04:00"
        self.assertEqual(x, build_context(o, a))

    def test_retrieval_time_does_not_mint_observation(self):
        o, a = inputs(); x = build_context(o, a)
        o["issued_at"] = "2026-10-02T20:02:30Z"
        y = build_context(o, a)
        self.assertEqual(x.observation_id, y.observation_id)
        with self.assertRaisesRegex(ContractViolation, "IDEMPOTENCY_CONFLICT"):
            reconcile_observation(x, y)

    def test_action_and_horizon_do_not_mint_economic_observation(self):
        x = self.artifact(); y = self.artifact("CONTINUATION")
        self.assertEqual(x.observation_id, y.observation_id)
        self.assertNotEqual(x.assessment_id, y.assessment_id)
        o, a = inputs(); a["forecast_horizon_sessions"] = 21; a["forecast_end_session"] = "2026-11-02"
        z = build_context(o, a)
        self.assertEqual(x.observation_id, z.observation_id)
        self.assertNotEqual(x.assessment_id, z.assessment_id)

    def test_distinct_episode_and_strategy_have_distinct_assessments(self):
        x = self.artifact()
        for key in ["episode_id", "strategy_id", "strategy_version", "target_version"]:
            with self.subTest(key=key):
                o, a = inputs(); a[key] += "-changed"; y = build_context(o, a)
                self.assertEqual(x.observation_id, y.observation_id)
                self.assertNotEqual(x.assessment_id, y.assessment_id)

    def test_all_six_action_contracts(self):
        self.assertEqual(set(ACTIONS), {"NEW_ENTRY", "CONTINUATION", "PULLBACK_BUY", "ADD", "REENTRY", "DERISK"})
        for action in ACTIONS:
            with self.subTest(action=action):
                self.assertEqual(self.artifact(action).to_dict()["assessment"]["action"], action)

    def test_all_six_unknown_actions_remain_unknown_not_inapplicable(self):
        for action in ACTIONS:
            with self.subTest(action=action):
                art = self.artifact(action, "UNKNOWN")
                self.assertEqual(art.to_dict()["assessment"]["applicability"], "UNKNOWN")
                result = self.consume(art)
                self.assertEqual(result.reason, "APPLICABILITY_UNKNOWN")
                self.assertIsNone(result.context)

    def test_position_actions_require_owner_position(self):
        for action in ["CONTINUATION", "ADD", "DERISK"]:
            with self.subTest(action=action):
                o, a = inputs(action); a["position_ref"] = None
                with self.assertRaisesRegex(ContractViolation, "ACTION_BINDING_REQUIRED"):
                    build_context(o, a)

    def test_pullback_and_add_require_geometry(self):
        for action in ["PULLBACK_BUY", "ADD"]:
            with self.subTest(action=action):
                o, a = inputs(action); a["geometry_ref"] = None
                with self.assertRaisesRegex(ContractViolation, "ACTION_BINDING_REQUIRED"):
                    build_context(o, a)

    def test_add_requires_incremental_risk_budget(self):
        o, a = inputs("ADD"); a["risk_budget_ref"] = None
        with self.assertRaisesRegex(ContractViolation, "ACTION_BINDING_REQUIRED"):
            build_context(o, a)

    def test_reentry_requires_paired_derisk_episode(self):
        o, a = inputs("REENTRY"); a["prior_exit_episode_ref"] = None
        with self.assertRaisesRegex(ContractViolation, "ACTION_BINDING_REQUIRED"):
            build_context(o, a)

    def test_new_entry_cannot_launder_existing_position(self):
        self.assert_bad("assessment", "position_ref", ref("position"), "ACTION_BINDING_FORBIDDEN")

    def test_unknown_action(self):
        self.assert_bad("assessment", "action", "BUY_NOW")

    def test_forecast_is_not_holding_horizon(self):
        o, a = inputs(); x = build_context(o, a); a["holding_horizon_ref"] = ref("long-holding")
        y = build_context(o, a)
        self.assertEqual(x.to_dict()["assessment"]["forecast_horizon_sessions"], 5)
        self.assertNotEqual(x.assessment_id, y.assessment_id)

    def test_all_unearned_effect_bits_rejected(self):
        for key in AUTHORITY_KEYS:
            for bad in [True, 0, 1, None, "false"]:
                with self.subTest(key=key, bad=bad):
                    o, a = inputs(); a["authority"][key] = bad
                    with self.assertRaisesRegex(ContractViolation, "AUTHORITY_FORBIDDEN"):
                        build_context(o, a)

    def test_missing_or_unknown_authority_bit_rejected(self):
        o, a = inputs(); del a["authority"]["rank"]
        with self.assertRaises(ContractViolation): build_context(o, a)
        o, a = inputs(); a["authority"]["entry_permission"] = False
        with self.assertRaises(ContractViolation): build_context(o, a)

    def test_numeric_estimate_is_never_zero_filled_or_admitted(self):
        art = self.artifact(); self.assertIsNone(art.to_dict()["assessment"]["estimate"])
        for value in [0, 0.0, {"probability": 0}, {"confidence": 1}]:
            with self.subTest(value=value): self.assert_bad("assessment", "estimate", value, "ESTIMATE_NOT_ADMITTED")
        self.assert_bad("assessment", "estimate_status", "FITTED", "ESTIMATE_NOT_ADMITTED")

    def test_claimed_calibration_rejected_in_observation_schema(self):
        self.assert_bad("assessment", "evidence_status", "CALIBRATED_SHADOW", "ESTIMATE_NOT_ADMITTED")

    def test_future_availability_rejected(self):
        o, a = inputs(); o["facts"][0]["known_at"]["latest"] = "2026-10-02T20:00:01Z"
        o["facts"][0]["known_at"]["precision"] = "INTERVAL"
        with self.assertRaisesRegex(ContractViolation, "NOT_KNOWN_AT_DECISION"): build_context(o, a)

    def test_interval_upper_bound_controls_availability(self):
        o, a = inputs(); k = o["facts"][0]["known_at"]
        k.update(earliest="2026-10-02T19:00:00Z", latest=DECISION, precision="INTERVAL")
        build_context(o, a)
        k["latest"] = "2026-10-02T20:00:00.000001Z"
        with self.assertRaisesRegex(ContractViolation, "NOT_KNOWN_AT_DECISION"): build_context(o, a)

    def test_date_precision_is_not_invented_exact_time(self):
        o, a = inputs(); k = o["facts"][0]["known_at"]
        k.update(earliest="2026-10-02T00:00:00Z", latest="2026-10-03T00:00:00Z", precision="DATE_ONLY")
        with self.assertRaisesRegex(ContractViolation, "NOT_KNOWN_AT_DECISION"): build_context(o, a)

    def test_naive_clocks_rejected(self):
        for section, key in [("observation", "decision_at"), ("observation", "issued_at"),
                             ("assessment", "issued_at"), ("fact", "economic_time")]:
            with self.subTest(section=section, key=key): self.assert_bad(section, key, "2026-10-02T20:00:00", "TIMEZONE_REQUIRED")

    def test_issue_cannot_precede_decision(self):
        self.assert_bad("observation", "issued_at", "2026-10-02T19:59:59Z", "CLOCK_ORDER")

    def test_assessment_cannot_precede_observation_issue(self):
        self.assert_bad("assessment", "issued_at", "2026-10-02T20:01:59Z", "CLOCK_ORDER")

    def test_missing_value_is_not_neutral_zero(self):
        o, a = inputs(); f = o["facts"][0]
        f.update(value=None, status="UNAVAILABLE", known_at=None, null_reason="SOURCE_MISSING")
        f["coverage"].update(numerator=0, missing_count=1)
        art = build_context(o, a)
        self.assertIsNone(art.to_dict()["observation"]["facts"][0]["value"])
        result = self.consume(art); self.assertEqual(result.status, "PARTIAL")
        self.assertIsNotNone(result.context)

    def test_valid_zero_is_observed_not_missing(self):
        art = self.artifact()
        self.assertEqual(art.to_dict()["observation"]["facts"][0]["value"], 0)
        self.assertEqual(self.consume(art).status, "AVAILABLE")

    def test_conflicted_and_not_applicable_are_explicit_nulls(self):
        for status in ["CONFLICTED", "NOT_APPLICABLE"]:
            with self.subTest(status=status):
                o, a = inputs(); f = o["facts"][0]
                f.update(value=None, status=status, known_at=None, null_reason=status)
                f["coverage"].update(numerator=0, missing_count=1)
                self.assertEqual(self.consume(build_context(o, a)).status, "PARTIAL")

    def test_null_status_cannot_carry_numeric_value(self):
        self.assert_bad("fact", "status", "UNAVAILABLE", "NULL_CONTRACT")

    def test_observed_cannot_be_null(self):
        self.assert_bad("fact", "value", None, "NULL_CONTRACT")

    def test_partial_requires_real_denominator(self):
        o, a = inputs(); f = o["facts"][0]; f["status"] = "PARTIAL"
        f["coverage"].update(numerator=4, denominator=10, missing_count=6)
        self.assertEqual(self.consume(build_context(o, a)).status, "PARTIAL")
        f["coverage"]["missing_count"] = 5
        with self.assertRaisesRegex(ContractViolation, "COVERAGE_MISMATCH"): build_context(o, a)

    def test_observed_cannot_hide_missing_mass(self):
        o, a = inputs(); o["facts"][0]["coverage"].update(numerator=1, denominator=2, missing_count=1)
        with self.assertRaisesRegex(ContractViolation, "COVERAGE_STATUS_MISMATCH"): build_context(o, a)

    def test_denominator_zero_or_boolean_rejected(self):
        for bad in [0, True, -1, 1.5]:
            with self.subTest(bad=bad):
                o, a = inputs(); o["facts"][0]["coverage"]["denominator"] = bad
                with self.assertRaises(ContractViolation): build_context(o, a)

    def test_nan_infinity_and_ambiguous_numeric_types_rejected(self):
        for bad in [float("nan"), float("inf"), float("-inf"), True, "0.5"]:
            with self.subTest(bad=bad): self.assert_bad("fact", "value", bad)

    def test_units_are_closed(self):
        self.assert_bad("fact", "unit", "maybe-percent", "UNIT_UNKNOWN")
        o, a = inputs(); o["facts"][0].update(unit="FRACTION", value=1.1)
        with self.assertRaises(ContractViolation): build_context(o, a)

    def test_duplicate_feature_identity_rejected(self):
        o, a = inputs(); o["facts"].append(copy.deepcopy(o["facts"][0]))
        with self.assertRaisesRegex(ContractViolation, "DUPLICATE_FEATURE"): build_context(o, a)

    def test_foreign_driver_reference_rejected(self):
        self.assert_bad("assessment", "drivers", ["made-up-factor"], "UNKNOWN_FACT_REFERENCE")

    def test_duplicate_driver_reference_rejected(self):
        self.assert_bad("assessment", "drivers", ["fixture.price.log_v20"] * 2, "DUPLICATE_REFERENCE")

    def test_owner_ref_cannot_be_dropped_or_changed_independently(self):
        self.assert_bad("fact", "owner_ref", "different-owner", "OWNER_MISMATCH")

    def test_sha_and_revision_shapes_rejected(self):
        o, a = inputs(); o["source_manifest_ref"]["sha256"] = "not-a-hash"
        with self.assertRaises(ContractViolation): build_context(o, a)
        self.assert_bad("observation", "producer_revision", "main", "REVISION_REQUIRED")

    def test_windowed_positioning_cannot_claim_full_book_or_dealer_inventory(self):
        o, a = inputs(); s = o["facts"][0]["source_scope"]
        s.update(position_scope="WINDOWED", side_semantics="UNSIGNED_GROSS")
        build_context(o, a)
        s["side_semantics"] = "OBSERVED_DEALER_INVENTORY"
        with self.assertRaises(ContractViolation): build_context(o, a)

    def test_llm_synthesis_cannot_originate_numeric_fact(self):
        self.assert_bad("fact", "method_kind", "GROUNDED_SYNTHESIS", "NUMERIC_SYNTHESIS_FORBIDDEN")

    def test_source_population_mismatch_rejected(self):
        o, a = inputs(); o["facts"][0]["source_scope"]["population_ref"] = ref("different-population")
        with self.assertRaisesRegex(ContractViolation, "POPULATION_MISMATCH"): build_context(o, a)

    def test_stale_fact_stays_stale_and_partial(self):
        o, a = inputs(); f = o["facts"][0]
        f.update(status="STALE", valid_until=DECISION, null_reason="OWNER_FRESHNESS_EXPIRED")
        self.assertEqual(self.consume(build_context(o, a)).status, "PARTIAL")

    def test_false_stale_and_false_fresh_rejected(self):
        self.assert_bad("fact", "status", "STALE")
        self.assert_bad("fact", "valid_until", DECISION, "FRESHNESS_STATUS_MISMATCH")

    def test_horizon_and_calendar_mismatch_rejected(self):
        for bad in [0, -1, True, 5.5]:
            with self.subTest(bad=bad): self.assert_bad("assessment", "forecast_horizon_sessions", bad)
        self.assert_bad("assessment", "calendar_ref", ref("other-calendar"), "CALENDAR_MISMATCH")
        self.assert_bad("assessment", "forecast_end_session", "2026-10-02", "HORIZON_ORDER")

    def test_retrospective_requires_reconstruction_time(self):
        o, a = inputs(); o["evidence_grade"] = "RETROSPECTIVE_PIT_UNPROVEN"
        o["facts"][0]["evidence_grade"] = "RETROSPECTIVE_PIT_UNPROVEN"
        with self.assertRaisesRegex(ContractViolation, "RECONSTRUCTION_REQUIRED"): build_context(o, a)
        o["reconstructed_at"] = "2026-10-02T20:01:00Z"
        art = build_context(o, a)
        result = self.consume(art, scope=binding(art, lane="READ_ONLY_LIVE"))
        self.assertEqual(result.reason, "SOURCE_GRADE_NOT_ADMITTED")

    def test_prospective_cannot_relabel_reconstruction(self):
        o, a = inputs(); o["evidence_grade"] = "PROSPECTIVE_FIRST_SEEN"
        o["facts"][0]["evidence_grade"] = "PROSPECTIVE_FIRST_SEEN"
        o["reconstructed_at"] = "2026-10-02T20:01:00Z"
        with self.assertRaisesRegex(ContractViolation, "PROSPECTIVE_RECONSTRUCTION_FORBIDDEN"): build_context(o, a)

    def test_observation_grade_cannot_upgrade_fact_grade(self):
        o, a = inputs()
        o.update(evidence_grade="PIT_QUALIFIED_REPLAY", reconstructed_at="2026-10-02T20:01:00Z")
        with self.assertRaisesRegex(ContractViolation, "GRADE_UPGRADE_FORBIDDEN"):
            build_context(o, a)

    def test_idempotent_existing_record(self):
        x = self.artifact(); self.assertEqual(reconcile_observation(x, x), "IDEMPOTENT")

    def test_correction_is_append_only_and_preserves_anchor(self):
        x = self.artifact(); o, a = inputs(); o["facts"][0]["value"] = 0.1
        o["facts"][0]["source_artifact_ref"] = ref("price-correction", "fixture-price-owner")
        o.update(supersedes_ref=x.observation_id, correction_reason="Owner corrected fixture source.")
        y = build_context(o, a)
        self.assertEqual(reconcile_observation(x, y), "CORRECTION")
        self.assertEqual(x.to_dict()["observation"]["facts"][0]["value"], 0)
        o["decision_at"] = a["decision_at"] = "2026-10-02T20:00:01Z"
        z = build_context(o, a)
        with self.assertRaisesRegex(ContractViolation, "CORRECTION_ANCHOR_MISMATCH"): reconcile_observation(x, z)

    def test_correction_requires_lineage_and_reason(self):
        self.assert_bad("observation", "supersedes_ref", "obs:" + "f" * 64, "CORRECTION_PAIR_REQUIRED")
        self.assert_bad("observation", "correction_reason", "changed", "CORRECTION_PAIR_REQUIRED")

    def test_changed_record_cannot_silently_replace_prior(self):
        x = self.artifact(); o, a = inputs(); o["facts"][0]["value"] = 0.1
        with self.assertRaisesRegex(ContractViolation, "CORRECTION_REQUIRED"):
            reconcile_observation(x, build_context(o, a))

    def test_forged_ids_and_unknown_fields_rejected(self):
        art = self.artifact(); p = art.to_dict(); p["observation"]["observation_id"] = "obs:" + "b" * 64
        with self.assertRaisesRegex(ContractViolation, "IDENTITY_MISMATCH"): validate_context(canonical_json(p))
        for section in ["observation", "assessment", "fact"]:
            with self.subTest(section=section): self.assert_bad(section, "entry_permission", False, "FIELD_SET")

    def test_duplicate_json_keys_and_nonfinite_wire_values_rejected(self):
        for raw in [b'{"schema_version":"a","schema_version":"b"}', b'{"x":NaN}', b'{"x":Infinity}']:
            with self.subTest(raw=raw):
                with self.assertRaises(ContractViolation): validate_context(raw)

    def test_parser_rejects_bom_invalid_utf8_and_non_object(self):
        for raw in [b'\xef\xbb\xbf{}', b'\xff', b'[]', b'null']:
            with self.subTest(raw=raw):
                with self.assertRaises(ContractViolation): validate_context(raw)

    def test_live_consumer_never_accepts_synthetic(self):
        art = self.artifact(); result = self.consume(art, scope=binding(art, lane="READ_ONLY_LIVE"))
        self.assertEqual(result.reason, "SOURCE_GRADE_NOT_ADMITTED")

    def test_first_live_slice_is_only_us_daily_h5_new_entry(self):
        for action in ACTIONS:
            o, a = inputs(action); o["evidence_grade"] = o["facts"][0]["evidence_grade"] = "PIT_QUALIFIED_REPLAY"
            o["reconstructed_at"] = "2026-10-02T20:01:00Z"
            art = build_context(o, a)
            result = self.consume(art, scope=binding(art, lane="READ_ONLY_LIVE"))
            with self.subTest(action=action):
                self.assertEqual(result.status == "AVAILABLE", action == "NEW_ENTRY")
                if action != "NEW_ENTRY": self.assertEqual(result.reason, "LANE_NOT_ADMITTED")

    def test_no_observation_call_grants_source_admission(self):
        art = self.artifact(); result = self.consume(art, scope=binding(art, accepted_grades=frozenset()))
        self.assertEqual(result.reason, "SOURCE_GRADE_NOT_ADMITTED")

    def test_consumer_binds_every_candidate_dimension(self):
        art = self.artifact()
        changes = {"market": "CA", "cadence": "INTRADAY", "session_scope": "EXTENDED",
                   "observation_instrument_id": "fixture:QQQ",
                   "episode_id": "other-episode", "security_id": "fixture:MU",
                   "company_id": "other-company", "identity_epoch": "other-epoch",
                   "candidate_generation_id": "other-generation",
                   "strategy_id": "other-strategy", "strategy_version": "v2", "action": "ADD",
                   "decision_at": "2026-10-02T20:00:01Z", "forecast_horizon_sessions": 21,
                   "forecast_end_session": "2026-11-02", "target_version": "other-target",
                   "calendar_sha256": "b" * 64, "cohort_sha256": "b" * 64,
                   "holding_horizon_sha256": "b" * 64, "producer_revision": "b" * 40,
                   "source_manifest_sha256": "b" * 64}
        for key, value in changes.items():
            with self.subTest(key=key):
                result = self.consume(art, scope=binding(art, **{key: value}))
                self.assertEqual(result.reason, "BINDING_MISMATCH")
                self.assertIsNone(result.context)

    def test_integrity_is_bound_outside_the_payload(self):
        art = self.artifact(); o, a = inputs(); o["facts"][0]["value"] = .9
        forged = build_context(o, a)
        result = self.consume(art, raw=forged.canonical_bytes)
        self.assertEqual(result.reason, "ARTIFACT_DIGEST_MISMATCH")

    def test_missing_invalid_and_rollback_preserve_current_prophet(self):
        art = self.artifact()
        for raw in [None, b"", b"not json", b"{}", b"[]"]:
            result = read_optional_context(self.incumbent, raw, binding(art), now=NOW,
                                           response_request_id="r1", active_request_id="r1")
            self.assertIs(result.incumbent, self.incumbent)
            self.assertEqual(canonical_json(self.incumbent), self.before)
            self.assertIsNone(result.context)
            self.assertEqual(result.update, "CLEAR_CONTEXT")
        result = self.consume(art, enabled=False)
        self.assertEqual(result.reason, "DISABLED")

    def test_late_response_cannot_clear_newer_context(self):
        art = self.artifact()
        for raw in [art.canonical_bytes, b"malformed", None]:
            result = read_optional_context(self.incumbent, raw, binding(art), now=NOW,
                                           response_request_id="old", active_request_id="new")
            self.assertEqual(result.update, "KEEP_CURRENT")
            self.assertEqual(result.reason, "SUPERSEDED_REQUEST")
            self.assertIs(result.incumbent, self.incumbent)

    def test_future_issue_and_expiry_exact_boundaries(self):
        art = self.artifact()
        for now, expected in [("2026-10-02T20:02:59Z", "NOT_YET_ISSUED"),
                              ("2026-10-02T21:00:00Z", "EXPIRED"),
                              ("2026-10-03T00:00:00Z", "EXPIRED")]:
            with self.subTest(now=now):
                result = read_optional_context(self.incumbent, art.canonical_bytes, binding(art), now=now,
                                               response_request_id="r1", active_request_id="r1")
                self.assertEqual(result.reason, expected)
                self.assertIs(result.incumbent, self.incumbent)

    def test_late_source_expiry_makes_context_partial_without_new_valuation(self):
        o, a = inputs(); o["facts"][0]["valid_until"] = "2026-10-02T20:03:30Z"
        art = build_context(o, a)
        result = self.consume(art); self.assertEqual(result.status, "PARTIAL")
        self.assertEqual(result.reason, "SOME_FACTS_UNAVAILABLE_OR_STALE")
        self.assertEqual(result.context.to_dict()["observation"]["facts"][0]["status"], "OBSERVED")

    def test_unsupported_schema_degrades_instead_of_mutating(self):
        art = self.artifact(); p = art.to_dict(); p["schema_version"] = "prophet.timing_context/v999"
        result = self.consume(art, raw=canonical_json(p)); self.assertEqual(result.status, "UNAVAILABLE")

    def test_valid_optional_context_never_updates_rank_gate_plan_alert_or_size(self):
        result = self.consume()
        self.assertEqual(result.status, "AVAILABLE")
        self.assertEqual(result.update, "REPLACE_CONTEXT")
        self.assertIsNotNone(result.context)
        self.assertEqual(canonical_json(result.incumbent), self.before)


    def test_first_live_slice_requires_explicit_daily_regular_session(self):
        for field, value in [("cadence", "INTRADAY"), ("session_scope", "EXTENDED"),
                             ("session_scope", "ALL"), ("session_scope", "OWNER_DEFINED")]:
            with self.subTest(field=field, value=value):
                o, a = inputs(); o["evidence_grade"] = "PROSPECTIVE_FIRST_SEEN"
                o["facts"][0]["evidence_grade"] = "PROSPECTIVE_FIRST_SEEN"; o[field] = value
                art = build_context(o, a)
                self.assertEqual(self.consume(art, scope=binding(art, lane="READ_ONLY_LIVE")).reason, "LANE_NOT_ADMITTED")

    def test_missing_optional_event_or_options_does_not_block_price_context(self):
        o, a = inputs(); o["evidence_grade"] = "PROSPECTIVE_FIRST_SEEN"
        o["facts"][0]["evidence_grade"] = "PROSPECTIVE_FIRST_SEEN"
        for feature in ["fixture.event.schedule", "fixture.options.structure"]:
            f = copy.deepcopy(o["facts"][0]); f.update(feature_id=feature, value=None,
                status="UNAVAILABLE", known_at=None, evidence_grade="RETROSPECTIVE_PIT_UNPROVEN",
                null_reason="Independent family has no qualified source; price lane remains eligible.")
            f["coverage"].update(numerator=0, denominator=None, missing_count=None)
            o["facts"].append(f)
        art = build_context(o, a); result = self.consume(art, scope=binding(art, lane="READ_ONLY_LIVE"))
        self.assertEqual(result.status, "PARTIAL")
        self.assertEqual(dict(result.effective_fact_statuses)["fixture.price.log_v20"], "OBSERVED")
        self.assertEqual(len(result.effective_fact_statuses), 3)
        self.assertEqual(result.context.to_dict()["assessment"]["estimate_status"], "NOT_FITTED")

    def test_unqualified_present_optional_value_cannot_inherit_price_grade(self):
        o, a = inputs(); o["evidence_grade"] = "PROSPECTIVE_FIRST_SEEN"
        o["facts"][0]["evidence_grade"] = "PROSPECTIVE_FIRST_SEEN"
        f = copy.deepcopy(o["facts"][0]); f.update(feature_id="fixture.options.structure",
                                                 evidence_grade="RETROSPECTIVE_PIT_UNPROVEN")
        o["facts"].append(f)
        with self.assertRaisesRegex(ContractViolation, "GRADE_UPGRADE_FORBIDDEN"):
            build_context(o, a)

    def test_scheduled_future_event_is_not_a_future_release_value(self):
        o, a = inputs(); f = o["facts"][0]
        f.update(economic_time_role="SCHEDULED_EVENT", economic_time="2026-10-05T12:30:00Z",
                 value="2026-10-05T12:30:00Z", unit="TIMESTAMP")
        self.assertEqual(self.consume(build_context(o, a)).status, "AVAILABLE")
        for unit, value in [("COUNT", 100), ("PERCENT", 3.2), ("BOOLEAN", True)]:
            f.update(unit=unit, value=value)
            with self.subTest(unit=unit), self.assertRaisesRegex(ContractViolation, "SCHEDULE_IS_NOT_RELEASE_OUTCOME"):
                build_context(o, a)

    def test_list_or_object_estimate_status_returns_typed_failure(self):
        for key in ["estimate_status", "evidence_status"]:
            for value in [[], {}, None, True, 0]:
                with self.subTest(key=key, value=value):
                    self.assert_bad("assessment", key, value, "ESTIMATE_NOT_ADMITTED")

    def test_invalid_grade_admission_container_cannot_self_admit(self):
        art = self.artifact()
        for grades in ["SYNTHETIC", {"SYNTHETIC"}, ["SYNTHETIC"], frozenset({"unknown"}), None]:
            with self.subTest(grades=grades):
                result = self.consume(art, scope=binding(art, accepted_grades=grades))
                self.assertEqual(result.reason, "CONSUMER_BINDING_INVALID")

    def test_large_and_deep_payloads_fail_closed_without_incumbent_change(self):
        for raw in [b" " * 1_048_577, b"{\"x\":" + b"[" * 1500 + b"0" + b"]" * 1500 + b"}"]:
            with self.subTest(size=len(raw)):
                result = self.consume(raw=raw)
                self.assertEqual(result.status, "UNAVAILABLE")
                self.assertIsNone(result.context)

    def test_correction_cannot_switch_cadence_or_session_scope(self):
        old = self.artifact()
        for field, value in [("cadence", "INTRADAY"), ("session_scope", "EXTENDED")]:
            o, a = inputs(); o[field] = value
            o.update(supersedes_ref=old.observation_id, correction_reason="Fixture changed scope.")
            with self.subTest(field=field), self.assertRaisesRegex(ContractViolation, "CORRECTION_ANCHOR_MISMATCH"):
                reconcile_observation(old, build_context(o, a))

    def test_invalid_enable_flag_is_not_truthy_authority(self):
        for flag in [1, "true", {}, None]:
            with self.subTest(flag=flag):
                self.assertEqual(self.consume(enabled=flag).reason, "INVALID_ENABLE_FLAG")

    def test_horizon_boolean_cannot_match_integer_binding(self):
        self.assert_bad("assessment", "forecast_horizon_sessions", True, "INTEGER_REQUIRED")
        art = self.artifact()
        self.assertEqual(self.consume(art, scope=binding(art, forecast_horizon_sessions=5.0)).reason, "BINDING_MISMATCH")

    def test_observation_scope_fields_are_required_not_inferred_from_h5(self):
        for key in ["cadence", "session_scope"]:
            o, a = inputs(); del o[key]
            with self.subTest(key=key), self.assertRaisesRegex(ContractViolation, "FIELD_SET"):
                build_context(o, a)

    def test_failed_optional_request_never_returns_authority_fields_as_patch(self):
        result = self.consume(raw=b"{\"rank\":0,\"trade\":true}")
        self.assertEqual(result.update, "CLEAR_CONTEXT")
        self.assertEqual(result.incumbent["rank"], 7)
        self.assertEqual(result.incumbent["plan"], {"entry": 99, "size": 3})



    def test_canonical_incumbent_identity_drift_is_not_a_ticker_alias_match(self):
        for key in ["episode_id", "security_id", "company_id", "identity_epoch", "candidate_generation_id"]:
            with self.subTest(key=key):
                self.setUp(); self.incumbent[key] = "fixture:other-owner-identity"
                self.before = canonical_json(self.incumbent)
                self.assertEqual(self.consume().reason, "INCUMBENT_EPISODE_BINDING_MISMATCH")

    def test_missing_canonical_identity_does_not_infer_a_new_episode(self):
        for key in ["episode_id", "security_id", "company_id", "identity_epoch", "candidate_generation_id"]:
            with self.subTest(key=key):
                self.setUp(); del self.incumbent[key]; self.before = canonical_json(self.incumbent)
                self.assertEqual(self.consume().reason, "INCUMBENT_EPISODE_BINDING_MISMATCH")

    def test_generation_change_changes_assessment_not_market_observation(self):
        old = self.artifact(); o, a = inputs(); a["candidate_generation_id"] = "fixture:generation-2"
        new = build_context(o, a)
        self.assertEqual(old.observation_id, new.observation_id)
        self.assertNotEqual(old.assessment_id, new.assessment_id)


class PTSEBoundaryRegressionTest(unittest.TestCase):
    """Synthetic caller-boundary regressions; no source or market admission."""

    EXTREME_TIMESTAMPS = (
        "0001-01-01T00:00:00+14:00", "9999-12-31T23:59:59-14:00",
        "0001-01-01T00:00:00+23:59", "9999-12-31T23:59:59-23:59",
    )

    def setUp(self):
        self.harness = PTSEContractTest()
        self.harness.setUp()
        self.artifact = build_context(*inputs())
        self.scope = binding(self.artifact)

    def consume_unavailable(self, raw, *, now=NOW, scope=None):
        result = read_optional_context(
            self.harness.incumbent, raw, scope or self.scope, now=now,
            response_request_id="r1", active_request_id="r1")
        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertEqual(result.update, "CLEAR_CONTEXT")
        self.assertIs(result.incumbent, self.harness.incumbent)
        self.assertEqual(canonical_json(self.harness.incumbent), self.harness.before)
        return result

    @staticmethod
    def wide_inputs(count):
        observation, assessment = inputs()
        original = observation["facts"][0]
        observation["facts"] = [copy.deepcopy(original) for _ in range(count)]
        for index, fact in enumerate(observation["facts"]):
            fact["feature_id"] = (original["feature_id"] if index == 0
                                  else f"fixture.price.extra_{index}")
        return observation, assessment

    def test_extreme_wire_timestamps_degrade_without_throwing(self):
        paths = (
            ("observation", "decision_at"), ("observation", "issued_at"),
            ("observation", "valid_until"),
            ("observation", "facts", 0, "economic_time"),
            ("observation", "facts", 0, "valid_until"),
            ("observation", "facts", 0, "known_at", "earliest"),
            ("observation", "facts", 0, "known_at", "latest"),
            ("assessment", "issued_at"), ("assessment", "decision_at"),
        )
        for path in paths:
            for stamp in self.EXTREME_TIMESTAMPS:
                with self.subTest(path=path, stamp=stamp):
                    payload = self.artifact.to_dict()
                    target = payload
                    for key in path[:-1]:
                        target = target[key]
                    target[path[-1]] = stamp
                    self.consume_unavailable(json.dumps(payload))

    def test_extreme_consumer_clocks_and_bindings_degrade(self):
        from dataclasses import replace
        for stamp in self.EXTREME_TIMESTAMPS:
            with self.subTest(clock=stamp):
                self.consume_unavailable(self.artifact.canonical_bytes, now=stamp)
            with self.subTest(binding=stamp):
                self.consume_unavailable(
                    self.artifact.canonical_bytes,
                    scope=replace(self.scope, decision_at=stamp))

    def test_factory_wraps_datetime_overflow_in_contract_error(self):
        for stamp in self.EXTREME_TIMESTAMPS:
            with self.subTest(stamp=stamp):
                observation, assessment = inputs()
                observation["decision_at"] = stamp
                with self.assertRaisesRegex(ContractViolation, "TIMESTAMP_INVALID"):
                    build_context(observation, assessment)

    def test_factory_refuses_canonical_payload_over_reader_limit(self):
        with self.assertRaisesRegex(ContractViolation, "PAYLOAD_TOO_LARGE"):
            build_context(*self.wide_inputs(768))

    def test_validator_refuses_canonical_expansion_over_limit(self):
        from research.options_estate import ptse_contract as contract
        # Manufacture a malicious wire fixture through pure internal validators,
        # not the public factory whose output bound is the behavior under test.
        observation, assessment = self.wide_inputs(742)
        observation = contract._observation(observation, sealed=False)
        assessment = contract._assessment(assessment, observation, sealed=False)
        canonical = canonical_json({
            "schema_version": contract.SCHEMA,
            "canonicalization": contract.CANONICALIZATION,
            "observation": observation, "assessment": assessment,
        })
        raw = canonical.replace(b".000000Z", b"Z")
        self.assertLessEqual(len(raw), contract.MAX_WIRE_BYTES)
        self.assertGreater(len(canonical), contract.MAX_WIRE_BYTES)
        with self.assertRaisesRegex(ContractViolation, "PAYLOAD_TOO_LARGE"):
            validate_context(raw)


if __name__ == "__main__":
    unittest.main()
