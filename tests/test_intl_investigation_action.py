"""Tests for the pure International Investigate ingress URL projection.

The coverage is discriminating rather than decorative:

* the action carries exactly the five reference fields, and the href is the
  relative investigations route with the fields in the documented order;
* the selected field ids are repeated in the order the caller gave them, and
  the fallback return URL survives byte for byte;
* the reference fields - and therefore the fingerprint - do not depend on the
  return URL, so the parent controller may replace the return on activation;
* a withheld, denied, unknown, missing, unbound, wrong-context, duplicated,
  unknown-field, malformed-URL or oversized input yields no action at all;
* a descriptor that merely shares the generation uuid is never enough: the
  artifact digest, the artifact size and the current policies must bind the
  canonical serialization of the contract;
* a tampered content identity or a policy that is not allowed is refused even
  though the contract itself still validates;
* the projection performs no I/O and never mutates its inputs.

Every fixture here is a scratch fixture: a synthetic contract built from the
public builder and published into a temporary directory.  These tests prove
the projection; they do not claim that the real Macro builder has emitted a
real generation.
"""

import builtins
import copy
import hashlib
import os
import socket
import sys
import tempfile
import unittest
from urllib.parse import unquote

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))

from lib.intl_generation_publication import (  # noqa: E402
    build_generation_contract,
    publish_generation,
    serialize_generation,
)
from lib.intl_investigation_action import (  # noqa: E402
    MAX_ACTION_URL_BYTES,
    build_intl_investigation_action,
)

GENERATION = "im-workspace-generation:4979a6c3-b834-4c69-8f1b-c8961cc5e11a"
OTHER_GENERATION = "im-workspace-generation:0f9c2b41-6f6e-4f0a-9a2b-1c3d4e5f6071"
EVALUATED_AT = "2026-10-01T00:00:00+00:00"

RECEIPT_SHA = "1" * 64
OTHER_RECEIPT_SHA = "2" * 64
ARTIFACT_SHA = "a" * 64
PROVENANCE_SHA = "b" * 64
POLICY_SHA = "c" * 64
OTHER_POLICY_SHA = "d" * 64

SOURCE_URL = "https://example.invalid/source"
OBSERVED_AT = "2026-10-01"

ECB = "EZ.policy_rate"
EZ_GDP = "EZ.gdp_yoy"
JP_GDP = "JP.gdp_yoy"
JP_CPI = "JP.cpi_yoy"
JP_YIELD = "JP.yield_10y"
GB_GDP = "GB.gdp_yoy"
GB_YIELD = "GB.yield_10y"

CONFIG = {
    "markets": ["EZ", "JP", "GB"],
    "horizons": ["1m", "3m"],
    "bases": ["local", "usd_unhedged"],
    "fields": {
        "EZ": ["policy_rate", "gdp_yoy", "cpi_yoy"],
        "JP": ["gdp_yoy", "cpi_yoy", "yield_10y"],
        "GB": ["gdp_yoy", "yield_10y"],
    },
}

CANONICAL_RETURN = (
    "https://www.mastermind-x.com/intl.html?view=macro&market=EZ&pins="
    "&horizon=1m&basis=local&return_basis=price&group=")
HASHED_RETURN = CANONICAL_RETURN + "#im-catalogue-library"
STOCKS_RETURN = (
    "https://www.mastermind-x.com/intl_stocks.html?view=library&market=GB"
    "&pins=&horizon=3m&basis=usd_unhedged&return_basis=price&group=")

#: Nothing that identifies a person, a private record or a session may appear
#: in an action.
FORBIDDEN_SUBSTRINGS = (
    "question", "account", "record", "token", "owner", "saved", "principal",
    "mmx_shell", "mmx_generation")

#: The "argument was not supplied" marker of the fixture helper.
_DEFAULT = object()


# ---------------------------------------------------------------------------
# Synthetic fixtures
# ---------------------------------------------------------------------------

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


def _ecb_receipt():
    return {"artifact_sha256": ARTIFACT_SHA, "provenance_sha256": PROVENANCE_SHA}


def _receipt(sha=RECEIPT_SHA):
    return {"receipt_sha256": sha}


def _ecb_decision(generation=GENERATION):
    return {
        "owner_ref": "scripts/build_intl.py",
        "policy_ref": "policy/ez-core-v1",
        "decision_ref": "%s:%s" % (generation, ECB),
        "metadata": "allowed",
        "value_permission": "allowed",
        "binding": {"market_id": "EZ", "field": "policy_rate",
                    "instrument_id": "deposit_facility",
                    "source_id": "D.U2.EUR.4F.KR.DFR.LEV",
                    "artifact_sha256": ARTIFACT_SHA,
                    "provenance_sha256": PROVENANCE_SHA,
                    "observation_at": OBSERVED_AT, "value": 2.5,
                    "unit": "percent"},
    }


def _decision(sid, generation=GENERATION, receipt_sha=RECEIPT_SHA,
              policy_ref="policy/core-v3"):
    return {
        "owner_ref": "scripts/build_intl.py",
        "policy_ref": policy_ref,
        "decision_ref": "%s:%s" % (generation, sid),
        "metadata": "allowed",
        "value_permission": "allowed",
        "binding": {"field": sid, "receipt_sha256": receipt_sha},
    }


def _evidence(sid, receipt=None, decision=None, clocks=None):
    """One closed evidence entry: the receipt, the decision and the clocks."""
    if clocks is None:
        clocks = {"observation_at": OBSERVED_AT}
    return {"receipt_identity": receipt, "publication_decision": decision,
            "clocks": clocks}


def _qualified_inputs():
    """Three admitted fields, one per market, plus the withheld siblings."""
    measures = {
        ECB: _measure(ECB, value=2.5,
                      instrument={"kind": "official_policy",
                                  "id": "deposit_facility",
                                  "market_id": "EZ"}),
        EZ_GDP: _measure(EZ_GDP, value=0.8),
        GB_YIELD: _measure(GB_YIELD, value=3.9,
                           instrument={"kind": "sovereign_10y",
                                       "id": "GBGB10YR",
                                       "market_id": "GB"}),
        # A stale field: the decision is valid, the quality is not.
        JP_CPI: _measure(JP_CPI, quality="stale", reason="source_stale",
                         value=2.9),
        # A denied field.
        JP_GDP: _measure(JP_GDP, quality="denied", reason="metadata_denied",
                         metadata="denied", permission="denied", value=None,
                         unit=None, source_reference=None, evidence_key=None),
        # An unknown field.
        GB_GDP: _measure(GB_GDP, quality="unknown", reason="source_unknown",
                         metadata="unknown", permission="unknown", value=None,
                         unit=None, source_reference=None, evidence_key=None),
    }
    evidence = {
        ECB: _evidence(ECB, _ecb_receipt(), _ecb_decision()),
        EZ_GDP: _evidence(EZ_GDP, _receipt(), _decision(EZ_GDP)),
        GB_YIELD: _evidence(GB_YIELD, _receipt(OTHER_RECEIPT_SHA),
                            _decision(GB_YIELD,
                                      receipt_sha=OTHER_RECEIPT_SHA)),
        JP_CPI: _evidence(JP_CPI, _receipt(), _decision(JP_CPI)),
        JP_GDP: _evidence(JP_GDP, _receipt(), _decision(JP_GDP)),
        GB_GDP: _evidence(GB_GDP, _receipt(), _decision(GB_GDP)),
    }
    documents = {ECB: POLICY_SHA, EZ_GDP: POLICY_SHA, GB_YIELD: OTHER_POLICY_SHA}
    return measures, evidence, documents


def _build(config=None, measures=None, evidence=None, documents=None,
           generation=GENERATION, evaluated_at=EVALUATED_AT):
    """Build one synthetic generation contract."""
    if measures is None and evidence is None and documents is None:
        measures, evidence, documents = _qualified_inputs()
    return build_generation_contract(
        config=copy.deepcopy(config if config is not None else CONFIG),
        binding_version=2,
        measures=measures if measures is not None else {},
        evidence=evidence if evidence is not None else {},
        evaluated_at=evaluated_at,
        policy_document_sha256=documents if documents is not None else {},
        generation=generation)


def _context_id(contract, market, horizon="1m", basis="local"):
    """The context identifier of one binding dimension of the contract."""
    for context in contract["contexts"]:
        if (context["market"] == market and context["horizon"] == horizon
                and context["currency_basis"] == basis):
            return context["id"]
    raise AssertionError("the contract has no such context")


def _query(href):
    """The decoded query pairs of one action URL."""
    raw = href.split("?", 1)[1]
    pairs = []
    for pair in raw.split("&"):
        key, _, value = pair.partition("=")
        pairs.append((unquote(key), unquote(value)))
    return pairs


class ActionFixture(unittest.TestCase):
    """A published synthetic generation and the helper that reads it."""

    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.contract = _build()
        self.descriptor = publish_generation(data_root=self._temp.name,
                                             contract=self.contract)

    def _action(self, *, context_id=_DEFAULT, selected=_DEFAULT,
                return_url=_DEFAULT, contract=_DEFAULT, descriptor=_DEFAULT):
        if context_id is _DEFAULT:
            context_id = _context_id(self.contract, "EZ")
        if selected is _DEFAULT:
            selected = [ECB]
        if return_url is _DEFAULT:
            return_url = CANONICAL_RETURN
        if contract is _DEFAULT:
            contract = self.contract
        if descriptor is _DEFAULT:
            descriptor = self.descriptor
        return build_intl_investigation_action(
            contract=contract,
            descriptor=descriptor,
            context_id=context_id,
            selected_measure_ids=selected,
            return_url=return_url)


class ActionShapeTests(ActionFixture):
    def test_the_action_carries_exactly_the_five_reference_fields(self):
        action = self._action()
        self.assertIsNotNone(action)
        self.assertEqual(set(action),
                         {"href", "context_id", "generation", "fingerprint",
                          "field_ids"})
        self.assertEqual(action["context_id"], _context_id(self.contract, "EZ"))
        self.assertEqual(action["generation"], GENERATION)
        self.assertEqual(action["field_ids"], [ECB])
        self.assertEqual(len(action["fingerprint"]), 64)
        self.assertTrue(all(char in "0123456789abcdef"
                            for char in action["fingerprint"]))

    def test_the_href_is_the_relative_investigations_route(self):
        action = self._action()
        href = action["href"]
        self.assertTrue(href.startswith("/analysis?"))
        self.assertNotIn("://", href)
        pairs = _query(href)
        self.assertEqual(pairs[0], ("view", "investigations"))
        self.assertEqual(pairs[1],
                         ("intl_context", _context_id(self.contract, "EZ")))
        self.assertEqual(pairs[2], ("intl_generation", GENERATION))
        self.assertEqual(pairs[3], ("intl_fingerprint", action["fingerprint"]))
        self.assertEqual(pairs[4], ("intl_field", ECB))
        self.assertEqual(pairs[5], ("intl_return", CANONICAL_RETURN))

    def test_the_field_ids_are_repeated_in_the_given_order(self):
        action = self._action(selected=[EZ_GDP, ECB])
        pairs = _query(action["href"])
        fields = [value for key, value in pairs if key == "intl_field"]
        self.assertEqual(fields, [EZ_GDP, ECB])
        self.assertEqual(action["field_ids"], [EZ_GDP, ECB])
        # The return stays last, after every field.
        self.assertEqual(pairs[-1][0], "intl_return")
        self.assertEqual([key for key, _ in pairs],
                         ["view", "intl_context", "intl_generation",
                          "intl_fingerprint", "intl_field", "intl_field",
                          "intl_return"])

    def test_the_return_url_survives_byte_for_byte(self):
        for return_url in (CANONICAL_RETURN, CANONICAL_RETURN.replace("view=macro","view=risk")):
            with self.subTest(return_url=return_url):
                action = self._action(return_url=return_url)
                self.assertIsNotNone(action)
                pairs = _query(action["href"])
                self.assertEqual(pairs[-1], ("intl_return", return_url))

    def test_a_canonical_return_with_a_hash_is_refused(self):
        self.assertIsNone(self._action(return_url=HASHED_RETURN))

    def test_the_stocks_page_is_not_a_native_return(self):
        self.assertIsNone(self._action(context_id=_context_id(self.contract, "GB"),
                                      selected=[GB_YIELD], return_url=STOCKS_RETURN))

    def test_a_second_market_field_is_admitted(self):
        action = self._action(context_id=_context_id(self.contract, "GB"),
                              selected=[GB_YIELD])
        self.assertIsNotNone(action)
        self.assertEqual(action["field_ids"], [GB_YIELD])

    def test_the_fingerprint_does_not_depend_on_the_return_url(self):
        first = self._action(return_url=CANONICAL_RETURN)
        second = self._action(return_url=CANONICAL_RETURN.replace("view=macro", "view=risk"))
        self.assertEqual(first["fingerprint"], second["fingerprint"])
        self.assertEqual(first["context_id"], second["context_id"])
        self.assertEqual(first["generation"], second["generation"])
        self.assertEqual(first["field_ids"], second["field_ids"])
        # Only the return may differ: the parent replaces it on activation.
        self.assertNotEqual(first["href"], second["href"])

    def test_same_generation_fingerprint_keeps_separate_selection_and_context(self):
        first = self._action(selected=[ECB])
        second = self._action(selected=[ECB, EZ_GDP])
        third = self._action(context_id=_context_id(self.contract, "EZ",
                                                     horizon="3m"),
                             selected=[ECB], return_url=CANONICAL_RETURN.replace("horizon=1m", "horizon=3m"))
        self.assertEqual(first["fingerprint"], second["fingerprint"])
        self.assertNotEqual(first["field_ids"], second["field_ids"])
        self.assertEqual(first["fingerprint"], third["fingerprint"])
        self.assertNotEqual(first["context_id"], third["context_id"])

    def test_the_action_url_stays_within_the_native_bound(self):
        action = self._action()
        self.assertLessEqual(len(action["href"].encode("utf-8")),
                             MAX_ACTION_URL_BYTES)

    def test_the_action_carries_no_private_or_session_reference(self):
        action = self._action()
        for value in (action["href"], action["context_id"], action["generation"],
                      action["fingerprint"], " ".join(action["field_ids"])):
            for forbidden in FORBIDDEN_SUBSTRINGS:
                self.assertNotIn(forbidden, value)


class RefusalTests(ActionFixture):
    def test_a_withheld_field_yields_no_action(self):
        for sid, quality in ((JP_CPI, "stale"), (JP_GDP, "denied"),
                             (GB_GDP, "unknown")):
            with self.subTest(sid=sid):
                action = self._action(context_id=_context_id(self.contract, "JP"
                                                             if sid.startswith("JP")
                                                             else "GB"),
                                      selected=[sid])
                self.assertIsNone(action)

    def test_a_missing_field_yields_no_action(self):
        action = self._action(context_id=_context_id(self.contract, "JP"),
                              selected=[JP_YIELD])
        self.assertIsNone(action)

    def test_no_descriptor_yields_no_action(self):
        self.assertIsNone(self._action(descriptor=None))

    def test_an_unavailable_descriptor_yields_no_action(self):
        descriptor = copy.deepcopy(self.descriptor)
        descriptor["state"] = "unavailable"
        self.assertIsNone(self._action(descriptor=descriptor))

    def test_a_descriptor_that_binds_another_digest_yields_no_action(self):
        descriptor = copy.deepcopy(self.descriptor)
        descriptor["artifact_sha256"] = "9" * 64
        self.assertIsNone(self._action(descriptor=descriptor))

    def test_a_descriptor_with_another_size_yields_no_action(self):
        descriptor = copy.deepcopy(self.descriptor)
        descriptor["artifact_bytes"] = descriptor["artifact_bytes"] + 1
        self.assertIsNone(self._action(descriptor=descriptor))

    def test_a_descriptor_with_another_generation_yields_no_action(self):
        descriptor = copy.deepcopy(self.descriptor)
        descriptor["generation"] = OTHER_GENERATION
        self.assertIsNone(self._action(descriptor=descriptor))

    def test_a_descriptor_with_another_policy_yields_no_action(self):
        descriptor = copy.deepcopy(self.descriptor)
        descriptor["current_policies"][ECB]["policy_ref"] = "policy/other-v9"
        self.assertIsNone(self._action(descriptor=descriptor))

    def test_a_descriptor_of_another_contract_yields_no_action(self):
        other = _build(evaluated_at="2026-10-02T00:00:00+00:00")
        descriptor = publish_generation(data_root=self._temp.name, contract=other)
        # The generation uuid is shared, the content is not.
        self.assertEqual(descriptor["generation"], GENERATION)
        self.assertIsNone(self._action(descriptor=descriptor))

    def test_a_malformed_contract_yields_no_action(self):
        contract = copy.deepcopy(self.contract)
        contract["asof"] = "2026-10-01"
        self.assertIsNone(self._action(contract=contract))

    def test_a_duplicated_context_yields_no_action(self):
        contract = copy.deepcopy(self.contract)
        contract["contexts"].append(copy.deepcopy(contract["contexts"][0]))
        self.assertIsNone(self._action(contract=contract))

    def test_an_unknown_context_yields_no_action(self):
        action = self._action(context_id="intl-workspace-context:sha256:" + "0" * 64)
        self.assertIsNone(action)

    def test_a_malformed_context_id_yields_no_action(self):
        for context_id in ("", "nope", "intl workspace context", 17, None):
            with self.subTest(context_id=context_id):
                self.assertIsNone(self._action(context_id=context_id))

    def test_an_unknown_field_yields_no_action(self):
        action = self._action(selected=["EZ.not_a_field"])
        self.assertIsNone(action)

    def test_a_field_outside_the_context_yields_no_action(self):
        action = self._action(context_id=_context_id(self.contract, "EZ"),
                              selected=[GB_YIELD])
        self.assertIsNone(action)

    def test_a_duplicated_field_yields_no_action(self):
        self.assertIsNone(self._action(selected=[ECB, ECB]))

    def test_an_empty_selection_yields_no_action(self):
        self.assertIsNone(self._action(selected=[]))

    def test_a_selection_that_is_not_a_list_yields_no_action(self):
        for selected in (ECB, None, {ECB}, (ECB,)):
            with self.subTest(selected=selected):
                self.assertIsNone(self._action(selected=selected))

    def test_a_malformed_field_id_yields_no_action(self):
        for sid in ("ez.policy_rate", "EZ.Policy_rate", "EZ.policy rate",
                    "EZ.policy-rate", "E.policy_rate", "EZ.", "EZ.a" * 40):
            with self.subTest(sid=sid):
                self.assertIsNone(self._action(selected=[sid]))

    def test_a_selection_above_the_bound_yields_no_action(self):
        fields = ["gdp_yoy", "cpi_yoy", "policy_rate", "policy_proxy",
                  "yield_10y", "yield_change"]
        names = list(fields)
        index = 0
        while len(names) < 129:
            names.append("%s_%03d" % (fields[index % len(fields)], index))
            index += 1
        config = {"markets": ["EZ"], "horizons": ["1m"], "bases": ["local"],
                  "fields": {"EZ": names}}
        contract = _build(config=config, measures={}, evidence={}, documents={})
        descriptor = publish_generation(data_root=self._temp.name,
                                        contract=contract)
        context_id = _context_id(contract, "EZ")
        members = contract["contexts"][0]["measure_ids"]
        self.assertEqual(len(members), 129)
        # The selection is bound before the admission, and 129 is above the
        # bound of 128 even though every id is a real member of the context.
        self.assertIsNone(build_intl_investigation_action(
            contract=contract, descriptor=descriptor, context_id=context_id,
            selected_measure_ids=members, return_url=CANONICAL_RETURN))

    def test_a_tampered_content_identity_yields_no_action(self):
        contract = copy.deepcopy(self.contract)
        contract["measures"][ECB]["content_identity"] = "7" * 64
        descriptor = publish_generation(data_root=self._temp.name, contract=contract)
        self.assertIsNone(self._action(contract=contract, descriptor=descriptor))

    def test_a_tampered_qualification_identity_yields_no_action(self):
        contract = copy.deepcopy(self.contract)
        contract["measures"][ECB]["qualification_identity"] = "7" * 64
        descriptor = publish_generation(data_root=self._temp.name, contract=contract)
        self.assertIsNone(self._action(contract=contract, descriptor=descriptor))

    def test_a_policy_that_is_not_allowed_yields_no_action(self):
        contract = copy.deepcopy(self.contract)
        contract["policies"][ECB]["metadata"] = "denied"
        descriptor = publish_generation(data_root=self._temp.name, contract=contract)
        self.assertIsNone(self._action(contract=contract, descriptor=descriptor))

    def test_a_policy_identity_that_does_not_match_yields_no_action(self):
        contract = copy.deepcopy(self.contract)
        contract["policies"][ECB]["policy_identity"] = "7" * 64
        self.assertIsNone(self._action(contract=contract))

    def test_a_malformed_return_url_yields_no_action(self):
        for return_url in (
                "",
                "not a url",
                "/intl.html",
                "http://www.mastermind-x.com/intl.html",
                "https://mastermind-x.com/intl.html",
                "https://www.mastermind-x.com/",
                "https://www.mastermind-x.com/intl_stock.html",
                "https://www.mastermind-x.com/intl.html\\",
                "https://user:secret@www.mastermind-x.com/intl.html",
                "https://www.mastermind-x.com:8443/intl.html",
                "https://www.mastermind-x.com/intl.html?view=macro\n",
                "https://www.mastermind-x.com/intl.html#im-catalogue\tlibrary",
                "https://www.mastermind-x.com/intl.html?" + "x" * 4096,
                17, None):
            with self.subTest(return_url=return_url):
                self.assertIsNone(self._action(return_url=return_url))

    def test_an_unknown_application_parameter_yields_no_action(self):
        for parameter in ("question", "account", "record", "token", "auth",
                          "saved", "owner", "mmx_shell", "mmx_generation",
                          "unknown"):
            with self.subTest(parameter=parameter):
                return_url = ("https://www.mastermind-x.com/intl.html?view=macro"
                              "&%s=1" % parameter)
                self.assertIsNone(self._action(return_url=return_url))

    def test_a_duplicated_application_parameter_yields_no_action(self):
        return_url = ("https://www.mastermind-x.com/intl.html?view=macro"
                      "&view=risk&horizon=1m")
        self.assertIsNone(self._action(return_url=return_url))

    def test_an_unsupported_return_basis_yields_no_action(self):
        return_url = ("https://www.mastermind-x.com/intl.html?view=macro"
                      "&return_basis=total_return")
        self.assertIsNone(self._action(return_url=return_url))

    def test_an_oversized_return_url_yields_no_action(self):
        return_url = ("https://www.mastermind-x.com/intl.html?view=macro&group="
                      + "a" * 4096)
        self.assertIsNone(self._action(return_url=return_url))

    def test_an_oversized_action_url_yields_no_action(self):
        # A query and a fragment at their own bounds: the percent-encoded
        # return alone exceeds the native action URL bound.
        return_url = ("https://www.mastermind-x.com/intl.html?view=a"
                      + ":" * 2000 + "#b" + ":" * 1023)
        self.assertLessEqual(len(return_url.encode("utf-8")), 4096)
        self.assertIsNone(self._action(return_url=return_url))


class HygieneTests(ActionFixture):
    def test_the_projection_performs_no_io_and_no_network(self):
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
            action = self._action()
        finally:
            builtins.open = real_open
            socket.socket = real_socket
        self.assertIsNotNone(action)
        self.assertEqual(opened, [])

    def test_the_projection_does_not_mutate_its_inputs(self):
        contract = copy.deepcopy(self.contract)
        descriptor = copy.deepcopy(self.descriptor)
        selected = [ECB, EZ_GDP]
        action = self._action(contract=contract, descriptor=descriptor,
                              selected=selected)
        self.assertIsNotNone(action)
        self.assertEqual(contract, self.contract)
        self.assertEqual(descriptor, self.descriptor)
        self.assertEqual(selected, [ECB, EZ_GDP])

    def test_the_published_bytes_are_the_ones_the_action_binds(self):
        payload = serialize_generation(self.contract)
        self.assertEqual(self.descriptor["artifact_bytes"], len(payload))
        self.assertEqual(self.descriptor["artifact_sha256"],
                         hashlib.sha256(payload).hexdigest())
        self.assertEqual(self.descriptor["current_policies"],
                         self.contract["policies"])


if __name__ == "__main__":
    unittest.main()


def test_native_fingerprint_is_exact_generation_artifact_sha256(tmp_path):
    contract=_build()
    descriptor=publish_generation(data_root=tmp_path,contract=contract)
    action=build_intl_investigation_action(contract=contract,descriptor=descriptor,
        context_id=_context_id(contract,'EZ'),selected_measure_ids=[ECB],return_url=CANONICAL_RETURN)
    assert action['fingerprint']==descriptor['artifact_sha256']


def test_native_canonical_return_rejects_fragment_and_nonempty_group(tmp_path):
    contract=_build();descriptor=publish_generation(data_root=tmp_path,contract=contract)
    for ret in [CANONICAL_RETURN+'#intl-legacy-research',CANONICAL_RETURN+'rates',CANONICAL_RETURN.replace('pins=&','pins=JP%2CGB&')]:
        assert build_intl_investigation_action(contract=contract,descriptor=descriptor,
            context_id=_context_id(contract,'EZ'),selected_measure_ids=[ECB],return_url=ret)is None
