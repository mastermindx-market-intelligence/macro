"""Synthetic bounded Options-owner adapter tests; no live source admission."""

from __future__ import annotations

from dataclasses import replace
import copy
import hashlib
import json
import unittest

from research.options_estate.ptse_contract import build_context
from research.options_estate.ptse_options_observation import (
    OptionsRootBinding,
    adapt_options_hub,
)
from research.options_estate.ptse_owner_observation import (
    OwnerArtifactBinding,
    PTSEOwnerAdapterError,
)


SESSION = "2026-10-02"
DECISION = "2026-10-02T20:00:00Z"
SECURITY = "SEC:US-XNAS-AAPL"
ROOT = "AAPL"


def ref(name: str, owner: str) -> dict:
    return {
        "owner_ref": owner,
        "artifact_id": "fixture:" + name,
        "sha256": hashlib.sha256(name.encode()).hexdigest(),
    }


IDENTITY_REF = ref("AAPL-security-root-binding", "identity-owner")
ROOT_BINDING = OptionsRootBinding(
    root=ROOT,
    security_id=SECURITY,
    identity_ref=IDENTITY_REF,
)


def payload_sha(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def binding(name: str, *, grade="SYNTHETIC", valid_until="2026-10-02T21:00:00Z", payload=None):
    payload = ({"vol": vol, "gex": gex}[name]() if payload is None else payload)
    return OwnerArtifactBinding(
        owner_ref="options-owner",
        artifact_ref={**ref(name, "options-owner"), "sha256": payload_sha(payload)},
        known_at_earliest="2026-10-02T19:58:00Z",
        known_at_latest="2026-10-02T19:58:00Z",
        known_at_precision="EXACT",
        known_at_evidence_ref=ref(name + "-known", "options-owner"),
        economic_time="2026-10-02T19:55:00Z",
        valid_until=valid_until,
        evidence_grade=grade,
        population_ref=IDENTITY_REF,
        instrument_id=SECURITY,
        session_scope="REGULAR",
        calculation_version="fixture:" + name + "-v1",
        limitations=("Synthetic Options fixture; no source or decision authority.",),
    )


def vol() -> dict:
    return {
        "schema": "options_hub.vol/v1",
        "asof": SESSION,
        "root": ROOT,
        "iv_rank_252": 72.5,
        "iv_rank_all": 61.2,
        "coverage_days_all": 812,
        "since_all": "2023-07-03",
        "atm_iv": 34.2,
        "iv_52w_hi": 55.0,
        "iv_52w_lo": 18.1,
        "rv20": 27.4,
        "vrp": 6.8,
        "term": [{"dte": 30, "atm_iv": 34.2}],
        "smile": [{"exp": "2026-11-20", "points": []}],
        "history": [{"date": SESSION, "atm_iv": 34.2}],
        "coverage": {"n_days": 812, "since": "2023-07-03"},
    }


def gex() -> dict:
    return {
        "schema": "options_hub.gex/v1",
        "asof": SESSION,
        "root": ROOT,
        "spot_ref": 292.40,
        "net_gex_bn": 1.25,
        "gamma_flip": 286.0,
        "profile": [{"spot": 280.0, "gex": -0.2}],
        "call_wall": 300.0,
        "put_wall": 280.0,
        "by_strike": [{"strike": 300.0, "gamma_net": 1.0}],
        "by_strike_full_n": 42,
        "by_delta": [{"lo": 0.45, "hi": 0.50}],
        "by_delta_full_n": 120,
        "by_expiry": [{"exp": "2026-10-16", "gamma_net": 1.0}],
        "convention": "dealer-sign per engine/gex_model (long-call/short-put)",
        "coverage": {
            "n_contracts": 120,
            "asof": SESSION,
            "oi_date": "t-1",
            "n_days": 1,
            "since": SESSION,
        },
        "history": [{"date": "2026-10-01", "net_gex_bn": 1.1}],
    }


class PTSEOptionsObservationTest(unittest.TestCase):
    def test_vol_and_gex_payload_changes_cannot_reuse_original_receipt(self):
        for factory, name, field, value in (
            (vol, "vol", "atm_iv", 99), (gex, "gex", "call_wall", 350),
        ):
            with self.subTest(source=name):
                original = factory()
                receipt = binding(name, payload=original)
                changed = copy.deepcopy(original)
                changed[field] = value
                with self.assertRaisesRegex(PTSEOwnerAdapterError, "OWNER_ARTIFACT_REF_MISMATCH"):
                    adapt_options_hub(market_session=SESSION, decision_at=DECISION,
                                      root_binding=ROOT_BINDING,
                                      **{name: changed, name + "_binding": receipt})
                facts = adapt_options_hub(market_session=SESSION, decision_at=DECISION,
                                          root_binding=ROOT_BINDING,
                                          **{name: changed, name + "_binding": binding(name, payload=changed)})
                self.assertEqual(facts[0]["source_artifact_ref"]["sha256"], payload_sha(changed))
                self.assertEqual(receipt.artifact_ref["sha256"], payload_sha(original))

    def test_full_options_payload_including_unprojected_arrays_is_bound(self):
        for factory, name, field in ((vol, "vol", "term"), (gex, "gex", "by_strike")):
            payload = factory()
            receipt = binding(name, payload=payload)
            payload[field] = []
            with self.assertRaisesRegex(PTSEOwnerAdapterError, "OWNER_ARTIFACT_REF_MISMATCH"):
                adapt_options_hub(market_session=SESSION, decision_at=DECISION,
                                  root_binding=ROOT_BINDING,
                                  **{name: payload, name + "_binding": receipt})

    def test_options_payload_key_order_does_not_change_content_binding(self):
        for factory, name in ((vol, "vol"), (gex, "gex")):
            payload = factory()
            reordered = {k: payload[k] for k in reversed(payload)}
            receipt = binding(name, payload=payload)
            kwargs = dict(market_session=SESSION, decision_at=DECISION,
                          root_binding=ROOT_BINDING)
            self.assertEqual(adapt_options_hub(**kwargs, **{name: payload, name + "_binding": receipt}),
                             adapt_options_hub(**kwargs, **{name: reordered, name + "_binding": receipt}))

    def test_annualized_volatility_percent_can_exceed_one_hundred(self):
        payload = vol()
        payload.update(atm_iv=150.0, rv20=125.0)
        facts = adapt_options_hub(market_session=SESSION, decision_at=DECISION,
                                  root_binding=ROOT_BINDING, vol=payload,
                                  vol_binding=binding("vol", payload=payload))
        by_id = {f["feature_id"]: f for f in facts}
        self.assertEqual(by_id["options.vol.atm_iv"]["value"], 150.0)
        self.assertEqual(by_id["options.vol.rv20"]["value"], 125.0)
        self.assertEqual(by_id["options.vol.atm_iv"]["unit"], "PERCENT")
        # Verify the field-specific domain also survives the canonical context
        # contract; it must not merely pass this adapter in isolation.
        from tests.test_ptse_owner_observation import observation, assessment
        from research.options_estate.ptse_contract import validate_context
        o = observation(facts)
        o.update(decision_at=DECISION, issued_at="2026-10-02T20:01:00Z",
                 valid_until="2026-10-02T21:00:00Z")
        a = assessment("options.vol.atm_iv")
        a.update(decision_at=DECISION, issued_at="2026-10-02T20:02:00Z")
        artifact = build_context(o, a)
        validate_context(artifact.canonical_bytes)
        self.assertTrue(all(value is False for value in artifact.to_dict()["assessment"]["authority"].values()))

    def test_volatility_stays_nonnegative_and_ranks_keep_their_upper_bound(self):
        for field, value in (("atm_iv", -1.0), ("rv20", -1.0),
                             ("iv_rank_252", 101), ("iv_rank_all", 101)):
            payload = vol()
            payload[field] = value
            with self.subTest(field=field):
                with self.assertRaisesRegex(PTSEOwnerAdapterError, "OPTIONS_VALUE_RANGE_INVALID"):
                    adapt_options_hub(market_session=SESSION, decision_at=DECISION,
                                      root_binding=ROOT_BINDING, vol=payload,
                                      vol_binding=binding("vol", payload=payload))

    def test_bounded_projection_omits_full_rows_and_research_effects(self):
        facts = adapt_options_hub(
            market_session=SESSION,
            decision_at=DECISION,
            root_binding=ROOT_BINDING,
            vol=vol(),
            vol_binding=binding("vol"),
            gex=gex(),
            gex_binding=binding("gex"),
        )
        ids = {f["feature_id"] for f in facts}
        self.assertEqual(
            ids,
            {
                "options.vol.iv_rank_252",
                "options.vol.iv_rank_all",
                "options.vol.atm_iv",
                "options.vol.rv20",
                "options.vol.coverage_days_all",
                "options.gex.spot_ref",
                "options.gex.gamma_flip",
                "options.gex.call_wall",
                "options.gex.put_wall",
                "options.gex.contract_count",
            },
        )
        self.assertFalse(any("strike" in x or "history" in x for x in ids))
        self.assertFalse(any("bh" in x.lower() or "ic" in x.lower() for x in ids))

    def test_october2_limits_are_carried_not_promoted(self):
        facts = adapt_options_hub(
            market_session=SESSION,
            decision_at=DECISION,
            root_binding=ROOT_BINDING,
            gex=gex(),
            gex_binding=binding("gex"),
        )
        by_id = {f["feature_id"]: f for f in facts}
        text = " ".join(by_id["options.gex.gamma_flip"]["limitations"])
        self.assertIn("realized volatility, not return", text)
        self.assertIn("survived BH only in Era1", text)
        self.assertIn("not measured whole-dealer inventory", text)
        self.assertTrue(all(f["method_kind"] != "GROUNDED_SYNTHESIS" for f in facts))

    def test_vol_research_limits_are_carried_and_history_is_not_exposed(self):
        facts = adapt_options_hub(
            market_session=SESSION,
            decision_at=DECISION,
            root_binding=ROOT_BINDING,
            vol=vol(),
            vol_binding=binding("vol"),
        )
        by_id = {f["feature_id"]: f for f in facts}
        text = " ".join(by_id["options.vol.atm_iv"]["limitations"])
        self.assertIn("retrospective/PIT-unproven", text)
        self.assertIn("inherit none of its BH findings", text)
        self.assertEqual(by_id["options.vol.coverage_days_all"]["unit"], "COUNT")

    def test_null_owner_field_stays_unavailable_not_zero(self):
        payload = vol()
        payload["iv_rank_252"] = None
        facts = adapt_options_hub(
            market_session=SESSION,
            decision_at=DECISION,
            root_binding=ROOT_BINDING,
            vol=payload,
            vol_binding=binding("vol", payload=payload),
        )
        row = {f["feature_id"]: f for f in facts}["options.vol.iv_rank_252"]
        self.assertEqual(row["status"], "UNAVAILABLE")
        self.assertIsNone(row["value"])
        self.assertEqual(row["coverage"], {
            "numerator": 0,
            "denominator": 1,
            "missing_count": 1,
            "population_ref": IDENTITY_REF,
        })

    def test_stale_owner_artifact_is_stale_context(self):
        facts = adapt_options_hub(
            market_session=SESSION,
            decision_at=DECISION,
            root_binding=ROOT_BINDING,
            vol=vol(),
            vol_binding=binding("vol", valid_until="2026-10-02T19:59:00Z"),
        )
        self.assertTrue(all(f["status"] == "STALE" for f in facts))
        self.assertTrue(all(f["null_reason"] == "SOURCE_EXPIRED_AT_DECISION" for f in facts))

    def test_known_at_after_decision_is_refused(self):
        late = replace(
            binding("vol"),
            known_at_earliest="2026-10-02T20:00:01Z",
            known_at_latest="2026-10-02T20:00:01Z",
        )
        with self.assertRaisesRegex(PTSEOwnerAdapterError, "NOT_KNOWN_AT_DECISION"):
            adapt_options_hub(
                market_session=SESSION,
                decision_at=DECISION,
                root_binding=ROOT_BINDING,
                vol=vol(),
                vol_binding=late,
            )

    def test_root_security_and_identity_receipt_are_all_required(self):
        with self.assertRaisesRegex(PTSEOwnerAdapterError, "OPTIONS_ROOT_MISMATCH"):
            adapt_options_hub(
                market_session=SESSION,
                decision_at=DECISION,
                root_binding=replace(ROOT_BINDING, root="MSFT"),
                vol=vol(),
                vol_binding=binding("vol"),
            )
        with self.assertRaisesRegex(PTSEOwnerAdapterError, "OPTIONS_SECURITY_MISMATCH"):
            adapt_options_hub(
                market_session=SESSION,
                decision_at=DECISION,
                root_binding=ROOT_BINDING,
                vol=vol(),
                vol_binding=replace(binding("vol"), instrument_id="SEC:US-XNAS-MSFT"),
            )
        bad_ref = ref("wrong-root-map", "identity-owner")
        with self.assertRaisesRegex(PTSEOwnerAdapterError, "OPTIONS_ROOT_IDENTITY_REF_MISMATCH"):
            adapt_options_hub(
                market_session=SESSION,
                decision_at=DECISION,
                root_binding=replace(ROOT_BINDING, identity_ref=bad_ref),
                vol=vol(),
                vol_binding=binding("vol"),
            )

    def test_schema_session_and_unknown_fields_fail_closed(self):
        payload = vol()
        payload["schema"] = "options_hub.vol/v2"
        with self.assertRaisesRegex(PTSEOwnerAdapterError, "OPTIONS_VOL_SCHEMA_INVALID"):
            adapt_options_hub(
                market_session=SESSION,
                decision_at=DECISION,
                root_binding=ROOT_BINDING,
                vol=payload,
                vol_binding=binding("vol", payload=payload),
            )
        payload = gex()
        payload["asof"] = "2026-10-01"
        with self.assertRaisesRegex(PTSEOwnerAdapterError, "OPTIONS_SESSION_MISMATCH"):
            adapt_options_hub(
                market_session=SESSION,
                decision_at=DECISION,
                root_binding=ROOT_BINDING,
                gex=payload,
                gex_binding=binding("gex", payload=payload),
            )
        payload = vol()
        payload["secret_chain"] = [{"contract": "forbidden"}]
        with self.assertRaisesRegex(PTSEOwnerAdapterError, "OPTIONS_VOL_OBJECT_INVALID"):
            adapt_options_hub(
                market_session=SESSION,
                decision_at=DECISION,
                root_binding=ROOT_BINDING,
                vol=payload,
                vol_binding=binding("vol", payload=payload),
            )

    def test_numeric_ranges_and_gex_convention_fail_closed(self):
        payload = vol()
        payload["iv_rank_252"] = 101
        with self.assertRaisesRegex(PTSEOwnerAdapterError, "OPTIONS_VALUE_RANGE_INVALID"):
            adapt_options_hub(
                market_session=SESSION,
                decision_at=DECISION,
                root_binding=ROOT_BINDING,
                vol=payload,
                vol_binding=binding("vol", payload=payload),
            )
        payload = gex()
        payload["spot_ref"] = -1
        with self.assertRaisesRegex(PTSEOwnerAdapterError, "OPTIONS_VALUE_RANGE_INVALID"):
            adapt_options_hub(
                market_session=SESSION,
                decision_at=DECISION,
                root_binding=ROOT_BINDING,
                gex=payload,
                gex_binding=binding("gex", payload=payload),
            )
        payload = gex()
        payload["convention"] = "measured dealer inventory"
        with self.assertRaisesRegex(PTSEOwnerAdapterError, "OPTIONS_GEX_CONVENTION_INVALID"):
            adapt_options_hub(
                market_session=SESSION,
                decision_at=DECISION,
                root_binding=ROOT_BINDING,
                gex=payload,
                gex_binding=binding("gex", payload=payload),
            )

    def test_payload_binding_pairs_and_at_least_one_options_source(self):
        with self.assertRaisesRegex(PTSEOwnerAdapterError, "OPTIONS_SOURCE_REQUIRED"):
            adapt_options_hub(
                market_session=SESSION,
                decision_at=DECISION,
                root_binding=ROOT_BINDING,
            )
        with self.assertRaisesRegex(PTSEOwnerAdapterError, "OPTIONS_VOL_BINDING_REQUIRED"):
            adapt_options_hub(
                market_session=SESSION,
                decision_at=DECISION,
                root_binding=ROOT_BINDING,
                vol=vol(),
            )


if __name__ == "__main__":
    unittest.main()
