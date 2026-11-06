"""Tests for the public International generation contract and publication.

The coverage is discriminating rather than decorative:

* the contract shape is exact and closed, and carries no caller identity;
* the same inputs produce the same bytes, and the context identifiers stay
  stable when the publication nonce changes;
* a qualified measure is copied exactly, and its identities are the ones the
  accepted projection helpers derive;
* a stale, denied, unknown, receipt-less or policy-less field is downgraded
  and loses every number, source, clock and decision;
* a changed receipt, a changed permission and a changed policy document are
  discriminated;
* two markets never join;
* malformed, duplicated, non-finite and oversized inputs are refused;
* the published files carry the exact names, the mutable selector equals its
  immutable sidecar, and a mutated selector, a lost sidecar, a lost artifact,
  a symlinked path and a colliding write all fail closed;
* a failed publication keeps the previous pointer, and only an explicit
  unavailable publication replaces it;
* a missing publication is never answered with an older artifact.

Every fixture here is a scratch fixture.  These tests prove the contract and
the publication mechanics; they do not claim that the real Macro builder has
emitted a real generation.
"""

import builtins
import copy
import hashlib
import json
import os
import socket
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))

from lib.intl_generation_publication import (  # noqa: E402
    build_generation_contract,
    publish_generation,
    publish_unavailable_generation,
    read_generation_publication,
    serialize_generation,
)

GENERATION = "im-workspace-generation:4979a6c3-b834-4c69-8f1b-c8961cc5e11a"
OTHER_GENERATION = "im-workspace-generation:0f9c2b41-6f6e-4f0a-9a2b-1c3d4e5f6071"
EVALUATED_AT = "2026-10-01T00:00:00+00:00"
OTHER_EVALUATED_AT = "2026-10-02T00:00:00+00:00"

RECEIPT_SHA = "1" * 64
OTHER_RECEIPT_SHA = "2" * 64
ARTIFACT_SHA = "a" * 64
PROVENANCE_SHA = "b" * 64
POLICY_SHA = "c" * 64
OTHER_POLICY_SHA = "d" * 64

ECB = "EZ.policy_rate"
EZ_GDP = "EZ.gdp_yoy"
JP_GDP = "JP.gdp_yoy"
JP_CPI = "JP.cpi_yoy"
JP_YIELD = "JP.yield_10y"

SOURCE_URL = "https://example.invalid/source"
OBSERVED_AT = "2026-10-01"

CONFIG = {
    "markets": ["EZ", "JP"],
    "horizons": ["1m", "3m"],
    "bases": ["local", "usd_unhedged"],
    "fields": {
        "EZ": ["policy_rate", "gdp_yoy"],
        "JP": ["gdp_yoy", "cpi_yoy", "yield_10y"],
    },
}

CONTRACT_KEYS = {
    "schema", "asof", "generation", "binding_version", "evaluated_at",
    "contexts", "measures", "policies"}
CONTEXT_KEYS = {
    "id", "market", "horizon", "currency_basis", "return_basis", "measure_ids"}
MEASURE_KEYS = {
    "native_measure", "native_evidence", "content_identity", "qualification_identity", "policy_identity"}
NATIVE_KEYS = {
    "quality", "reason", "metadata", "value_permission", "value", "unit",
    "instrument", "period", "observation_at", "calculation_at",
    "source_reference", "evidence_key"}
EVIDENCE_KEYS = {"receipt_identity", "publication_decision", "clocks"}
POLICY_KEYS = {
    "metadata", "value_permission", "policy_ref", "policy_document_sha256",
    "policy_identity"}
DESCRIPTOR_KEYS = {
    "schema", "asof", "state", "generation", "artifact_name", "artifact_sha256",
    "artifact_bytes", "current_policies"}

#: No caller identity may ever appear in the public contract.  The admitted
#: publication decision names the publishing script; that fixed public path is
#: not a caller, a principal or a private reference, and the decision is
#: copied exactly so that a consumer can re-verify it.
FORBIDDEN_KEYS = {
    "owner", "question", "query", "cohort", "saved", "savedAt", "updatedAt",
    "principal", "account", "private", "user", "email"}


def _measure(sid, *, value=1.5, unit="percent", quality="qualified", reason=None,
             metadata="allowed", permission="allowed", instrument=None,
             observation_at=OBSERVED_AT, source_reference=None, evidence_key=None,
             period=None, calculation_at=None):
    """A closed native measure in the shape the admit helpers return."""
    if instrument is None:
        market = sid.split(".")[0]
        instrument = {"kind": "macro_yoy", "id": "NATIVE.%s" % sid,
                      "market_id": market}
    if source_reference is None:
        source_reference = "%s/%s" % (SOURCE_URL, sid)
    if evidence_key is None:
        evidence_key = "evidence-%s" % sid
    return {
        "quality": quality,
        "reason": reason,
        "metadata": metadata,
        "value_permission": permission,
        "value": value,
        "unit": unit,
        "instrument": instrument,
        "period": period,
        "observation_at": observation_at,
        "calculation_at": calculation_at,
        "source_reference": source_reference,
        "evidence_key": evidence_key,
    }


def _ecb_measure(**overrides):
    overrides.setdefault("value", 2.5)
    overrides.setdefault("unit", "percent")
    overrides.setdefault("instrument", {"kind": "official_policy",
                                         "id": "deposit_facility",
                                         "market_id": "EZ"})
    return _measure(ECB, **overrides)


def _ecb_receipt():
    return {"artifact_sha256": ARTIFACT_SHA, "provenance_sha256": PROVENANCE_SHA}


def _receipt(sha=RECEIPT_SHA):
    return {"receipt_sha256": sha}


def _ecb_decision(generation=GENERATION, value=2.5, unit="percent",
                  observation_at=OBSERVED_AT, policy_ref="policy/ez-core-v1",
                  **overrides):
    decision = {
        "owner_ref": "scripts/build_intl.py",
        "policy_ref": policy_ref,
        "decision_ref": "%s:%s" % (generation, ECB),
        "metadata": "allowed",
        "value_permission": "allowed",
        "binding": {"market_id": "EZ", "field": "policy_rate",
                    "instrument_id": "deposit_facility",
                    "source_id": "D.U2.EUR.4F.KR.DFR.LEV",
                    "artifact_sha256": ARTIFACT_SHA,
                    "provenance_sha256": PROVENANCE_SHA,
                    "observation_at": observation_at, "value": value, "unit": unit},
    }
    decision.update(overrides)
    return decision


def _decision(sid, generation=GENERATION, receipt_sha=RECEIPT_SHA,
              policy_ref="policy/jp-core-v3", **overrides):
    decision = {
        "owner_ref": "scripts/build_intl.py",
        "policy_ref": policy_ref,
        "decision_ref": "%s:%s" % (generation, sid),
        "metadata": "allowed",
        "value_permission": "allowed",
        "binding": {"field": sid, "receipt_sha256": receipt_sha},
    }
    decision.update(overrides)
    return decision


def _evidence(sid, receipt=None, decision=None, clocks=None):
    """One closed evidence entry: the receipt, the decision and the clocks."""
    if clocks is None:
        clocks = {"observation_at": OBSERVED_AT}
    return {"receipt_identity": receipt, "publication_decision": decision,
            "clocks": clocks}


def _qualified_inputs():
    """A qualified EZ + JP fixture with an explicit policy revision."""
    measures = {
        ECB: _ecb_measure(),
        EZ_GDP: _measure(EZ_GDP, value=0.8),
        JP_YIELD: _measure(JP_YIELD, value=1.62,
                            instrument={"kind": "sovereign_10y",
                                        "id": "IRLTLT01JPM156N",
                                        "market_id": "JP"}),
    }
    evidence = {}
    evidence[ECB] = _evidence(ECB, _ecb_receipt(), _ecb_decision())
    evidence[EZ_GDP] = _evidence(EZ_GDP, _receipt(), _decision(EZ_GDP))
    evidence[JP_YIELD] = _evidence(JP_YIELD, _receipt(OTHER_RECEIPT_SHA),
                                   _decision(JP_YIELD, receipt_sha=OTHER_RECEIPT_SHA))
    documents = {ECB: POLICY_SHA, EZ_GDP: POLICY_SHA, JP_YIELD: OTHER_POLICY_SHA}
    return measures, evidence, documents


def _build(config=None, measures=None, evidence=None, documents=None,
           generation=GENERATION, evaluated_at=EVALUATED_AT, binding_version=2):
    if measures is None and evidence is None and documents is None:
        measures, evidence, documents = _qualified_inputs()
    return build_generation_contract(
        config=config if config is not None else copy.deepcopy(CONFIG),
        binding_version=binding_version,
        measures=measures if measures is not None else {},
        evidence=evidence if evidence is not None else {},
        evaluated_at=evaluated_at,
        policy_document_sha256=documents if documents is not None else {},
        generation=generation)


def _context_id(market, horizon, basis):
    payload = json.dumps({"binding_version": 2, "market": market, "horizon": horizon,
                          "currency_basis": basis, "return_basis": "price"},
                         sort_keys=True, separators=(",", ":"))
    return "intl-workspace-context:sha256:" + hashlib.sha256(
        payload.encode("utf-8")).hexdigest()


def _keys_of(value, found=None):
    """Every dictionary key that appears anywhere inside a plain JSON tree."""
    if found is None:
        found = set()
    if isinstance(value, dict):
        for key, item in value.items():
            found.add(key)
            _keys_of(item, found)
    elif isinstance(value, list):
        for item in value:
            _keys_of(item, found)
    return found


class ContractShapeTests(unittest.TestCase):
    def test_contract_carries_exactly_the_public_keys(self):
        contract = _build()
        self.assertEqual(set(contract), CONTRACT_KEYS)
        self.assertEqual(contract["schema"], "intl.workspace_generation.v1")
        self.assertEqual(contract["binding_version"], 2)
        self.assertIsNone(contract["asof"])
        self.assertEqual(contract["generation"], GENERATION)
        self.assertEqual(contract["evaluated_at"], EVALUATED_AT)
        for context in contract["contexts"]:
            self.assertEqual(set(context), CONTEXT_KEYS)
            self.assertEqual(context["return_basis"], "price")
        for sid, entry in contract["measures"].items():
            self.assertEqual(set(entry), MEASURE_KEYS, sid)
            self.assertEqual(set(entry["native_measure"]), NATIVE_KEYS, sid)
            self.assertEqual(set(entry["native_evidence"]), EVIDENCE_KEYS, sid)
        for sid, entry in contract["policies"].items():
            self.assertEqual(set(entry), POLICY_KEYS, sid)

    def test_contract_carries_no_caller_identity(self):
        contract = _build()
        found = _keys_of(contract)
        leaked = found & FORBIDDEN_KEYS
        self.assertEqual(leaked, set())
        self.assertEqual(contract["policies"][ECB]["policy_ref"], "policy/ez-core-v1")

    def test_the_only_owner_reference_is_the_publication_script(self):
        contract = _build()
        decision = contract["measures"][ECB]["native_evidence"]["publication_decision"]
        self.assertEqual(decision["owner_ref"], "scripts/build_intl.py")
        # No caller-owned identity reaches the contract at all.
        payload = json.dumps(contract)
        self.assertNotIn("owner-1", payload)
        self.assertNotIn("cohort", payload)
        self.assertNotIn("question", payload)

    def test_asof_is_never_taken_from_a_clock(self):
        contract = _build()
        self.assertIsNone(contract["asof"])
        self.assertEqual(contract["evaluated_at"], EVALUATED_AT)
        later = _build(evaluated_at=OTHER_EVALUATED_AT)
        self.assertEqual(later["evaluated_at"], OTHER_EVALUATED_AT)

    def test_contexts_enumerate_the_configured_dimensions(self):
        contract = _build()
        expected = set()
        for market in CONFIG["markets"]:
            for horizon in CONFIG["horizons"]:
                for basis in CONFIG["bases"]:
                    expected.add(_context_id(market, horizon, basis))
        self.assertEqual({context["id"] for context in contract["contexts"]}, expected)
        self.assertEqual(len(contract["contexts"]), 8)

    def test_context_identifiers_follow_the_documented_formula(self):
        contract = _build()
        for context in contract["contexts"]:
            self.assertEqual(
                context["id"],
                _context_id(context["market"], context["horizon"],
                            context["currency_basis"]))

    def test_native_selected_measure_ids_are_exact(self):
        contract = _build()
        for context in contract["contexts"]:
            self.assertEqual(context["measure_ids"],
                             ["%s.%s" % (context["market"], field)
                              for field in CONFIG["fields"][context["market"]]])

    def test_context_identifiers_are_stable_across_the_publication_nonce(self):
        first = _build(generation=GENERATION)
        second = _build(generation=OTHER_GENERATION)
        self.assertNotEqual(first["generation"], second["generation"])
        self.assertEqual([context["id"] for context in first["contexts"]],
                         [context["id"] for context in second["contexts"]])
        self.assertNotEqual(serialize_generation(first), serialize_generation(second))

    def test_the_same_inputs_produce_the_same_bytes(self):
        first = serialize_generation(_build())
        second = serialize_generation(_build())
        self.assertEqual(first, second)
        self.assertEqual(hashlib.sha256(first).hexdigest(),
                         hashlib.sha256(second).hexdigest())

    def test_a_fresh_nonce_still_mints_a_valid_generation(self):
        contract = build_generation_contract(
            config=copy.deepcopy(CONFIG), binding_version=2, measures={},
            evidence={}, evaluated_at=EVALUATED_AT, policy_document_sha256={})
        self.assertTrue(contract["generation"].startswith("im-workspace-generation:"))


class QualificationTests(unittest.TestCase):
    def test_a_qualified_measure_is_copied_exactly(self):
        measures, evidence, documents = _qualified_inputs()
        contract = _build(measures=measures, evidence=evidence, documents=documents)
        entry = contract["measures"][ECB]
        self.assertEqual(entry["native_measure"], measures[ECB])
        self.assertEqual(entry["native_evidence"]["receipt_identity"], _ecb_receipt())
        self.assertEqual(entry["native_evidence"]["publication_decision"],
                         _ecb_decision())
        self.assertIsNotNone(entry["content_identity"])
        self.assertIsNotNone(entry["qualification_identity"])

    def test_the_identities_are_the_ones_the_projection_helpers_derive(self):
        from lib.intl_investigation_projection import (
            _content_identity, _qualification_identity)
        measures, evidence, documents = _qualified_inputs()
        contract = _build(measures=measures, evidence=evidence, documents=documents)
        for sid, receipt, decision in (
                (ECB, _ecb_receipt(), _ecb_decision()),
                (EZ_GDP, _receipt(), _decision(EZ_GDP)),
                (JP_YIELD, _receipt(OTHER_RECEIPT_SHA),
                 _decision(JP_YIELD, receipt_sha=OTHER_RECEIPT_SHA))):
            entry = contract["measures"][sid]
            self.assertEqual(entry["content_identity"],
                             _content_identity(sid, measures[sid], receipt), sid)
            self.assertEqual(entry["qualification_identity"],
                             _qualification_identity(sid, decision, receipt), sid)

    def test_a_changed_receipt_changes_both_identities(self):
        first_measures, first_evidence, documents = _qualified_inputs()
        first = _build(measures=first_measures, evidence=first_evidence,
                       documents=documents)
        second_measures, second_evidence, _ = _qualified_inputs()
        second_evidence[JP_YIELD] = _evidence(
            JP_YIELD, _receipt("9" * 64),
            _decision(JP_YIELD, receipt_sha="9" * 64))
        second = _build(measures=second_measures, evidence=second_evidence,
                        documents=documents)
        left = first["measures"][JP_YIELD]
        right = second["measures"][JP_YIELD]
        self.assertNotEqual(left["content_identity"], right["content_identity"])
        self.assertNotEqual(left["qualification_identity"],
                            right["qualification_identity"])

    def test_a_changed_policy_document_changes_only_the_policy_identity(self):
        measures, evidence, documents = _qualified_inputs()
        first = _build(measures=measures, evidence=evidence, documents=documents)
        second_documents = dict(documents)
        second_documents[JP_YIELD] = "e" * 64
        second = _build(measures=measures, evidence=evidence,
                        documents=second_documents)
        left = first["measures"][JP_YIELD]
        right = second["measures"][JP_YIELD]
        self.assertEqual(left["content_identity"], right["content_identity"])
        self.assertEqual(left["qualification_identity"],
                         right["qualification_identity"])
        self.assertNotEqual(first["policies"][JP_YIELD]["policy_identity"],
                            second["policies"][JP_YIELD]["policy_identity"])

    def test_a_changed_permission_is_never_an_export(self):
        measures, evidence, documents = _qualified_inputs()
        measures[JP_YIELD]["value_permission"] = "denied"
        evidence[JP_YIELD] = _evidence(JP_YIELD, _receipt(OTHER_RECEIPT_SHA),
                                       _decision(JP_YIELD,
                                                 receipt_sha=OTHER_RECEIPT_SHA,
                                                 value_permission="denied"))
        contract = _build(measures=measures, evidence=evidence, documents=documents)
        entry = contract["measures"][JP_YIELD]
        self.assertEqual(entry["native_measure"]["quality"], "denied")
        self.assertEqual(entry["native_measure"]["reason"], "value_denied")
        self.assertIsNone(entry["content_identity"])
        self.assertIsNone(entry["qualification_identity"])
        self.assertIsNone(entry["native_measure"]["value"])
        self.assertEqual(contract["policies"][JP_YIELD]["policy_ref"], None)
        self.assertEqual(contract["policies"][JP_YIELD]["policy_identity"], None)

    def test_a_missing_policy_document_withholds_the_export(self):
        measures, evidence, documents = _qualified_inputs()
        del documents[JP_YIELD]
        contract = _build(measures=measures, evidence=evidence, documents=documents)
        entry = contract["measures"][JP_YIELD]
        self.assertEqual(entry["native_measure"]["quality"], "unknown")
        self.assertEqual(entry["native_measure"]["reason"], "disclosure_unknown")
        self.assertIsNone(entry["native_measure"]["value"])
        self.assertIsNone(entry["content_identity"])
        self.assertIsNone(entry["qualification_identity"])
        self.assertEqual(contract["policies"][JP_YIELD]["policy_identity"], None)
        self.assertEqual(contract["policies"][JP_YIELD]["policy_document_sha256"], None)

    def test_an_absent_receipt_cannot_become_a_qualification(self):
        measures, evidence, documents = _qualified_inputs()
        evidence[JP_YIELD] = _evidence(JP_YIELD, None,
                                       _decision(JP_YIELD, receipt_sha=OTHER_RECEIPT_SHA))
        contract = _build(measures=measures, evidence=evidence, documents=documents)
        entry = contract["measures"][JP_YIELD]
        self.assertEqual(entry["native_measure"]["quality"], "unknown")
        self.assertEqual(entry["native_measure"]["reason"], "disclosure_unknown")
        self.assertIsNone(entry["content_identity"])
        self.assertIsNone(entry["qualification_identity"])
        self.assertEqual(entry["native_evidence"],
                         {"receipt_identity": None, "publication_decision": None,
                          "clocks": {}})

    def test_a_decision_for_another_generation_is_never_an_export(self):
        measures, evidence, documents = _qualified_inputs()
        evidence[JP_YIELD] = _evidence(
            JP_YIELD, _receipt(OTHER_RECEIPT_SHA),
            _decision(JP_YIELD, generation=OTHER_GENERATION,
                      receipt_sha=OTHER_RECEIPT_SHA))
        contract = _build(measures=measures, evidence=evidence, documents=documents)
        entry = contract["measures"][JP_YIELD]
        self.assertEqual(entry["native_measure"]["quality"], "unknown")
        self.assertIsNone(entry["qualification_identity"])

    def test_a_stale_measure_keeps_its_actual_state_and_loses_the_rest(self):
        measures, evidence, documents = _qualified_inputs()
        measures[JP_CPI] = _measure(JP_CPI, quality="stale", reason="source_stale",
                                    value=2.9)
        contract = _build(measures=measures, evidence=evidence, documents=documents)
        entry = contract["measures"][JP_CPI]
        self.assertEqual(entry["native_measure"]["quality"], "stale")
        self.assertEqual(entry["native_measure"]["reason"], "source_stale")
        self.assertEqual(entry["native_measure"]["metadata"], "allowed")
        self.assertEqual(entry["native_measure"]["value_permission"], "allowed")
        for field in ("value", "unit", "instrument", "period", "observation_at",
                      "calculation_at", "source_reference", "evidence_key"):
            self.assertIsNone(entry["native_measure"][field], field)
        self.assertEqual(entry["native_evidence"],
                         {"receipt_identity": None, "publication_decision": None,
                          "clocks": {}})
        self.assertIsNone(entry["content_identity"])
        self.assertIsNone(entry["qualification_identity"])

    def test_a_denied_measure_never_exposes_its_policy(self):
        measures, evidence, documents = _qualified_inputs()
        measures[JP_GDP] = _measure(JP_GDP, quality="denied",
                                    reason="metadata_denied", metadata="denied",
                                    permission="denied", value=None, unit=None,
                                    source_reference=None, evidence_key=None)
        contract = _build(measures=measures, evidence=evidence, documents=documents)
        entry = contract["measures"][JP_GDP]
        self.assertEqual(entry["native_measure"]["quality"], "denied")
        self.assertEqual(entry["native_measure"]["reason"], "metadata_denied")
        self.assertEqual(entry["native_measure"]["metadata"], "denied")
        self.assertIsNone(entry["native_measure"]["value"])
        self.assertIsNone(entry["content_identity"])
        policy = contract["policies"][JP_GDP]
        self.assertEqual(policy["metadata"], "denied")
        self.assertEqual(policy["policy_ref"], None)
        self.assertEqual(policy["policy_document_sha256"], None)
        self.assertEqual(policy["policy_identity"], None)

    def test_an_unknown_measure_keeps_its_actual_permissions(self):
        measures, evidence, documents = _qualified_inputs()
        measures[JP_GDP] = _measure(JP_GDP, quality="unknown",
                                    reason="source_unknown", metadata="unknown",
                                    permission="unknown", value=None, unit=None,
                                    source_reference=None, evidence_key=None)
        contract = _build(measures=measures, evidence=evidence, documents=documents)
        entry = contract["measures"][JP_GDP]
        self.assertEqual(entry["native_measure"]["quality"], "unknown")
        self.assertEqual(entry["native_measure"]["reason"], "source_unknown")
        self.assertEqual(entry["native_measure"]["metadata"], "unknown")
        self.assertEqual(entry["native_measure"]["value_permission"], "unknown")
        self.assertIsNone(entry["native_measure"]["value"])

    def test_a_missing_measure_stays_visible_as_missing(self):
        measures, evidence, documents = _qualified_inputs()
        # The config declares JP.gdp_yoy, but no admit helper supplied it.
        self.assertNotIn(JP_GDP, measures)
        contract = _build(measures=measures, evidence=evidence, documents=documents)
        entry = contract["measures"][JP_GDP]
        self.assertEqual(entry["native_measure"]["quality"], "missing")
        self.assertEqual(entry["native_measure"]["reason"], "not_supplied")
        self.assertIsNone(entry["native_measure"]["value"])
        self.assertIsNone(entry["content_identity"])
        self.assertEqual(entry["native_evidence"],
                         {"receipt_identity": None, "publication_decision": None,
                          "clocks": {}})
        self.assertEqual(contract["policies"][JP_GDP]["metadata"], "unknown")
        self.assertEqual(contract["policies"][JP_GDP]["policy_identity"], None)

    def test_an_unsupported_unit_is_never_exported(self):
        measures, evidence, documents = _qualified_inputs()
        measures[JP_GDP] = _measure(JP_GDP, value=1.2, unit="percent_gdp")
        contract = _build(measures=measures, evidence=evidence, documents=documents)
        entry = contract["measures"][JP_GDP]
        self.assertEqual(entry["native_measure"]["quality"], "unknown")
        self.assertEqual(entry["native_measure"]["reason"], "source_unknown")
        self.assertIsNone(entry["native_measure"]["value"])
        self.assertIsNone(entry["native_measure"]["unit"])

    def test_an_unqualified_output_never_carries_a_decision_binding(self):
        measures, evidence, documents = _qualified_inputs()
        measures[ECB] = _ecb_measure(quality="stale", reason="source_stale")
        contract = _build(measures=measures, evidence=evidence, documents=documents)
        payload = serialize_generation(contract).decode("utf-8")
        entry = contract["measures"][ECB]
        self.assertIsNone(entry["native_evidence"]["publication_decision"])
        self.assertNotIn("2.5", payload)
        self.assertNotIn("D.U2.EUR.4F.KR.DFR.LEV", payload)

    def test_two_markets_never_join(self):
        measures, evidence, documents = _qualified_inputs()
        # A JP field that carries the EZ instrument is refused outright.
        measures[JP_YIELD]["instrument"] = {"kind": "official_policy",
                                            "id": "deposit_facility",
                                            "market_id": "EZ"}
        with self.assertRaises(ValueError):
            _build(measures=measures, evidence=evidence, documents=documents)

    def test_the_ecb_receipt_family_does_not_qualify_another_field(self):
        measures, evidence, documents = _qualified_inputs()
        evidence[JP_YIELD] = _evidence(JP_YIELD, _ecb_receipt(),
                                       _decision(JP_YIELD))
        contract = _build(measures=measures, evidence=evidence, documents=documents)
        entry = contract["measures"][JP_YIELD]
        self.assertEqual(entry["native_measure"]["quality"], "unknown")
        self.assertIsNone(entry["qualification_identity"])

    def test_an_ez_decision_never_qualifies_a_jp_field(self):
        measures, evidence, documents = _qualified_inputs()
        decision = _ecb_decision()
        decision["decision_ref"] = "%s:%s" % (GENERATION, JP_YIELD)
        evidence[JP_YIELD] = _evidence(JP_YIELD, _receipt(OTHER_RECEIPT_SHA),
                                       decision)
        contract = _build(measures=measures, evidence=evidence, documents=documents)
        self.assertIsNone(contract["measures"][JP_YIELD]["qualification_identity"])

    def test_the_builder_does_not_touch_its_inputs(self):
        measures, evidence, documents = _qualified_inputs()
        measures_copy = copy.deepcopy(measures)
        evidence_copy = copy.deepcopy(evidence)
        documents_copy = copy.deepcopy(documents)
        contract = _build(measures=measures, evidence=evidence, documents=documents)
        contract["measures"][ECB]["native_measure"]["value"] = 99
        self.assertEqual(measures, measures_copy)
        self.assertEqual(evidence, evidence_copy)
        self.assertEqual(documents, documents_copy)

    def test_the_builder_performs_no_io_and_no_network(self):
        opened = []
        real_open = builtins.open
        real_socket = socket.socket

        def trap_open(*args, **kwargs):
            opened.append(args)
            raise AssertionError("the contract builder must not open a file")

        def trap_socket(*args, **kwargs):
            raise AssertionError("the contract builder must not open a socket")

        builtins.open = trap_open
        socket.socket = trap_socket
        try:
            contract = _build()
        finally:
            builtins.open = real_open
            socket.socket = real_socket
        self.assertEqual(opened, [])
        self.assertEqual(len(contract["contexts"]), 8)


class InputContractTests(unittest.TestCase):
    def test_an_unknown_config_dimension_is_refused(self):
        config = copy.deepcopy(CONFIG)
        config["extra"] = ["x"]
        with self.assertRaises(ValueError):
            _build(config=config)
        config = copy.deepcopy(CONFIG)
        del config["bases"]
        with self.assertRaises(ValueError):
            _build(config=config)

    def test_a_duplicate_config_dimension_is_refused(self):
        config = copy.deepcopy(CONFIG)
        config["markets"] = ["EZ", "EZ"]
        with self.assertRaises(ValueError):
            _build(config=config)
        config = copy.deepcopy(CONFIG)
        config["fields"]["JP"] = ["gdp_yoy", "gdp_yoy"]
        with self.assertRaises(ValueError):
            _build(config=config)

    def test_config_fields_must_cover_exactly_the_markets(self):
        config = copy.deepcopy(CONFIG)
        config["fields"]["US"] = ["gdp_yoy"]
        with self.assertRaises(ValueError):
            _build(config=config)
        config = copy.deepcopy(CONFIG)
        del config["fields"]["JP"]
        with self.assertRaises(ValueError):
            _build(config=config)

    def test_the_native_registry_market_shape_is_accepted(self):
        config = copy.deepcopy(CONFIG)
        config["markets"] = [
            {"market_id": "EZ", "name_en": "Euro area", "name_zh": "欧元区"},
            {"market_id": "JP", "name_en": "Japan", "name_zh": "日本"},
        ]
        contract = _build(config=config)
        self.assertEqual({context["market"] for context in contract["contexts"]},
                         {"EZ", "JP"})
        # The display names are not part of the public contract.
        self.assertNotIn("Euro area", json.dumps(contract))
        self.assertNotIn("name_en", json.dumps(contract))

    def test_a_duplicated_market_entry_is_refused_in_both_shapes(self):
        config = copy.deepcopy(CONFIG)
        config["markets"] = ["EZ", {"market_id": "EZ"}]
        with self.assertRaises(ValueError):
            _build(config=config)

    def test_too_many_contexts_are_refused(self):
        config = {"markets": ["EZ"], "horizons": ["h%d" % i for i in range(12)],
                  "bases": ["b%d" % i for i in range(12)], "fields": {"EZ": []}}
        with self.assertRaises(ValueError):
            _build(config=config)

    def test_an_extra_measure_is_refused(self):
        measures, evidence, documents = _qualified_inputs()
        measures["JP.not_a_field"] = _measure("JP.not_a_field")
        with self.assertRaises(ValueError):
            _build(measures=measures, evidence=evidence, documents=documents)

    def test_an_extra_evidence_entry_is_refused(self):
        measures, evidence, documents = _qualified_inputs()
        evidence["JP.not_a_field"] = _evidence("JP.not_a_field")
        with self.assertRaises(ValueError):
            _build(measures=measures, evidence=evidence, documents=documents)

    def test_a_malformed_measure_is_refused(self):
        measures, evidence, documents = _qualified_inputs()
        measures[JP_YIELD]["extra"] = 1
        with self.assertRaises(ValueError):
            _build(measures=measures, evidence=evidence, documents=documents)
        measures, evidence, documents = _qualified_inputs()
        del measures[JP_YIELD]["unit"]
        with self.assertRaises(ValueError):
            _build(measures=measures, evidence=evidence, documents=documents)

    def test_a_malformed_evidence_entry_is_refused(self):
        measures, evidence, documents = _qualified_inputs()
        evidence[JP_YIELD]["extra"] = 1
        with self.assertRaises(ValueError):
            _build(measures=measures, evidence=evidence, documents=documents)
        measures, evidence, documents = _qualified_inputs()
        evidence[JP_YIELD]["clocks"] = {"unknown_clock": "x"}
        with self.assertRaises(ValueError):
            _build(measures=measures, evidence=evidence, documents=documents)

    def test_a_non_finite_value_is_refused(self):
        measures, evidence, documents = _qualified_inputs()
        measures[JP_YIELD]["value"] = float("nan")
        with self.assertRaises(ValueError):
            _build(measures=measures, evidence=evidence, documents=documents)

    def test_an_invalid_generation_is_refused(self):
        for generation in ("nope", "im-workspace-generation:not-a-uuid",
                           "im-workspace-generation:"):
            with self.subTest(generation=generation):
                with self.assertRaises(ValueError):
                    _build(generation=generation)

    def test_a_non_utc_evaluated_at_is_refused(self):
        for evaluated_at in ("2026-10-01", "2026-10-01T00:00:00+02:00", "", 17):
            with self.subTest(evaluated_at=evaluated_at):
                with self.assertRaises(ValueError):
                    _build(evaluated_at=evaluated_at)

    def test_an_invalid_binding_version_is_refused(self):
        for version in (1, 3, "2", True):
            with self.subTest(binding_version=version):
                with self.assertRaises(ValueError):
                    _build(binding_version=version)

    def test_a_non_plain_json_input_is_refused(self):
        measures, evidence, documents = _qualified_inputs()
        measures["JP.gdp_yoy"] = _measure(JP_GDP)
        measures["JP.gdp_yoy"]["instrument"] = {"kind": "macro_yoy"}
        with self.assertRaises(ValueError):
            _build(measures=measures, evidence=evidence, documents=documents)

    def test_an_oversized_artifact_is_refused(self):
        measures, evidence, documents = _qualified_inputs()
        # A qualified field is copied exactly, so an oversized source would
        # exceed the published artifact limit.
        measures[JP_YIELD]["source_reference"] = "x" * (9 * 1024 * 1024)
        contract = _build(measures=measures, evidence=evidence, documents=documents)
        with self.assertRaises(ValueError):
            serialize_generation(contract)

    def test_a_malformed_contract_is_refused_by_the_serializer(self):
        contract = _build()
        contract["asof"] = "2026-10-01"
        with self.assertRaises(ValueError):
            serialize_generation(contract)
        contract = _build()
        contract["extra"] = 1
        with self.assertRaises(ValueError):
            serialize_generation(contract)


class HygieneTests(unittest.TestCase):
    def test_hostile_text_is_serialized_safely(self):
        hostile = '</script><script>alert("x")</script>\x00\r\n\t'
        measures, evidence, documents = _qualified_inputs()
        measures[JP_YIELD]["source_reference"] = hostile
        contract = _build(measures=measures, evidence=evidence, documents=documents)
        payload = serialize_generation(contract)
        parsed = json.loads(payload.decode("utf-8"))
        self.assertEqual(parsed["measures"][JP_YIELD]["native_measure"]
                         ["source_reference"], hostile)
        # The hostile text stays data: it cannot terminate the JSON string and
        # no raw control character reaches the published bytes.
        self.assertNotIn(b"\x00", payload)
        self.assertNotIn(b"\r", payload)
        self.assertNotIn(b"\n", payload)
        self.assertNotIn(b"\t", payload)
        self.assertIn(b'\\"x\\"', payload)

    def test_hostile_text_in_a_policy_reference_is_preserved_as_json(self):
        hostile = "policy/<script>& "
        measures, evidence, documents = _qualified_inputs()
        evidence[EZ_GDP] = _evidence(EZ_GDP, _receipt(),
                                     _decision(EZ_GDP, policy_ref=hostile))
        contract = _build(measures=measures, evidence=evidence, documents=documents)
        payload = serialize_generation(contract).decode("utf-8")
        parsed = json.loads(payload)
        self.assertEqual(parsed["policies"]["EZ.gdp_yoy"]["policy_ref"], hostile)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.data_root = self._temp.name
        self.generations = os.path.join(self.data_root, "intl", "publication",
                                        "generations")
        self.addCleanup(self._temp.cleanup)

    def _publish(self, contract=None):
        contract = contract if contract is not None else _build()
        return publish_generation(data_root=self.data_root, contract=contract)

    def test_publication_round_trip(self):
        contract = _build()
        descriptor = self._publish(contract)
        self.assertEqual(descriptor["state"], "ready")
        self.assertEqual(descriptor["schema"], "intl.workspace_generation_current.v1")
        self.assertIsNone(descriptor["asof"])
        self.assertEqual(descriptor["generation"], GENERATION)
        self.assertEqual(descriptor["artifact_bytes"],
                         len(serialize_generation(contract)))
        self.assertEqual(descriptor["artifact_sha256"],
                         hashlib.sha256(serialize_generation(contract)).hexdigest())
        self.assertEqual(descriptor["current_policies"], contract["policies"])

        read = read_generation_publication(data_root=self.data_root)
        self.assertEqual(read["status"], "ready")
        self.assertEqual(read["descriptor"], descriptor)
        self.assertEqual(read["artifact_bytes"], serialize_generation(contract))

    def test_the_published_files_carry_the_exact_names(self):
        descriptor = self._publish()
        names = sorted(os.listdir(self.generations))
        self.assertEqual(len(names), 3)
        self.assertIn("intl_generation_current.json", names)
        self.assertIn(descriptor["artifact_name"], names)
        sidecar = [name for name in names
                   if name.startswith("intl_generation_descriptor_")]
        self.assertEqual(len(sidecar), 1)
        self.assertRegex(descriptor["artifact_name"],
                         r"^intl_generation_[0-9a-f-]{36}_[0-9a-f]{64}\.json$")

    def test_the_current_selector_equals_its_immutable_sidecar(self):
        descriptor = self._publish()
        with open(os.path.join(self.generations, "intl_generation_current.json"),
                  "rb") as handle:
            current = handle.read()
        digest = hashlib.sha256(current).hexdigest()
        sidecar = os.path.join(self.generations,
                               "intl_generation_descriptor_%s.json" % digest)
        self.assertTrue(os.path.exists(sidecar))
        with open(sidecar, "rb") as handle:
            self.assertEqual(handle.read(), current)
        self.assertEqual(json.loads(current.decode("utf-8")), descriptor)

    def test_a_mutated_selector_fails_closed(self):
        self._publish()
        path = os.path.join(self.generations, "intl_generation_current.json")
        with open(path, "rb") as handle:
            payload = handle.read()
        mutated = payload.replace(b'"ready"', b'"unavail"')
        with open(path, "wb") as handle:
            handle.write(mutated)
        read = read_generation_publication(data_root=self.data_root)
        self.assertEqual(read["status"], "failed")
        self.assertIsNone(read["artifact_bytes"])
        self.assertEqual(read["descriptor"]["state"], "unavailable")
        self.assertEqual(read["descriptor"]["current_policies"], {})

    def test_a_lost_sidecar_fails_closed(self):
        descriptor = self._publish()
        path = os.path.join(self.generations, "intl_generation_current.json")
        with open(path, "rb") as handle:
            digest = hashlib.sha256(handle.read()).hexdigest()
        os.unlink(os.path.join(self.generations,
                               "intl_generation_descriptor_%s.json" % digest))
        read = read_generation_publication(data_root=self.data_root)
        self.assertEqual(read["status"], "failed")
        self.assertIsNone(read["artifact_bytes"])
        self.assertEqual(descriptor["state"], "ready")

    def test_a_lost_artifact_fails_closed(self):
        descriptor = self._publish()
        os.unlink(os.path.join(self.generations, descriptor["artifact_name"]))
        read = read_generation_publication(data_root=self.data_root)
        self.assertEqual(read["status"], "failed")
        self.assertIsNone(read["artifact_bytes"])
        self.assertEqual(read["descriptor"]["current_policies"], {})

    def test_a_generation_mismatch_fails_closed(self):
        self._publish()
        path = os.path.join(self.generations, "intl_generation_current.json")
        with open(path, "rb") as handle:
            descriptor = json.loads(handle.read().decode("utf-8"))
        descriptor["generation"] = OTHER_GENERATION
        payload = json.dumps(descriptor, sort_keys=True,
                             separators=(",", ":")).encode("utf-8")
        with open(path, "wb") as handle:
            handle.write(payload)
        read = read_generation_publication(data_root=self.data_root)
        self.assertEqual(read["status"], "failed")
        self.assertIsNone(read["artifact_bytes"])

    def test_a_hash_mismatch_fails_closed(self):
        self._publish()
        path = os.path.join(self.generations, "intl_generation_current.json")
        with open(path, "rb") as handle:
            descriptor = json.loads(handle.read().decode("utf-8"))
        descriptor["artifact_sha256"] = "9" * 64
        payload = json.dumps(descriptor, sort_keys=True,
                             separators=(",", ":")).encode("utf-8")
        with open(path, "wb") as handle:
            handle.write(payload)
        read = read_generation_publication(data_root=self.data_root)
        self.assertEqual(read["status"], "failed")
        self.assertIsNone(read["artifact_bytes"])

    def test_a_tampered_artifact_fails_closed(self):
        descriptor = self._publish()
        path = os.path.join(self.generations, descriptor["artifact_name"])
        with open(path, "rb") as handle:
            payload = handle.read()
        with open(path, "wb") as handle:
            handle.write(payload.replace(b'"value":1.62', b'"value":9.99'))
        read = read_generation_publication(data_root=self.data_root)
        self.assertEqual(read["status"], "failed")
        self.assertIsNone(read["artifact_bytes"])

    def test_a_symlinked_publication_path_is_refused(self):
        outside = os.path.join(self.data_root, "outside")
        os.makedirs(outside)
        os.symlink(outside, os.path.join(self.data_root, "intl"))
        with self.assertRaises(ValueError):
            self._publish()
        read = read_generation_publication(data_root=self.data_root)
        self.assertEqual(read["status"], "missing")

    def test_a_symlinked_artifact_is_refused(self):
        descriptor = self._publish()
        path = os.path.join(self.generations, descriptor["artifact_name"])
        target = os.path.join(self.data_root, "elsewhere.json")
        with open(target, "wb") as handle:
            handle.write(b"{}")
        os.unlink(path)
        os.symlink(target, path)
        read = read_generation_publication(data_root=self.data_root)
        self.assertEqual(read["status"], "failed")
        self.assertIsNone(read["artifact_bytes"])

    def test_an_immutable_collision_is_refused(self):
        contract = _build()
        payload = serialize_generation(contract)
        digest = hashlib.sha256(payload).hexdigest()
        name = "intl_generation_%s_%s.json" % (GENERATION.split(":")[1], digest)
        os.makedirs(self.generations, exist_ok=True)
        with open(os.path.join(self.generations, name), "wb") as handle:
            handle.write(b"a different artifact")
        with self.assertRaises(ValueError):
            self._publish(contract)

    def test_a_repeated_publication_of_the_same_contract_is_idempotent(self):
        contract = _build()
        first = self._publish(contract)
        second = self._publish(contract)
        self.assertEqual(first, second)
        read = read_generation_publication(data_root=self.data_root)
        self.assertEqual(read["status"], "ready")

    def test_a_failed_publication_preserves_the_old_pointer(self):
        first = self._publish()
        other = _build(evaluated_at=OTHER_EVALUATED_AT)
        payload = serialize_generation(other)
        digest = hashlib.sha256(payload).hexdigest()
        name = "intl_generation_%s_%s.json" % (GENERATION.split(":")[1], digest)
        with open(os.path.join(self.generations, name), "wb") as handle:
            handle.write(b"a different artifact")
        with self.assertRaises(ValueError):
            self._publish(other)
        read = read_generation_publication(data_root=self.data_root)
        self.assertEqual(read["status"], "ready")
        self.assertEqual(read["descriptor"], first)

    def test_an_explicit_unavailable_publication_replaces_the_pointer(self):
        self._publish()
        descriptor = publish_unavailable_generation(data_root=self.data_root)
        self.assertEqual(descriptor["state"], "unavailable")
        self.assertIsNone(descriptor["generation"])
        self.assertIsNone(descriptor["artifact_name"])
        self.assertIsNone(descriptor["artifact_sha256"])
        self.assertIsNone(descriptor["artifact_bytes"])
        self.assertEqual(descriptor["current_policies"], {})
        read = read_generation_publication(data_root=self.data_root)
        self.assertEqual(read["status"], "unavailable")
        self.assertEqual(read["descriptor"], descriptor)
        self.assertIsNone(read["artifact_bytes"])

    def test_missing_and_failed_are_distinguished(self):
        missing = read_generation_publication(data_root=self.data_root)
        self.assertEqual(missing["status"], "missing")
        self._publish()
        path = os.path.join(self.generations, "intl_generation_current.json")
        with open(path, "rb") as handle:
            descriptor = json.loads(handle.read().decode("utf-8"))
        descriptor["artifact_bytes"] = descriptor["artifact_bytes"] + 1
        with open(path, "wb") as handle:
            handle.write(json.dumps(descriptor, sort_keys=True,
                                    separators=(",", ":")).encode("utf-8"))
        failed = read_generation_publication(data_root=self.data_root)
        self.assertEqual(failed["status"], "failed")
        self.assertNotEqual(missing["status"], failed["status"])
        self.assertIsNone(failed["artifact_bytes"])

    def test_a_missing_publication_is_missing_and_never_a_fallback(self):
        read = read_generation_publication(data_root=self.data_root)
        self.assertEqual(read["status"], "missing")
        self.assertIsNone(read["artifact_bytes"])
        self.assertEqual(read["descriptor"]["state"], "unavailable")
        self.assertIsNone(read["descriptor"]["generation"])
        self.assertEqual(read["descriptor"]["current_policies"], {})

    def test_a_missing_object_is_never_answered_with_an_older_artifact(self):
        descriptor = self._publish()
        os.unlink(os.path.join(self.generations, descriptor["artifact_name"]))
        read = read_generation_publication(data_root=self.data_root)
        self.assertEqual(read["status"], "failed")
        self.assertIsNone(read["artifact_bytes"])
        self.assertIsNone(read["descriptor"]["generation"])
        self.assertEqual(read["descriptor"]["current_policies"], {})

    def test_the_publication_never_writes_outside_its_directory(self):
        self._publish()
        self.assertTrue(os.path.isdir(self.generations))
        for root, dirs, files in os.walk(self.data_root):
            for name in files:
                self.assertTrue(os.path.abspath(os.path.join(root, name))
                                .startswith(os.path.abspath(self.generations)))

    def test_the_publication_writes_no_manifest_and_leaves_no_temporary_file(self):
        self._publish()
        names = os.listdir(self.generations)
        self.assertEqual(len(names), 3)
        for name in names:
            self.assertFalse(name.startswith("."), name)
            self.assertFalse(name.endswith(".tmp"), name)


if __name__ == "__main__":
    unittest.main()


def test_all_negative_identity_keys_are_explicit_null():
    contract = build_generation_contract(config=CONFIG, binding_version=2, measures={}, evidence={},
        evaluated_at=EVALUATED_AT, policy_document_sha256={}, generation=GENERATION)
    for entry in contract["measures"].values():
        assert {key: entry[key] for key in ("content_identity", "qualification_identity", "policy_identity")} == {
            "content_identity": None, "qualification_identity": None, "policy_identity": None}
    serialize_generation(contract)
