"""Tests for the IntlInvestigation owner bridge.

These tests exercise the pure-Python bridge with trusted caller inputs
(synthetic). They are NOT exercising a real upstream producer; every
origins record is explicitly labelled as a synthetic trusted origin.

Coverage targets:
* Positive path: synthetic ECB-style DFR fixture at 2.50 percent,
  observed_at 2026-10-06 with the official instrument and source.
* Negative paths: malformed/extra context, missing generation,
  one-missing-selected-among-two, partial membership, denied-scrubs,
  whole-unavailable-never-denied, invalid bool/string/nonfinite/hugeint,
  origin/correction/exclusion, context-market-mismatch, etc.
* Stable-identity invariants: identical content with quality or generation
  churn keeps a stable content identity; a value or date change revises it.
* Clocks envelope is null when absent and never appears inside the result.
* Detached: input containers are not mutated.
* Zero/negative values are accepted finite numerics.
* No I/O: ``builtins.open`` and ``socket.socket`` traps stay untouched.
"""

import builtins
import copy
import hashlib
import json
import math
import os
import socket
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))


from lib.intl_investigation_owner import (  # noqa: E402
    build_intl_owner_result,
    MACRO_FIELDS,
)


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

MARKET = "ECB"
PREFIX = "ECB."
MEASURE_ID = "ECB.policy.dfr"


def _valid_context(**overrides):
    ctx = {
        "researchMarket": MARKET,
        "toolBindingVersion": "2026.10.11",
        "periodIdentity": "2026-Q4",
        "currencyBasis": "EUR",
        "returnBasis": "spot",
        "owner": "intl-investigation",
        "query": "policy_rates",
        "cohort": "euro_area",
        "temporalPolicy": "fixed",
        "selectedMeasureIds": [MEASURE_ID],
    }
    ctx.update(overrides)
    return ctx


def _valid_origin(**overrides):
    o = {
        "content_identity": None,
        "qualification_identity": None,
        "excluded": False,
        "correction": False,
    }
    o.update(overrides)
    return o


def _valid_measure(**overrides):
    m = {
        "quality": "qualified",
        "reason": None,
        "metadata": "allowed",
        "value_permission": "allowed",
        "value": 2.50,
        "unit": "percent",
        "instrument": {
            "kind": "ecb_policy_rate",
            "id": "DFR",
            "market_id": MARKET,
        },
        "period": "2026-10-06",
        "observation_at": "2026-10-06",
        "calculation_at": "2026-10-06T15:15:00+01:00",
        "source_reference": (
            "https://www.ecb.europa.eu/stats/policy_and_exchange_rates/"
            "key_ecb_interest_rates/html/index.en.html"
        ),
        "evidence_key": "ECB.MB.2026.10.06",
    }
    m.update(overrides)
    return m


def _build(measures, **kwargs):
    kwargs.setdefault("context", _valid_context())
    kwargs.setdefault("generation", "synthetic-test-publisher:gen-001")
    kwargs.setdefault("measures", measures)
    if "origins" not in kwargs and MEASURE_ID in (measures or {}):
        kwargs.setdefault(
            "origins",
            {
                MEASURE_ID: _valid_origin(
                    qualification_identity="synthetic-trusted:qual/v1"
                )
            },
        )
    return build_intl_owner_result(**kwargs)


# ---------------------------------------------------------------------------
# Positive: the synthetic ECB DFR fixture
# ---------------------------------------------------------------------------

class TestECBFixture(unittest.TestCase):

    def test_ecb_dfr_2_50_percent_2026_10_06(self):
        """Synthetic ECB-shaped DFR at 2.50 percent observed 2026-10-06."""
        m = _valid_measure()
        origin = _valid_origin(
            qualification_identity="synthetic-trusted:qual/v1",
        )

        out = _build(
            {MEASURE_ID: m},
            origins={MEASURE_ID: origin},
            clocks={
                "published_at": "2026-10-06T15:15:00+01:00",
                "source_observed_at": "2026-10-06",
                "rights_at": "2026-10-06T15:30:00+01:00",
            },
        )

        # Result must be present.
        self.assertIsNotNone(out["result"])
        r = out["result"]

        # The nine context strings and selectedMeasureIds are preserved.
        self.assertEqual(r["researchMarket"], "ECB")
        self.assertEqual(r["toolBindingVersion"], "2026.10.11")
        self.assertEqual(r["periodIdentity"], "2026-Q4")
        self.assertEqual(r["currencyBasis"], "EUR")
        self.assertEqual(r["returnBasis"], "spot")
        self.assertEqual(r["owner"], "intl-investigation")
        self.assertEqual(r["query"], "policy_rates")
        self.assertEqual(r["cohort"], "euro_area")
        self.assertEqual(r["temporalPolicy"], "fixed")
        self.assertNotIn("selectedMeasureIds", r)

        # generation/read/membership preserved.
        self.assertEqual(r["generation"], "synthetic-test-publisher:gen-001")
        self.assertEqual(r["read"], "ok")
        self.assertEqual(r["membership"], "unknown")
        self.assertEqual(r["tombstones"], [])

        # Observation: available + qualified + non-excluded + corrected=false.
        obs = r["observations"][0]
        self.assertEqual(obs["id"], MEASURE_ID)
        self.assertEqual(obs["availability"], "available")
        self.assertTrue(obs["qualified"])
        self.assertFalse(obs["excluded"])
        self.assertFalse(obs["correction"])

        # Identities: explicit qualification, computed content identity.
        self.assertIsNotNone(obs["contentIdentity"])
        self.assertEqual(
            obs["qualificationIdentity"],
            "synthetic-trusted:qual/v1",
        )
        self.assertEqual(len(obs["contentIdentity"]), 64)

        # Interpretation: exactly four fields, no percent conversion.
        interp = obs["interpretation"]
        self.assertIsNotNone(interp)
        self.assertEqual(set(interp.keys()), {"value", "unit", "basis", "cohort"})
        self.assertEqual(interp["value"], 2.50)
        self.assertEqual(interp["unit"], "percent")
        self.assertEqual(interp["basis"], "EUR")
        self.assertEqual(interp["cohort"], "euro_area")
        self.assertNotIn("percent_unit", interp)
        self.assertNotIn("ratio", interp)

        # Clocks are in the envelope, NOT in the result.
        self.assertEqual(out["clocks"], {
            "published_at": "2026-10-06T15:15:00+01:00",
            "source_observed_at": "2026-10-06",
            "rights_at": "2026-10-06T15:30:00+01:00",
        })
        self.assertNotIn("clocks", r)
        self.assertNotIn("published_at", r)
        self.assertNotIn("source_observed_at", r)
        self.assertNotIn("rights_at", r)

        # No diagnostics on the happy path.
        self.assertEqual(out["diagnostics"], [])


# ---------------------------------------------------------------------------
# Generation / context validation
# ---------------------------------------------------------------------------

class TestMissingGeneration(unittest.TestCase):

    def test_missing_generation_returns_null(self):
        out = build_intl_owner_result(
            context=_valid_context(),
            generation="",  # missing -> empty string rejected
            measures={},
        )
        self.assertIsNone(out["result"])
        codes = [d["code"] for d in out["diagnostics"]]
        self.assertIn("missing_owner_input", codes)

    def test_missing_context_returns_null(self):
        out = build_intl_owner_result(
            context=None,  # type: ignore[arg-type]
            generation="g",
            measures={},
        )
        self.assertIsNone(out["result"])
        codes = [d["code"] for d in out["diagnostics"]]
        self.assertIn("invalid_context", codes)


class TestInvalidEnum(unittest.TestCase):

    def test_invalid_read_returns_null(self):
        out = build_intl_owner_result(
            context=_valid_context(),
            generation="g",
            measures={},
            read="maybe",
        )
        self.assertIsNone(out["result"])
        codes = [d["code"] for d in out["diagnostics"]]
        self.assertIn("invalid_owner_input", codes)

    def test_invalid_membership_returns_null(self):
        out = build_intl_owner_result(
            context=_valid_context(),
            generation="g",
            measures={},
            membership="all",
        )
        self.assertIsNone(out["result"])
        codes = [d["code"] for d in out["diagnostics"]]
        self.assertIn("invalid_owner_input", codes)


# ---------------------------------------------------------------------------
# Missing measurement selected among two
# ---------------------------------------------------------------------------

class TestMissingSelectedAmongTwo(unittest.TestCase):

    def test_one_of_two_selected_is_missing(self):
        ctx = _valid_context(selectedMeasureIds=[
            "ECB.policy.dfr",
            "ECB.policy.mro",
        ])
        m_dfr = _valid_measure()
        m_dfr["instrument"] = {
            "kind": "ecb_policy_rate", "id": "DFR", "market_id": MARKET,
        }
        # Only the DFR measure is supplied; MRO is absent.
        out = build_intl_owner_result(
            context=copy.deepcopy(ctx),
            generation="g",
            measures={"ECB.policy.dfr": m_dfr},
        )
        self.assertIsNotNone(out["result"])
        obs = out["result"]["observations"]
        self.assertEqual(len(obs), 2)
        self.assertEqual(obs[0]["id"], "ECB.policy.dfr")
        self.assertEqual(obs[0]["availability"], "available")
        self.assertEqual(obs[1]["id"], "ECB.policy.mro")
        self.assertEqual(obs[1]["availability"], "unavailable")
        self.assertFalse(obs[1]["qualified"])
        codes = [d["code"] for d in out["diagnostics"]]
        self.assertIn("missing_owner_input", codes)


# ---------------------------------------------------------------------------
# Partial membership
# ---------------------------------------------------------------------------

class TestPartialMembership(unittest.TestCase):

    def test_page_membership_does_not_claim_complete(self):
        out = _build({MEASURE_ID: _valid_measure()}, membership="page")
        self.assertEqual(out["result"]["membership"], "page")

    def test_top_k_membership_does_not_claim_complete(self):
        out = _build({MEASURE_ID: _valid_measure()}, membership="top_k")
        self.assertEqual(out["result"]["membership"], "top_k")

    def test_unknown_membership_does_not_claim_complete(self):
        out = _build({MEASURE_ID: _valid_measure()}, membership="unknown")
        self.assertEqual(out["result"]["membership"], "unknown")

    def test_partial_membership_preserves_supplied(self):
        # A page membership with a missing measure does NOT invent a tombstone.
        out = _build({}, membership="page")
        self.assertEqual(out["result"]["tombstones"], [])
        self.assertEqual(out["result"]["membership"], "page")


# ---------------------------------------------------------------------------
# Denied scrubbing
# ---------------------------------------------------------------------------

class TestDeniedScrubs(unittest.TestCase):

    def test_denied_metadata_does_not_serialize_value_or_source(self):
        secret = "RECURSIVE_TOP_SECRET_PROJECT_PHOENIX_2026"
        m = _valid_measure(
            value=999.99,
            source_reference=secret,
            evidence_key=secret,
            metadata="denied",
        )
        out = build_intl_owner_result(
            context=_valid_context(),
            generation="g",
            measures={MEASURE_ID: m},
            read="ok",
        )
        self.assertIsNotNone(out["result"])
        payload = json.dumps(out, sort_keys=True, default=str)
        self.assertNotIn(secret, payload)

        obs = out["result"]["observations"][0]
        self.assertEqual(obs["availability"], "denied")
        self.assertIsNone(obs["contentIdentity"])
        self.assertIsNone(obs["qualificationIdentity"])
        self.assertIsNone(obs["interpretation"])

    def test_whole_read_denied_scrubs_all_identities(self):
        secret_id = "synthetic-trusted:qual/v1"
        m = _valid_measure()
        out = build_intl_owner_result(
            context=_valid_context(),
            generation="g",
            measures={MEASURE_ID: m},
            origins={
                MEASURE_ID: _valid_origin(
                    qualification_identity=secret_id,
                    content_identity="deadbeef" * 8,
                )
            },
            read="denied",
        )
        obs = out["result"]["observations"][0]
        self.assertEqual(obs["availability"], "denied")
        self.assertIsNone(obs["contentIdentity"])
        self.assertIsNone(obs["qualificationIdentity"])
        payload = json.dumps(out, sort_keys=True, default=str)
        self.assertNotIn(secret_id, payload)
        self.assertNotIn("deadbeef" * 8, payload)


# ---------------------------------------------------------------------------
# Whole unavailable never denied
# ---------------------------------------------------------------------------

class TestWholeUnavailableNeverDenied(unittest.TestCase):

    def test_unavailable_whole_read_marks_unavailable(self):
        m = _valid_measure(quality="qualified")  # perfectly good
        out = build_intl_owner_result(
            context=_valid_context(),
            generation="g",
            measures={MEASURE_ID: m},
            origins={
                MEASURE_ID: _valid_origin(
                    qualification_identity="synthetic-trusted:qual/v1"
                )
            },
            read="unavailable",
        )
        self.assertIsNotNone(out["result"])
        obs = out["result"]["observations"][0]
        self.assertEqual(obs["availability"], "unavailable")
        self.assertFalse(obs["qualified"])
        self.assertNotEqual(obs["availability"], "denied")


# ---------------------------------------------------------------------------
# Invalid value shapes
# ---------------------------------------------------------------------------

class TestInvalidValue(unittest.TestCase):

    def test_bool_value_rejected_globally(self):
        out = build_intl_owner_result(
            context=_valid_context(),
            generation="g",
            measures={MEASURE_ID: _valid_measure(value=True)},
        )
        self.assertIsNone(out["result"])
        codes = [d["code"] for d in out["diagnostics"]]
        self.assertIn("invalid_owner_input", codes)

    def test_string_value_rejected_globally(self):
        out = build_intl_owner_result(
            context=_valid_context(),
            generation="g",
            measures={MEASURE_ID: _valid_measure(value="2.50")},
        )
        self.assertIsNone(out["result"])
        codes = [d["code"] for d in out["diagnostics"]]
        self.assertIn("invalid_owner_input", codes)

    def test_nan_rejected_globally(self):
        out = build_intl_owner_result(
            context=_valid_context(),
            generation="g",
            measures={MEASURE_ID: _valid_measure(value=float("nan"))},
        )
        self.assertIsNone(out["result"])
        codes = [d["code"] for d in out["diagnostics"]]
        self.assertIn("invalid_owner_input", codes)

    def test_inf_rejected_globally(self):
        out = build_intl_owner_result(
            context=_valid_context(),
            generation="g",
            measures={MEASURE_ID: _valid_measure(value=float("inf"))},
        )
        self.assertIsNone(out["result"])
        codes = [d["code"] for d in out["diagnostics"]]
        self.assertIn("invalid_owner_input", codes)

    def test_huge_int_marks_unavailable_with_no_leak(self):
        huge = 2 ** 200
        out = build_intl_owner_result(
            context=_valid_context(),
            generation="g",
            measures={MEASURE_ID: _valid_measure(value=huge)},
            origins={
                MEASURE_ID: _valid_origin(
                    qualification_identity="synthetic-trusted:qual/v1"
                )
            },
        )
        # Huge int does NOT collapse the whole result.
        self.assertIsNotNone(out["result"])
        obs = out["result"]["observations"][0]
        self.assertEqual(obs["availability"], "unavailable")
        self.assertFalse(obs["qualified"])
        self.assertIsNone(obs["interpretation"])

        # The huge int value itself never appears in the output envelope.
        payload = json.dumps(out, sort_keys=True, default=str)
        self.assertNotIn(str(huge), payload)
        self.assertNotIn(repr(huge), payload)

        # The content identity is NOT auto-computed for huge ints, but the
        # qualification identity from the origin may be preserved per the
        # general identities rule (metadata here is "allowed").
        idents = ({"content": obs["contentIdentity"], "qualification": obs["qualificationIdentity"]} if obs["contentIdentity"] or obs["qualificationIdentity"] else None)
        if idents is not None:
            self.assertIsNone(obs["contentIdentity"])
            self.assertEqual(
                idents.get("qualification"), "synthetic-trusted:qual/v1"
            )

        # invalid_owner_input is recorded with the measure_id.
        diags_with_measure = [
            d for d in out["diagnostics"] if d["measure_id"] == MEASURE_ID
        ]
        self.assertTrue(diags_with_measure)
        self.assertTrue(
            any(d["code"] == "invalid_owner_input" for d in diags_with_measure)
        )


# ---------------------------------------------------------------------------
# Origin / correction / exclusion
# ---------------------------------------------------------------------------

class TestOriginFlags(unittest.TestCase):

    def test_excluded_propagates_and_blocks_interpretation(self):
        out = build_intl_owner_result(
            context=_valid_context(),
            generation="g",
            measures={MEASURE_ID: _valid_measure()},
            origins={
                MEASURE_ID: _valid_origin(
                    qualification_identity="synthetic-trusted:qual/v1",
                    excluded=True,
                )
            },
        )
        obs = out["result"]["observations"][0]
        self.assertTrue(obs["excluded"])
        self.assertTrue(obs["qualified"])
        # Interpretation is suppressed because excluded==True.
        self.assertIsNone(obs["interpretation"])

    def test_correction_propagates_to_observation(self):
        out = build_intl_owner_result(
            context=_valid_context(),
            generation="g",
            measures={MEASURE_ID: _valid_measure()},
            origins={
                MEASURE_ID: _valid_origin(
                    qualification_identity="synthetic-trusted:qual/v1",
                    correction=True,
                )
            },
        )
        obs = out["result"]["observations"][0]
        self.assertTrue(obs["correction"])

    def test_missing_qualification_identity_keeps_interpretation_none(self):
        # No origin supplied -> no qualification_identity.
        out = build_intl_owner_result(
            context=_valid_context(),
            generation="g",
            measures={MEASURE_ID: _valid_measure()},
            origins=None,
        )
        self.assertIsNotNone(out["result"])
        obs = out["result"]["observations"][0]
        self.assertEqual(obs["availability"], "available")
        self.assertFalse(obs["qualified"])
        self.assertIsNone(obs["interpretation"])
        codes = [d["code"] for d in out["diagnostics"]]
        self.assertIn("missing_qualification_identity", codes)


# ---------------------------------------------------------------------------
# Scope / market mismatch
# ---------------------------------------------------------------------------

class TestMarketScope(unittest.TestCase):

    def test_context_market_mismatch_against_measure_id(self):
        # Context says FED but selected IDs are ECB-prefixed.
        ctx = _valid_context(
            researchMarket="FED",
            selectedMeasureIds=[MEASURE_ID],
        )
        out = build_intl_owner_result(
            context=ctx,
            generation="g",
            measures={MEASURE_ID: _valid_measure()},
        )
        self.assertIsNone(out["result"])
        codes = [d["code"] for d in out["diagnostics"]]
        self.assertIn("invalid_owner_input", codes)

    def test_unselected_measure_payload_rejected(self):
        # Measure payload contains an ID not in selectedMeasureIds.
        out = build_intl_owner_result(
            context=_valid_context(),
            generation="g",
            measures={
                MEASURE_ID: _valid_measure(),
                "ECB.policy.mro": _valid_measure(
                    instrument={
                        "kind": "ecb_policy_rate",
                        "id": "MRO",
                        "market_id": MARKET,
                    }
                ),
            },
        )
        self.assertIsNone(out["result"])
        codes = [d["code"] for d in out["diagnostics"]]
        self.assertIn("invalid_owner_input", codes)


# ---------------------------------------------------------------------------
# Identity stability under content-equivalent variations
# ---------------------------------------------------------------------------

class TestContentIdentityStability(unittest.TestCase):

    @staticmethod
    def _expected_content_id(sid, m):
        canonical = {
            "calculation_at": m["calculation_at"],
            "instrument": m["instrument"],
            "measure_id": sid,
            "observation_at": m["observation_at"],
            "period": m["period"],
            "source_reference": m["source_reference"],
            "unit": m["unit"],
            "value": m["value"],
        }
        domain = b"intl-investigation-owner:content-identity:v1\n"
        payload = domain + json.dumps(
            canonical, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def test_identical_content_with_qual_change_keeps_id(self):
        m1 = _valid_measure(quality="qualified")
        out1 = build_intl_owner_result(
            context=_valid_context(),
            generation="g-1",
            measures={MEASURE_ID: m1},
        )
        ci1 = out1["result"]["observations"][0]["contentIdentity"]
        self.assertEqual(ci1, self._expected_content_id(MEASURE_ID, m1))

        # Same content, quality changed to "stale" with a new generation.
        m2 = _valid_measure(quality="stale", reason="late_refresh")
        out2 = build_intl_owner_result(
            context=_valid_context(),
            generation="g-2",
            measures={MEASURE_ID: m2},
        )
        ci2 = out2["result"]["observations"][0]["contentIdentity"]
        self.assertEqual(ci1, ci2)
        self.assertNotEqual(out1["result"]["generation"],
                             out2["result"]["generation"])

    def test_changed_value_revises_id(self):
        m1 = _valid_measure(value=2.50)
        m2 = _valid_measure(value=2.25)
        out1 = build_intl_owner_result(
            context=_valid_context(),
            generation="g",
            measures={MEASURE_ID: m1},
        )
        out2 = build_intl_owner_result(
            context=_valid_context(),
            generation="g",
            measures={MEASURE_ID: m2},
        )
        ci1 = out1["result"]["observations"][0]["contentIdentity"]
        ci2 = out2["result"]["observations"][0]["contentIdentity"]
        self.assertNotEqual(ci1, ci2)

    def test_changed_observation_at_revises_id(self):
        m1 = _valid_measure(observation_at="2026-10-06")
        m2 = _valid_measure(observation_at="2026-10-07")
        out1 = build_intl_owner_result(
            context=_valid_context(),
            generation="g",
            measures={MEASURE_ID: m1},
        )
        out2 = build_intl_owner_result(
            context=_valid_context(),
            generation="g",
            measures={MEASURE_ID: m2},
        )
        ci1 = out1["result"]["observations"][0]["contentIdentity"]
        ci2 = out2["result"]["observations"][0]["contentIdentity"]
        self.assertNotEqual(ci1, ci2)

    def test_explicit_content_identity_is_preserved(self):
        explicit = "a" * 64
        out = build_intl_owner_result(
            context=_valid_context(),
            generation="g",
            measures={MEASURE_ID: _valid_measure()},
            origins={
                MEASURE_ID: _valid_origin(
                    qualification_identity="synthetic-trusted:qual/v1",
                    content_identity=explicit,
                )
            },
        )
        obs = out["result"]["observations"][0]
        self.assertEqual(obs["contentIdentity"], explicit)


# ---------------------------------------------------------------------------
# Clocks absent -> null with diagnostics
# ---------------------------------------------------------------------------

class TestClocksAbsent(unittest.TestCase):

    def test_clocks_absent_yields_null_envelope(self):
        out = _build({MEASURE_ID: _valid_measure()})
        self.assertEqual(
            out["clocks"],
            {"published_at": None, "source_observed_at": None, "rights_at": None},
        )

    def test_clocks_missing_keys_diagnose_missing_clock(self):
        out = _build(
            {MEASURE_ID: _valid_measure()},
            clocks={"published_at": "2026-10-06T15:15:00+01:00"},
        )
        self.assertEqual(out["clocks"]["published_at"], "2026-10-06T15:15:00+01:00")
        self.assertIsNone(out["clocks"]["source_observed_at"])
        self.assertIsNone(out["clocks"]["rights_at"])
        codes = [d["code"] for d in out["diagnostics"]]
        # At least one diagnostic per missing clock, all "missing_clock".
        missing_clock_diags = [
            d for d in out["diagnostics"] if d["code"] == "missing_clock"
        ]
        self.assertGreaterEqual(len(missing_clock_diags), 2)
        for d in missing_clock_diags:
            self.assertIsNone(d["measure_id"])
            self.assertIn(d["field"], ("source_observed_at", "rights_at"))


# ---------------------------------------------------------------------------
# Detached: inputs are not mutated
# ---------------------------------------------------------------------------

class TestNoInputMutation(unittest.TestCase):

    def test_inputs_not_mutated(self):
        ctx = _valid_context()
        m = _valid_measure()
        ctx_snap = copy.deepcopy(ctx)
        m_snap = copy.deepcopy(m)

        build_intl_owner_result(
            context=ctx,
            generation="g",
            measures={MEASURE_ID: m},
            origins={
                MEASURE_ID: _valid_origin(
                    qualification_identity="synthetic-trusted:qual/v1"
                )
            },
            clocks={"published_at": "2026-10-06T15:15:00+01:00"},
        )
        self.assertEqual(ctx, ctx_snap)
        self.assertEqual(m, m_snap)


# ---------------------------------------------------------------------------
# Zero / negative numeric values
# ---------------------------------------------------------------------------

class TestZeroAndNegative(unittest.TestCase):

    def test_zero_value_accepted(self):
        m = _valid_measure(value=0)
        out = build_intl_owner_result(
            context=_valid_context(),
            generation="g",
            measures={MEASURE_ID: m},
            origins={
                MEASURE_ID: _valid_origin(
                    qualification_identity="synthetic-trusted:qual/v1"
                )
            },
        )
        obs = out["result"]["observations"][0]
        self.assertEqual(obs["availability"], "available")
        self.assertEqual(obs["interpretation"]["value"], 0)
        self.assertIsInstance(obs["interpretation"]["value"], int)

    def test_negative_value_accepted(self):
        m = _valid_measure(value=-3.5)
        out = build_intl_owner_result(
            context=_valid_context(),
            generation="g",
            measures={MEASURE_ID: m},
            origins={
                MEASURE_ID: _valid_origin(
                    qualification_identity="synthetic-trusted:qual/v1"
                )
            },
        )
        obs = out["result"]["observations"][0]
        self.assertEqual(obs["availability"], "available")
        self.assertEqual(obs["interpretation"]["value"], -3.5)


# ---------------------------------------------------------------------------
# No I/O via monkeypatch traps on builtins.open and socket.socket
# ---------------------------------------------------------------------------

class TestNoIO(unittest.TestCase):

    def test_no_io_when_calling(self):
        opened = []
        socked = []

        orig_open = builtins.open
        orig_socket = socket.socket

        def trap_open(*args, **kwargs):
            opened.append((args, kwargs))
            return orig_open(*args, **kwargs)

        def trap_socket(*args, **kwargs):
            socked.append((args, kwargs))
            return orig_socket(*args, **kwargs)

        builtins.open = trap_open
        socket.socket = trap_socket
        try:
            out = build_intl_owner_result(
                context=_valid_context(),
                generation="g",
                measures={
                    MEASURE_ID: _valid_measure(),
                },
                origins={
                    MEASURE_ID: _valid_origin(
                        qualification_identity="synthetic-trusted:qual/v1"
                    ),
                },
                clocks={
                    "published_at": "2026-10-06T15:15:00+01:00",
                    "source_observed_at": "2026-10-06",
                    "rights_at": "2026-10-06T15:30:00+01:00",
                },
            )
        finally:
            builtins.open = orig_open
            socket.socket = orig_socket

        self.assertEqual(opened, [])
        self.assertEqual(socked, [])
        self.assertIsNotNone(out["result"])


# ---------------------------------------------------------------------------
# Module-level invariant: closed Macro field set
# ---------------------------------------------------------------------------

class TestMacroFieldClosure(unittest.TestCase):

    def test_macro_fields_closed_exact_match(self):
        m = _valid_measure()
        self.assertEqual(set(m.keys()), MACRO_FIELDS)

    def test_extra_macro_field_rejected(self):
        m = _valid_measure()
        m["extra_secret_field"] = "should_reject"
        out = build_intl_owner_result(
            context=_valid_context(),
            generation="g",
            measures={MEASURE_ID: m},
        )
        self.assertIsNone(out["result"])
        codes = [d["code"] for d in out["diagnostics"]]
        self.assertIn("invalid_owner_input", codes)


class TestFrozenExportRegressions(unittest.TestCase):
    def test_omitted_membership_unknown_and_exact_observation(self):
        out=build_intl_owner_result(context=_valid_context(),generation="publication",measures={MEASURE_ID:_valid_measure()})
        self.assertEqual(out["result"]["membership"],"unknown")
        self.assertEqual(set(out["result"]["observations"][0]), {"id","availability","qualified","excluded","correction","contentIdentity","qualificationIdentity","interpretation"})
        self.assertNotIn("selectedMeasureIds",out["result"])
    def test_absent_clocks_three_diagnostics(self):
        out=build_intl_owner_result(context=_valid_context(),generation="publication",measures={})
        self.assertEqual(len([x for x in out["diagnostics"] if x["code"]=="missing_clock"]),3)
    def test_malformed_enums_and_clock_containers(self):
        for key in ("read","membership","clocks"):
            for value in ([],[{}],True):
                with self.subTest(key=key,value=value):
                    out=build_intl_owner_result(context=_valid_context(),generation="publication",measures={},**{key:value})
                    self.assertIsNone(out["result"])
    def test_exotic_container_rejected_without_method_call(self):
        class Bad(dict):
            def items(self): raise AssertionError("called custom mapping")
        out=build_intl_owner_result(context=Bad(_valid_context()),generation="publication",measures={})
        self.assertIsNone(out["result"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
