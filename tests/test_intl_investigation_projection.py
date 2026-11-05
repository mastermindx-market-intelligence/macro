"""Tests for the IntlInvestigation resolved-packet projection (T007.S5).

Discriminating coverage of the contract:

* qualified JP monthly + annual, and the zero-retained case;
* a changed policy changes the qualification identity only;
* qualified -> stale / denied / failed scrubs every number;
* a missing policy keeps a null qualification and no interpretation;
* all nine context strings are required, and period / basis / market /
  version / generation mismatches are refused;
* duplicate selection, duplicate prior observation and tombstone collisions
  are refused; partial membership never removes an observation;
* an absent prior stays null, a historical prior is passed through
  unchanged and surfaces scope_changed;
* a caller clock that is null stays null - "now" is never invented;
* a denied sidecar exposes no source URL and no date.
"""

import builtins
import copy
import json
import os
import re
import socket
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))

from lib.intl_investigation_projection import (  # noqa: E402
    project_intl_resolved_packet,
    SUPPORTED_UNITS,
)

GENERATION = "im-workspace-generation:4979a6c3-b834-4c69-8f1b-c8961cc5e11a"
OTHER_GENERATION = "im-workspace-generation:0f9c2b41-6f6e-4f0a-9a2b-1c3d4e5f6071"
RECEIPT_SHA = "1" * 64
OTHER_RECEIPT_SHA = "2" * 64
ARTIFACT_SHA = "a" * 64
PROVENANCE_SHA = "b" * 64

MONTHLY = "JP.yield_10y"
ANNUAL = "JP.annual_current_account"
ECB = "EZ.policy_rate"
UNSUPPORTED = "JP.not_a_supported_measure"

OBSERVED_AT = "2026-10-01"
SOURCE_URL = "https://example.invalid/source"
TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T[\d:.]+Z?")

CONTEXT_STRINGS = (
    "researchMarket", "toolBindingVersion", "periodIdentity", "currencyBasis",
    "returnBasis", "owner", "query", "cohort", "temporalPolicy",
)
FROZEN_PACKET_KEYS = {"exactContext", "prior", "current", "requirements", "owner"}
FROZEN_CONTEXT_KEYS = set(CONTEXT_STRINGS) | {"selectedMeasureIds"}
FROZEN_CURRENT_KEYS = (set(CONTEXT_STRINGS) | {
    "generation", "read", "membership", "observations", "tombstones"})
FROZEN_OBSERVATION_KEYS = {
    "id", "availability", "qualified", "excluded", "correction",
    "contentIdentity", "qualificationIdentity", "interpretation"}
FROZEN_OWNER_KEYS = {
    "lang", "question", "marketLabel", "toolLabel", "periodLabel", "basisLabel",
    "savedAt", "updatedAt", "sourceGenerationAt", "rightsAt", "measureLabels",
    "unmetLabels", "observedAtByMeasureId"}


def _binding(**overrides):
    binding = {"market": "JP", "horizon": "3m", "currency_basis": "local",
               "return_basis": "price", "binding_version": 2, "generation": GENERATION}
    binding.update(overrides)
    return binding


def _context(selected, **overrides):
    context = {"researchMarket": "JP", "toolBindingVersion": "2",
               "periodIdentity": "3m", "currencyBasis": "local",
               "returnBasis": "price", "owner": "owner-1",
               "query": "What is the JP 10y yield?", "cohort": "jp-core",
               "temporalPolicy": "as-of", "selectedMeasureIds": list(selected)}
    context.update(overrides)
    return context


def _request(selected=(MONTHLY,), **overrides):
    selected = list(selected)
    request = {
        "context": _context(selected),
        "requirements": {"requiredMeasureIds": list(selected),
                         "unmetPrerequisites": []},
        "owner": {"lang": "en", "question": "What is the JP 10y yield?",
                  "marketLabel": "Japan", "toolLabel": "IntlInvestigation",
                  "periodLabel": "3m", "basisLabel": "local",
                  "savedAt": None, "updatedAt": None, "sourceGenerationAt": None,
                  "rightsAt": None,
                  "measureLabels": {sid: "label %s" % sid for sid in selected},
                  "unmetLabels": []},
        "prior": None, "prior_authorized": False, "read": "ok",
        "membership": "complete", "enumerated_measure_ids": list(selected),
        "facts": {}, "tombstones": []}
    request.update(overrides)
    return request


def _measure(sid=MONTHLY, **overrides):
    instrument = {"kind": "sovereign_10y", "id": "IRLTLT01JPM156N", "market_id": sid.split(".")[0]}
    if sid == ECB:
        instrument = {"kind": "official_policy", "id": "deposit_facility", "market_id": "EZ"}
    measure = {"quality": "qualified", "reason": None, "metadata": "allowed",
               "value_permission": "allowed", "value": 1.5,
               "unit": SUPPORTED_UNITS.get(sid, "percent"), "instrument": instrument,
               "period": None, "observation_at": OBSERVED_AT,
               "calculation_at": None,
               "source_reference": "%s/%s" % (SOURCE_URL, sid),
               "evidence_key": "evidence-%s" % sid}
    measure.update(overrides)
    return measure


def _receipt(sha=RECEIPT_SHA):
    return {"receipt_sha256": sha}


def _ecb_receipt():
    return {"artifact_sha256": ARTIFACT_SHA, "provenance_sha256": PROVENANCE_SHA}


def _decision(sid=MONTHLY, receipt_sha=RECEIPT_SHA, policy_ref="policy/jp-core-v3",
              generation=GENERATION, **overrides):
    decision = {"owner_ref": "scripts/build_intl.py", "policy_ref": policy_ref,
                "decision_ref": "%s:%s" % (generation, sid), "metadata": "allowed",
                "value_permission": "allowed",
                "binding": {"field": sid, "receipt_sha256": receipt_sha}}
    decision.update(overrides)
    return decision


def _ecb_decision(value=2.5, unit="percent", observation_at=OBSERVED_AT, **overrides):
    decision = {"owner_ref": "scripts/build_intl.py", "policy_ref": "policy/ez-core-v1",
                "decision_ref": "%s:%s" % (GENERATION, ECB), "metadata": "allowed",
                "value_permission": "allowed",
                "binding": {"market_id": "EZ", "field": "policy_rate",
                            "instrument_id": "deposit_facility",
                            "source_id": "D.U2.EUR.4F.KR.DFR.LEV",
                            "artifact_sha256": ARTIFACT_SHA,
                            "provenance_sha256": PROVENANCE_SHA,
                            "observation_at": observation_at, "value": value,
                            "unit": unit}}
    decision.update(overrides)
    return decision


def _evidence(sid=MONTHLY, receipt=None, decision=None, clocks=None):
    if clocks is None:
        clocks = {"observation_at": OBSERVED_AT}
    return {sid: {"receipt_identity": receipt, "publication_decision": decision,
                  "clocks": clocks}}


def _prior(**overrides):
    prior = {"researchMarket": "JP", "toolBindingVersion": "2",
             "periodIdentity": "1m", "currencyBasis": "local",
             "returnBasis": "price", "owner": "owner-0",
             "query": "What was the JP 10y yield?", "cohort": "jp-core",
             "temporalPolicy": "as-of", "generation": GENERATION, "read": "ok",
             "membership": "complete",
             "observations": [{"id": MONTHLY, "availability": "available",
                               "qualified": True, "excluded": False,
                               "correction": False, "contentIdentity": "c" * 64,
                               "qualificationIdentity": "d" * 64,
                               "interpretation": {"value": 1.4, "unit": "percent",
                                                  "basis": "local", "cohort": "jp-core"}}],
             "tombstones": []}
    prior.update(overrides)
    return prior


def _project(request=None, binding=None, measures=None, evidence=None):
    return project_intl_resolved_packet(
        request=request if request is not None else _request(),
        native_binding=binding if binding is not None else _binding(),
        measures=measures if measures is not None else {},
        evidence=evidence if evidence is not None else {})


def _qualified_pair():
    """A fully qualified JP monthly + annual projection."""
    selected = [MONTHLY, ANNUAL]
    request = _request(selected)
    measures = {
        MONTHLY: _measure(MONTHLY, value=1.5),
        ANNUAL: _measure(ANNUAL, value=2.1, observation_at="2026-09-24",
                          period={"start":"2025-01-01","end":"2026-01-01","count":1,"count_basis":"release_periods"},
                          instrument={"kind": "current_account", "id": "JPN.BCA_NGDPD.A",
                                      "market_id": "JP"})}
    evidence = {}
    evidence.update(_evidence(MONTHLY, _receipt(), _decision(MONTHLY)))
    evidence.update(_evidence(ANNUAL, _receipt(OTHER_RECEIPT_SHA),
                               _decision(ANNUAL, OTHER_RECEIPT_SHA)))
    return request, measures, evidence


class QualificationTests(unittest.TestCase):
    def test_qualified_jp_monthly_and_annual(self):
        request, measures, evidence = _qualified_pair()
        out = _project(request, measures=measures, evidence=evidence)
        observations = out["packet"]["current"]["observations"]
        self.assertEqual([item["id"] for item in observations], [MONTHLY, ANNUAL])
        for observation in observations:
            self.assertEqual(observation["availability"], "available")
            self.assertTrue(observation["qualified"])
            self.assertIsNotNone(observation["contentIdentity"])
            self.assertIsNotNone(observation["qualificationIdentity"])
            self.assertIsNotNone(observation["interpretation"])
        self.assertEqual(observations[0]["interpretation"]["value"], 1.5)
        self.assertEqual(observations[0]["interpretation"]["unit"], "percent")
        self.assertEqual(observations[0]["interpretation"]["basis"], "local")
        self.assertEqual(observations[0]["interpretation"]["cohort"], "jp-core")
        self.assertEqual(observations[1]["interpretation"]["value"], 2.1)
        self.assertEqual(observations[1]["interpretation"]["unit"], "percent_gdp")
        self.assertEqual(out["packet"]["owner"]["observedAtByMeasureId"],
                         {MONTHLY: OBSERVED_AT, ANNUAL: "2026-09-24"})
        self.assertEqual(out["diagnostics"], [])

    def test_packet_shape_is_frozen(self):
        request, measures, evidence = _qualified_pair()
        packet = _project(request, measures=measures, evidence=evidence)["packet"]
        self.assertEqual(set(packet), FROZEN_PACKET_KEYS)
        self.assertEqual(set(packet["exactContext"]), FROZEN_CONTEXT_KEYS)
        self.assertEqual(set(packet["current"]), FROZEN_CURRENT_KEYS)
        self.assertNotIn("selectedMeasureIds", packet["current"])
        self.assertEqual(set(packet["requirements"]),
                         {"requiredMeasureIds", "unmetPrerequisites"})
        self.assertEqual(set(packet["owner"]), FROZEN_OWNER_KEYS)
        for observation in packet["current"]["observations"]:
            self.assertEqual(set(observation), FROZEN_OBSERVATION_KEYS)

    def test_zero_retained_when_no_measure_is_supplied(self):
        out = _project(_request())
        observations = out["packet"]["current"]["observations"]
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0]["availability"], "unavailable")
        self.assertFalse(observations[0]["qualified"])
        self.assertIsNone(observations[0]["interpretation"])
        self.assertIsNone(observations[0]["contentIdentity"])
        self.assertIsNone(observations[0]["qualificationIdentity"])
        self.assertEqual(out["packet"]["owner"]["observedAtByMeasureId"], {MONTHLY: None})
        self.assertNotIn("1.5", json.dumps(out["packet"]))
        self.assertIn("missing_owner_input",
                      [entry["code"] for entry in out["diagnostics"]])

    def test_same_value_changed_policy_changes_qualification_only(self):
        request, measures = _request(), {MONTHLY: _measure(MONTHLY, value=1.5)}
        first = _project(request, measures=measures,
                         evidence=_evidence(MONTHLY, _receipt(),
                                            _decision(MONTHLY, policy_ref="policy/v1")))
        second = _project(request, measures=measures,
                          evidence=_evidence(MONTHLY, _receipt(),
                                             _decision(MONTHLY, policy_ref="policy/v2")))
        left = first["packet"]["current"]["observations"][0]
        right = second["packet"]["current"]["observations"][0]
        self.assertEqual(left["contentIdentity"], right["contentIdentity"])
        self.assertNotEqual(left["qualificationIdentity"], right["qualificationIdentity"])
        self.assertEqual(left["interpretation"], right["interpretation"])

    def test_stale_denied_and_failed_scrub_every_number(self):
        for quality, availability in (("stale", "stale"), ("denied", "denied"),
                                      ("failed", "unavailable")):
            with self.subTest(quality=quality):
                request = _request()
                measures = {MONTHLY: _measure(MONTHLY, quality=quality, value=1.5)}
                evidence = _evidence(MONTHLY, _receipt(), _decision(MONTHLY))
                out = _project(request, measures=measures, evidence=evidence)
                observation = out["packet"]["current"]["observations"][0]
                self.assertEqual(observation["availability"], availability)
                self.assertFalse(observation["qualified"])
                self.assertIsNone(observation["interpretation"])
                self.assertNotIn("1.5", json.dumps(out["packet"]))
                self.assertNotIn("1.5", json.dumps(out["provenance"]))
                sidecar = out["provenance"]["measures"][MONTHLY]
                self.assertIsNone(sidecar.get("qualificationIdentity"))
                self.assertEqual(out["packet"]["owner"]["observedAtByMeasureId"],
                                 {MONTHLY: None})
                if quality == "stale":
                    # A stale read is still an allowed read: the source stays
                    # visible, only the number is withheld.
                    self.assertIn("sourceReference", sidecar)
                else:
                    self.assertNotIn("sourceReference", sidecar)
                    self.assertNotIn("clocks", sidecar)

    def test_missing_policy_keeps_null_qualification_and_no_interpretation(self):
        request = _request()
        measures = {MONTHLY: _measure(MONTHLY, value=1.5)}
        out = _project(request, measures=measures, evidence=_evidence(MONTHLY, _receipt(), None))
        observation = out["packet"]["current"]["observations"][0]
        self.assertEqual(observation["availability"], "available")
        self.assertFalse(observation["qualified"])
        self.assertIsNone(observation["qualificationIdentity"])
        self.assertIsNone(observation["interpretation"])
        self.assertIsNotNone(observation["contentIdentity"])
        self.assertIn("missing_publication_decision",
                      [entry["code"] for entry in out["diagnostics"]])
        self.assertNotIn("1.5", json.dumps(out["packet"]))

    def test_invalid_decisions_are_never_a_grant(self):
        variants = {
            "wrong_owner": _decision(MONTHLY, owner_ref="scripts/other.py"),
            "empty_policy": _decision(MONTHLY, policy_ref=""),
            "other_generation": _decision(MONTHLY, generation=OTHER_GENERATION),
            "wrong_receipt": _decision(MONTHLY, receipt_sha=OTHER_RECEIPT_SHA),
            "denied_permission": _decision(MONTHLY, value_permission="denied"),
            "arbitrary_identity": dict(_decision(MONTHLY), qualification_identity="f" * 64),
            "short_receipt": _decision(MONTHLY, receipt_sha="abc")}
        for name, decision in variants.items():
            with self.subTest(variant=name):
                request = _request()
                measures = {MONTHLY: _measure(MONTHLY, value=1.5)}
                out = _project(request, measures=measures,
                               evidence=_evidence(MONTHLY, {"receipt_sha256": "f" * 64},
                                                  decision))
                observation = out["packet"]["current"]["observations"][0]
                self.assertIsNone(observation["qualificationIdentity"])
                self.assertFalse(observation["qualified"])
                self.assertIsNone(observation["interpretation"])
                self.assertNotIn("1.5", json.dumps(out["packet"]))

    def test_missing_receipt_downgrades_to_unknown_and_scrubs(self):
        request = _request()
        measures = {MONTHLY: _measure(MONTHLY, value=1.5)}
        out = _project(request, measures=measures,
                       evidence=_evidence(MONTHLY, None, _decision(MONTHLY)))
        observation = out["packet"]["current"]["observations"][0]
        self.assertEqual(observation["availability"], "unavailable")
        self.assertFalse(observation["qualified"])
        self.assertIsNone(observation["contentIdentity"])
        self.assertIsNone(observation["qualificationIdentity"])
        self.assertIsNone(observation["interpretation"])
        sidecar = out["provenance"]["measures"][MONTHLY]
        self.assertNotIn("sourceReference", sidecar)
        self.assertNotIn("clocks", sidecar)
        self.assertNotIn("1.5", json.dumps(out["packet"]))

    def test_unsupported_measure_is_unavailable_never_not_applicable(self):
        request = _request([UNSUPPORTED])
        measures = {UNSUPPORTED: _measure(UNSUPPORTED, value=1.5)}
        out = _project(request, measures=measures,
                       evidence=_evidence(UNSUPPORTED, _receipt(), _decision(UNSUPPORTED)))
        observation = out["packet"]["current"]["observations"][0]
        self.assertEqual(observation["availability"], "unavailable")
        self.assertNotEqual(observation["availability"], "not_applicable")
        self.assertIsNone(observation["interpretation"])
        self.assertIn("unsupported_measure",
                      [entry["code"] for entry in out["diagnostics"]])

    def test_unit_mismatch_blocks_qualification(self):
        request = _request()
        measures = {MONTHLY: _measure(MONTHLY, unit="percent_gdp", value=1.5)}
        out = _project(request, measures=measures,
                       evidence=_evidence(MONTHLY, _receipt(), _decision(MONTHLY)))
        observation = out["packet"]["current"]["observations"][0]
        self.assertEqual(observation["availability"], "unavailable")
        self.assertIsNone(observation["qualificationIdentity"])
        self.assertIsNone(observation["interpretation"])
        self.assertIn("unit_mismatch", [entry["code"] for entry in out["diagnostics"]])

    def test_excluded_measure_never_carries_an_interpretation(self):
        request = _request()
        request["facts"] = {MONTHLY: {"excluded": True, "correction": False}}
        measures = {MONTHLY: _measure(MONTHLY, value=1.5)}
        out = _project(request, measures=measures,
                       evidence=_evidence(MONTHLY, _receipt(), _decision(MONTHLY)))
        observation = out["packet"]["current"]["observations"][0]
        self.assertTrue(observation["excluded"])
        self.assertIsNone(observation["interpretation"])
        self.assertNotIn("1.5", json.dumps(out["packet"]))


class EcbBindingTests(unittest.TestCase):
    def _ecb_request(self):
        request = _request([ECB])
        request["context"] = _context([ECB], researchMarket="EZ", currencyBasis="EUR")
        request["owner"]["marketLabel"] = "Euro area"
        request["owner"]["basisLabel"] = "EUR"
        request["owner"]["measureLabels"] = {ECB: "policy rate"}
        return request

    def test_qualified_ecb_policy_rate(self):
        measures = {ECB: _measure(ECB, value=2.5)}
        out = _project(self._ecb_request(), binding=_binding(market="EZ",
                                                             currency_basis="EUR"),
                       measures=measures,
                       evidence=_evidence(ECB, _ecb_receipt(), _ecb_decision()))
        observation = out["packet"]["current"]["observations"][0]
        self.assertTrue(observation["qualified"])
        self.assertEqual(observation["interpretation"]["value"], 2.5)
        self.assertIsNotNone(observation["qualificationIdentity"])

    def test_ecb_binding_must_match_exactly(self):
        decision = _ecb_decision()
        decision["binding"]["source_id"] = "D.U2.EUR.4F.KR.DFR.OTHER"
        out = _project(self._ecb_request(), binding=_binding(market="EZ",
                                                             currency_basis="EUR"),
                       measures={ECB: _measure(ECB, value=2.5)},
                       evidence=_evidence(ECB, _ecb_receipt(), decision))
        observation = out["packet"]["current"]["observations"][0]
        self.assertIsNone(observation["qualificationIdentity"])
        self.assertIsNone(observation["interpretation"])
        self.assertIn("invalid_publication_decision",
                      [entry["code"] for entry in out["diagnostics"]])


class ScopeAndContractTests(unittest.TestCase):
    def test_all_nine_context_strings_are_required(self):
        for key in CONTEXT_STRINGS:
            with self.subTest(context_key=key):
                request = _request()
                del request["context"][key]
                with self.assertRaises(ValueError):
                    _project(request)
                empty = _request()
                empty["context"][key] = ""
                with self.assertRaises(ValueError):
                    _project(empty)

    def test_binding_mismatches_are_refused(self):
        for key, value in (("periodIdentity", "2026-Q4"), ("currencyBasis", "USD"),
                           ("returnBasis", "yield"), ("researchMarket", "EZ"),
                           ("toolBindingVersion", "1")):
            with self.subTest(context_key=key):
                request = _request()
                request["context"][key] = value
                with self.assertRaises(ValueError):
                    _project(request)

    def test_generation_must_be_a_workspace_generation(self):
        for generation in ("nope", "im-workspace-generation:not-a-uuid",
                           "im-workspace-generation:"):
            with self.subTest(generation=generation):
                with self.assertRaises(ValueError):
                    _project(binding=_binding(generation=generation))

    def test_duplicate_selected_measure_is_refused(self):
        with self.assertRaises(ValueError):
            _project(_request([MONTHLY, MONTHLY]))

    def test_selected_measure_outside_the_market_prefix_is_refused(self):
        with self.assertRaises(ValueError):
            _project(_request([ECB]))

    def test_unknown_request_key_is_refused(self):
        request = _request()
        request["extra"] = 1
        with self.assertRaises(ValueError):
            _project(request)

    def test_unknown_evidence_key_is_refused(self):
        evidence = _evidence(MONTHLY, _receipt(), _decision(MONTHLY))
        evidence[ECB] = {"receipt_identity": None, "publication_decision": None,
                         "clocks": {}}
        with self.assertRaises(ValueError):
            _project(_request(), evidence=evidence)

    def test_complete_membership_requires_the_full_enumeration(self):
        request = _request([MONTHLY, ANNUAL])
        request["enumerated_measure_ids"] = [MONTHLY]
        with self.assertRaises(ValueError):
            _project(request)

    def test_partial_membership_never_removes_an_observation(self):
        request = _request([MONTHLY, ANNUAL])
        request["membership"] = "page"
        request["enumerated_measure_ids"] = [MONTHLY]
        out = _project(request, measures={MONTHLY: _measure(MONTHLY, value=1.5)},
                       evidence=_evidence(MONTHLY, _receipt(), _decision(MONTHLY)))
        observations = out["packet"]["current"]["observations"]
        self.assertEqual([item["id"] for item in observations], [MONTHLY, ANNUAL])
        self.assertEqual(observations[1]["availability"], "unavailable")
        self.assertIsNone(observations[1]["interpretation"])

    def test_missing_measure_creates_an_unavailable_observation(self):
        out = _project(_request([MONTHLY, ANNUAL]), measures={MONTHLY: _measure(MONTHLY)})
        observations = out["packet"]["current"]["observations"]
        self.assertEqual(len(observations), 2)
        self.assertEqual(observations[1]["id"], ANNUAL)
        self.assertEqual(observations[1]["availability"], "unavailable")

    def test_owner_may_not_supply_the_derived_observation_map(self):
        request = _request()
        request["owner"]["observedAtByMeasureId"] = {MONTHLY: OBSERVED_AT}
        with self.assertRaises(ValueError):
            _project(request)

    def test_required_measure_ids_must_be_a_subset_of_the_selection(self):
        request = _request()
        request["requirements"]["requiredMeasureIds"] = [ANNUAL]
        with self.assertRaises(ValueError):
            _project(request)

    def test_unmet_labels_must_align_with_the_prerequisites(self):
        request = _request()
        request["requirements"]["unmetPrerequisites"] = ["needs_prior_release"]
        with self.assertRaises(ValueError):
            _project(request)
        aligned = _request()
        aligned["requirements"]["unmetPrerequisites"] = ["needs_prior_release"]
        aligned["owner"]["unmetLabels"] = ["needs a prior release"]
        out = _project(aligned)
        self.assertEqual(out["packet"]["requirements"]["unmetPrerequisites"],
                         ["needs_prior_release"])
        self.assertEqual(out["packet"]["owner"]["unmetLabels"], ["needs a prior release"])

    def test_tombstone_collisions_are_refused(self):
        measures = {MONTHLY: _measure(MONTHLY)}
        cases = {
            "collides with a supplied measure": ({"tombstones": [MONTHLY]}, {}),
            "not a selected id": ({"tombstones": [ANNUAL]}, {}),
            "duplicate": ({"tombstones": [ANNUAL, ANNUAL]}, {"selected": [MONTHLY, ANNUAL]}),
            "read is not ok": ({"tombstones": [ANNUAL], "read": "denied"}, {})}
        for name, (patch, extra) in cases.items():
            with self.subTest(case=name):
                request = _request(extra.get("selected", (MONTHLY,)))
                request.update(patch)
                with self.assertRaises(ValueError):
                    _project(request, measures=measures)

    def test_tombstone_omits_the_auto_missing_observation(self):
        request = _request([MONTHLY, ANNUAL])
        request["tombstones"] = [ANNUAL]
        out = _project(request, measures={MONTHLY: _measure(MONTHLY, value=1.5)},
                       evidence=_evidence(MONTHLY, _receipt(), _decision(MONTHLY)))
        observations = out["packet"]["current"]["observations"]
        self.assertEqual([item["id"] for item in observations], [MONTHLY])
        self.assertEqual(out["packet"]["current"]["tombstones"], [ANNUAL])
        self.assertIsNone(out["packet"]["owner"]["observedAtByMeasureId"][ANNUAL])
        self.assertIn("tombstone_applied",
                      [entry["code"] for entry in out["diagnostics"]])


class PriorTests(unittest.TestCase):
    def test_absent_prior_remains_null(self):
        request = _request()
        request["prior"] = None
        request["prior_authorized"] = False
        out = _project(request)
        self.assertIsNone(out["packet"]["prior"])
        self.assertFalse(out["provenance"]["priorScopeChanged"])

    def test_prior_requires_an_explicit_authorisation_flag(self):
        with self.subTest(case="null prior with an authorised flag"):
            request = _request()
            request["prior_authorized"] = True
            with self.assertRaises(ValueError):
                _project(request)
        with self.subTest(case="supplied prior without the flag"):
            request = _request()
            request["prior"] = _prior()
            request["prior_authorized"] = False
            with self.assertRaises(ValueError):
                _project(request)

    def test_historical_prior_is_passed_through_unchanged(self):
        prior = _prior()
        request = _request()
        request["prior"] = prior
        request["prior_authorized"] = True
        out = _project(request)
        self.assertEqual(out["packet"]["prior"], prior)
        self.assertIn("scope_changed", [entry["code"] for entry in out["diagnostics"]])
        self.assertTrue(out["provenance"]["priorScopeChanged"])

    def test_prior_with_the_same_scope_is_not_a_scope_change(self):
        prior = _prior()
        current_context = _context([MONTHLY])
        for key in CONTEXT_STRINGS:
            prior[key] = current_context[key]
        request = _request()
        request["prior"] = prior
        request["prior_authorized"] = True
        out = _project(request)
        self.assertNotIn("scope_changed", [entry["code"] for entry in out["diagnostics"]])
        self.assertFalse(out["provenance"]["priorScopeChanged"])

    def test_duplicate_prior_observation_is_refused(self):
        prior = _prior()
        prior["observations"].append(copy.deepcopy(prior["observations"][0]))
        request = _request()
        request["prior"] = prior
        request["prior_authorized"] = True
        with self.assertRaises(ValueError):
            _project(request)

    def test_prior_tombstone_collision_is_refused(self):
        prior = _prior()
        prior["tombstones"] = [MONTHLY]
        request = _request()
        request["prior"] = prior
        request["prior_authorized"] = True
        with self.assertRaises(ValueError):
            _project(request)


class ClockAndProvenanceTests(unittest.TestCase):
    def test_caller_clocks_are_copied_and_never_invented(self):
        request = _request()
        out = _project(request, measures={MONTHLY: _measure(MONTHLY, value=1.5)},
                       evidence=_evidence(MONTHLY, _receipt(), _decision(MONTHLY)))
        owner = out["packet"]["owner"]
        for key in ("savedAt", "updatedAt", "sourceGenerationAt", "rightsAt"):
            self.assertIsNone(owner[key])
        # Only the explicitly supplied source clock may appear in the sidecar.
        self.assertEqual(out["provenance"]["measures"][MONTHLY]["clocks"], {"observation_at": OBSERVED_AT})
        self.assertEqual(TIMESTAMP_RE.findall(json.dumps(out["provenance"])), [])
        self.assertIsNone(out["provenance"]["publicationClock"])

    def test_supplied_caller_clocks_are_copied_verbatim(self):
        request = _request()
        request["owner"]["savedAt"] = "2026-10-02T09:00:00Z"
        request["owner"]["sourceGenerationAt"] = "2026-10-01T00:00:00Z"
        out = _project(request)
        self.assertEqual(out["packet"]["owner"]["savedAt"], "2026-10-02T09:00:00Z")
        self.assertEqual(out["packet"]["owner"]["sourceGenerationAt"], "2026-10-01T00:00:00Z")

    def test_denied_sidecar_exposes_no_source_url_and_no_date(self):
        request = _request()
        request["read"] = "denied"
        measures = {MONTHLY: _measure(MONTHLY, value=1.5, reason="reader_denied")}
        out = _project(request, measures=measures,
                       evidence=_evidence(MONTHLY, _receipt(), _decision(MONTHLY)))
        sidecar = json.dumps(out["provenance"])
        self.assertNotIn("http", sidecar)
        self.assertNotIn("://", sidecar)
        self.assertEqual(TIMESTAMP_RE.findall(sidecar), [])
        entry = out["provenance"]["measures"][MONTHLY]
        self.assertEqual(entry["availability"], "denied")
        self.assertFalse(entry["qualified"])
        for key in ("sourceReference", "receiptIdentity", "publicationDecision"):
            self.assertNotIn(key, entry)
        self.assertNotIn("1.5", json.dumps(out["packet"]))

    def test_denied_metadata_keeps_the_sidecar_scrubbed(self):
        request = _request()
        measures = {MONTHLY: _measure(MONTHLY, value=1.5, metadata="denied")}
        out = _project(request, measures=measures)
        entry = out["provenance"]["measures"][MONTHLY]
        self.assertEqual(entry["availability"], "denied")
        for key in ("sourceReference", "clocks", "receiptIdentity"):
            self.assertNotIn(key, entry)
        self.assertNotIn("http", json.dumps(out["provenance"]))

    def test_typed_native_period_is_preserved_in_the_sidecar(self):
        period = {"start": "2026-10-01", "end": "2026-11-01", "count": 1,
                  "count_basis": "release_periods"}
        request = _request()
        measures = {MONTHLY: _measure(MONTHLY, period=period, value=1.5)}
        out = _project(request, measures=measures,
                       evidence=_evidence(MONTHLY, _receipt(), _decision(MONTHLY)))
        self.assertEqual(out["provenance"]["measures"][MONTHLY]["period"], period)
        self.assertTrue(out["packet"]["current"]["observations"][0]["qualified"])

    def test_provenance_keeps_the_raw_reason(self):
        request = _request()
        measures = {MONTHLY: _measure(MONTHLY, value=1.5, reason="admitted_by_reader_v2")}
        out = _project(request, measures=measures,
                       evidence=_evidence(MONTHLY, _receipt(), _decision(MONTHLY)))
        self.assertEqual(out["provenance"]["measures"][MONTHLY]["reason"],
                         "admitted_by_reader_v2")


class HygieneTests(unittest.TestCase):
    def test_projection_does_not_touch_the_inputs(self):
        request, measures, evidence = _qualified_pair()
        request_copy = copy.deepcopy(request)
        measures_copy = copy.deepcopy(measures)
        evidence_copy = copy.deepcopy(evidence)
        _project(request, binding=_binding(), measures=measures, evidence=evidence)
        self.assertEqual(request, request_copy)
        self.assertEqual(measures, measures_copy)
        self.assertEqual(evidence, evidence_copy)

    def test_projection_performs_no_io_and_no_network(self):
        request, measures, evidence = _qualified_pair()
        opened = []
        real_open = builtins.open
        real_socket = socket.socket

        def trap_open(*args, **kwargs):
            opened.append(args)
            raise AssertionError("the projection must not open a file")

        def trap_socket(*args, **kwargs):
            raise AssertionError("the projection must not open a socket")

        builtins.open = trap_open
        socket.socket = trap_socket
        try:
            out = _project(request, measures=measures, evidence=evidence)
        finally:
            builtins.open = real_open
            socket.socket = real_socket
        self.assertEqual(opened, [])
        self.assertTrue(out["packet"]["current"]["observations"][0]["qualified"])

    def test_cycles_and_bool_as_number_are_refused(self):
        with self.subTest(case="cyclic request"):
            request = _request()
            facts = {}
            facts["self"] = facts
            request["facts"] = facts
            with self.assertRaises(ValueError):
                _project(request)
        with self.subTest(case="bool as a numeric value"):
            measures = {MONTHLY: _measure(MONTHLY, value=True)}
            with self.assertRaises(ValueError):
                _project(_request(), measures=measures)
        with self.subTest(case="bool as a binding version"):
            with self.assertRaises(ValueError):
                _project(binding=_binding(binding_version=True))
        with self.subTest(case="not a finite number"):
            measures = {MONTHLY: _measure(MONTHLY, value=float("nan"))}
            with self.assertRaises(ValueError):
                _project(_request(), measures=measures)


if __name__ == "__main__":
    unittest.main()


def test_generation_nonce_alone_cannot_manufacture_qualification_change():
    request = _request(); measures = {MONTHLY: _measure()}
    first = _project(request, measures=measures, evidence=_evidence(MONTHLY, _receipt(), _decision()))
    second = _project(request, binding=_binding(generation=OTHER_GENERATION), measures=measures,
                      evidence=_evidence(MONTHLY, _receipt(), _decision(generation=OTHER_GENERATION)))
    left, right = (x['packet']['current']['observations'][0] for x in [first, second])
    assert left['contentIdentity'] == right['contentIdentity']
    assert left['qualificationIdentity'] == right['qualificationIdentity']
    assert first['packet']['current']['generation'] != second['packet']['current']['generation']
    assert (first['provenance']['measures'][MONTHLY]['publicationDecision']['decision_ref'] !=
            second['provenance']['measures'][MONTHLY]['publicationDecision']['decision_ref'])


def test_stale_ecb_decision_does_not_disclose_its_numeric_binding_as_an_alternative_value():
    request = _request([ECB]); request['context']['researchMarket'] = 'EZ'
    out = _project(request, binding=_binding(market='EZ'),
        measures={ECB: _measure(ECB, quality='stale', reason='source_stale', value=2.5)},
        evidence=_evidence(ECB, _ecb_receipt(), _ecb_decision(value=2.5)))
    assert out['packet']['current']['observations'][0]['availability'] == 'stale'
    assert '2.5' not in json.dumps(out)
    assert out['provenance']['measures'][ECB]['publicationDecision'] is None
    assert any(x.get('source_reason') == 'source_stale' for x in out['diagnostics'])


def test_missing_receipt_cannot_become_a_fallback_content_identity():
    out = _project(_request(), measures={MONTHLY: _measure(value=1.5)},
                   evidence=_evidence(MONTHLY, None, _decision()))
    observation = out['packet']['current']['observations'][0]
    assert observation['contentIdentity'] is observation['qualificationIdentity'] is observation['interpretation'] is None
    assert '1.5' not in json.dumps(out)
