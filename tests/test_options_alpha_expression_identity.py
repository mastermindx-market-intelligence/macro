"""Synthetic focused tests for the Options Alpha expression identity bridge.

Self-contained: no sibling-test imports, no repository fixtures, no I/O, and
no ambient clocks.  The incumbent cohort module supplies only the exact
contract semantics under test.
"""

from __future__ import annotations

import hashlib
import json
import unittest

from engine import options_alpha_expression_identity as identity
from engine import options_nbbo_cohort as cohort


def group(**overrides):
    base = {
        "ticker": "SPXW",
        "expiration": "2026-10-17",
        "right": "C",
        "strike_key": "452.5",
        "strike": 452.5,
    }
    base.update(overrides)
    return base


def call_contract():
    return identity.contract_from_group(group())


def catalog_row(**overrides):
    row = {
        "symbol": "SPXW",
        "expiration": "2026-10-17",
        "strike": 452.5,
        "right": "call",
    }
    row.update(overrides)
    return row


def catalog_bytes(*rows):
    return json.dumps(list(rows)).encode("utf-8")


class ContractFromGroupTests(unittest.TestCase):
    def test_call_roundtrip_matches_incumbent_contract(self):
        contract = identity.contract_from_group(group())
        self.assertEqual(
            contract,
            {
                "root": "SPXW",
                "expiration": "2026-10-17",
                "right": "call",
                "strike": "452.5",
                "strike_millis": 452500,
                "occ_symbol": "SPXW  261017C00452500",
            },
        )
        self.assertEqual(contract, cohort.validate_contract(contract))

    def test_put_roundtrip(self):
        contract = identity.contract_from_group(group(right="P"))
        self.assertEqual(contract["right"], "put")
        self.assertEqual(contract["occ_symbol"], "SPXW  261017P00452500")
        self.assertEqual(contract, cohort.validate_contract(contract))

    def test_whole_strike_millis_with_int_and_equal_float(self):
        via_int = identity.contract_from_group(
            group(right="P", strike_key="452", strike=452)
        )
        via_float = identity.contract_from_group(
            group(right="P", strike_key="452", strike=452.0)
        )
        self.assertEqual(via_int, via_float)
        self.assertEqual(via_int["strike"], "452")
        self.assertEqual(via_int["strike_millis"], 452000)
        self.assertEqual(via_int["occ_symbol"], "SPXW  261017P00452000")

    def test_root_preserved_verbatim_with_adjusted_looking_digit_root(self):
        contract = identity.contract_from_group(
            group(ticker="AAPL7", strike_key="15", strike=15)
        )
        self.assertEqual(contract["root"], "AAPL7")
        self.assertEqual(contract["strike_millis"], 15000)
        self.assertEqual(contract["occ_symbol"], "AAPL7 261017C00015000")

    def test_other_group_members_are_never_consulted(self):
        decorated = group()
        decorated["policy"] = "never-an-authority"
        decorated["note"] = "ignored"
        self.assertEqual(identity.contract_from_group(decorated), call_contract())

    def test_lowercase_root_fails_instead_of_case_conversion(self):
        with self.assertRaises(identity.IdentityUnavailable):
            identity.contract_from_group(group(ticker="spxw"))

    def test_submill_and_imprecise_strike_fails(self):
        for override in (
            {"strike": 0.0001},
            {"strike_key": "452.4999", "strike": 452.4999},
            {"strike": 452.50005},
            {"strike_key": "452.50005"},
        ):
            with self.subTest(override=override):
                with self.assertRaises(identity.IdentityUnavailable):
                    identity.contract_from_group(group(**override))

    def test_non_canonical_strike_key_fails(self):
        with self.assertRaises(identity.IdentityUnavailable):
            identity.contract_from_group(group(strike_key="452.50"))

    def test_float_strike_disagreement_fails(self):
        with self.assertRaises(identity.IdentityUnavailable):
            identity.contract_from_group(group(strike=452.6))

    def test_bool_nan_inf_and_type_drift_fail(self):
        for override in (
            {"strike": True},
            {"strike": False},
            {"strike": float("nan")},
            {"strike": float("inf")},
            {"strike": float("-inf")},
            {"strike": "452.5"},
            {"strike": None},
            {"strike": -452.5},
            {"strike": 0},
            {"strike": 0.0},
            {"strike": 100000},
            {"strike_key": 452.5},
            {"strike_key": None},
            {"right": "call"},
            {"right": "c"},
            {"right": "call/put"},
            {"ticker": ""},
            {"expiration": "20261017"},
            {"expiration": "2026-13-01"},
        ):
            with self.subTest(override=override):
                with self.assertRaises(identity.IdentityUnavailable):
                    identity.contract_from_group(group(**override))

    def test_missing_member_and_non_mapping_fail(self):
        incomplete = group()
        del incomplete["strike_key"]
        for bad in (incomplete, [group()], "SPXW", None):
            with self.subTest(bad=bad):
                with self.assertRaises(identity.IdentityUnavailable):
                    identity.contract_from_group(bad)


class ThetaContractIdentityEvidenceTests(unittest.TestCase):
    def test_identity_observed_terms_stay_unavailable(self):
        payload = catalog_bytes(catalog_row())
        evidence = identity.theta_contract_identity_evidence(payload, call_contract())
        self.assertEqual(
            evidence,
            {
                "identity_observed": True,
                "multiplier": None,
                "standard_deliverable": None,
                "terms_status": "unavailable",
                "terms_reason": "THETA_LIST_CONTRACTS_DOES_NOT_SUPPLY_TERMS",
                "raw_sha256": hashlib.sha256(payload).hexdigest(),
                "raw_bytes_count": len(payload),
            },
        )

    def test_observed_between_other_contracts_with_c_enum_and_occ_symbol(self):
        payload = catalog_bytes(
            catalog_row(symbol="OTHER", strike=10.0),
            catalog_row(right="C", symbol=call_contract()["occ_symbol"]),
            catalog_row(right="put", expiration="2027-01-15"),
        )
        evidence = identity.theta_contract_identity_evidence(payload, call_contract())
        self.assertIs(evidence["identity_observed"], True)

    def test_adjusted_looking_root_keeps_terms_null(self):
        contract = identity.contract_from_group(
            group(ticker="AAPL7", right="P", strike_key="15", strike=15)
        )
        payload = catalog_bytes(catalog_row(symbol="AAPL7", strike=15.0, right="Put"))
        evidence = identity.theta_contract_identity_evidence(payload, contract)
        self.assertTrue(evidence["identity_observed"])
        self.assertIsNone(evidence["multiplier"])
        self.assertIsNone(evidence["standard_deliverable"])
        self.assertEqual(evidence["terms_status"], "unavailable")
        self.assertEqual(
            evidence["terms_reason"], "THETA_LIST_CONTRACTS_DOES_NOT_SUPPLY_TERMS"
        )

    def test_missing_exact_identity_fails(self):
        for payload in (catalog_bytes(catalog_row(strike=453.0)), catalog_bytes()):
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(
                    identity.IdentityUnavailable, "does not contain"
                ):
                    identity.theta_contract_identity_evidence(
                        payload, call_contract()
                    )

    def test_duplicate_exact_identity_fails(self):
        payload = catalog_bytes(catalog_row(), catalog_row(right="C"))
        with self.assertRaisesRegex(identity.IdentityUnavailable, "duplicate"):
            identity.theta_contract_identity_evidence(payload, call_contract())

    def test_wrong_contract_rows_never_match(self):
        for row in (
            catalog_row(symbol="OTHER"),
            catalog_row(right="put"),
            catalog_row(expiration="2027-01-15"),
            catalog_row(strike=452.6),
            catalog_row(symbol="spxw"),
        ):
            with self.subTest(row=row):
                with self.assertRaisesRegex(
                    identity.IdentityUnavailable, "does not contain"
                ):
                    identity.theta_contract_identity_evidence(
                        catalog_bytes(row), call_contract()
                    )

    def test_unsupported_response_shape_fails(self):
        for payload in (
            catalog_bytes(catalog_row(multiplier=100)),
            catalog_bytes(catalog_row(standard_deliverable="shares")),
            catalog_bytes(catalog_row(symbol="OTHER", multiplier=100), catalog_row()),
            catalog_bytes(catalog_row(right="call/put")),
            b'[{"symbol":"SPXW","expiration":"2026-10-17","strike":true,"right":"call"}]',
            catalog_bytes({"symbol": "SPXW", "strike": 452.5, "right": "call"}),
            catalog_bytes("not-a-row"),
            b'{"symbol":"SPXW"}',
            b'"SPXW"',
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(identity.IdentityUnavailable):
                    identity.theta_contract_identity_evidence(
                        payload, call_contract()
                    )

    def test_strict_json_rejects_duplicates_nonfinite_and_garbage(self):
        for payload in (
            b'[{"symbol":"SPXW","symbol":"SPXW","expiration":"2026-10-17",'
            b'"strike":452.5,"right":"call"}]',
            b'[{"symbol":"SPXW","expiration":"2026-10-17","strike":NaN,"right":"call"}]',
            b'[{"symbol":"SPXW","expiration":"2026-10-17","strike":Infinity,'
            b'"right":"call"}]',
            b'[{"symbol":"SPXW","expiration":"2026-10-17","strike":1e999,'
            b'"right":"call"}]',
            b"not json",
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(identity.IdentityUnavailable):
                    identity.theta_contract_identity_evidence(
                        payload, call_contract()
                    )

    def test_non_bytes_payload_and_unvalidated_contract_fail(self):
        payload = catalog_bytes(catalog_row())
        for raw, contract in (
            (payload.decode("utf-8"), call_contract()),
            (bytearray(payload), call_contract()),
            (payload, {"root": "SPXW"}),
            (payload, dict(call_contract(), right="C")),
            (payload, dict(call_contract(), occ_symbol="SPXW  261017C00452600")),
        ):
            with self.subTest(contract=contract):
                with self.assertRaises(identity.IdentityUnavailable):
                    identity.theta_contract_identity_evidence(raw, contract)

    def test_exact_raw_hash_and_count_across_whitespace_variants(self):
        compact = catalog_bytes(catalog_row())
        spaced = b"  " + json.dumps([catalog_row()], indent=2).encode("utf-8") + b"\n"
        self.assertNotEqual(compact, spaced)
        for payload in (compact, spaced):
            with self.subTest(payload=payload):
                evidence = identity.theta_contract_identity_evidence(
                    payload, call_contract()
                )
                self.assertEqual(
                    evidence["raw_sha256"], hashlib.sha256(payload).hexdigest()
                )
                self.assertEqual(evidence["raw_bytes_count"], len(payload))
        self.assertNotEqual(
            identity.theta_contract_identity_evidence(
                compact, call_contract()
            )["raw_sha256"],
            identity.theta_contract_identity_evidence(
                spaced, call_contract()
            )["raw_sha256"],
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
