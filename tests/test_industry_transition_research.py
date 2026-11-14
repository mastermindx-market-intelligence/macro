"""Executable safeguards. Synthetic fixtures are not market evidence."""
from copy import deepcopy
from datetime import date
import io
import unittest
import zipfile

import numpy as np
import pandas as pd

from engine.industry_transition_research import BASE_FEATURES, ConditionalModel, feature_panel, label_panel, validate_panel
from engine.prophet_industry_k3e import aggregate_industry_expectations, attach_to_candidates, compare_same_issuers, compose_industry_context, from_revision_frame
from engine.prophet_industry_context_sources import build_board_context, hypothesis_read, taxonomy_membership
from scripts.research.industry_transition_discovery import parse_french


def panel(n=1600, groups=8):
    rng = np.random.default_rng(716)
    dates = pd.bdate_range("1980-01-01", periods=n)
    market = pd.Series(rng.normal(.0003, .011, n), index=dates)
    returns = pd.DataFrame({f"g{k}": (.5 + k / 8) * market + rng.normal(.0001, .009, n) for k in range(groups)}, index=dates)
    return returns, market


def snapshot(ticker="AAA", drift=3., age=1, as_of="2026-11-13", source="2026-11-12"):
    return {"schema": "leader_recovery_expectations.v1", "ticker": ticker, "as_of": as_of,
            "availability": "SOURCE_DATED_OBSERVATIONS", "source_date": source,
            "source_age_sessions": age, "quality_flags": [], "first_seen_qualified": False,
            "readings": {"eps_estimate_change_30d": {"value": drift, "unit": "percent"},
                         "coverage_normalized_net_revisions": {"value": .2, "unit": "ratio"}}}


def membership(as_of="2026-11-13"):
    return {"as_of": as_of, "basis": "reconstructed_static_membership", "source_ref": "fixture:members",
            "members": [{"industry": "Meals", "ticker": "AAA", "issuer_id": "issuer-a"},
                        {"industry": "Meals", "ticker": "BBB", "issuer_id": "issuer-b"}]}


def native_expectation():
    return {"semantic_payload": {"schema": "k3e.declared_capture_inspection.v1",
            "normalized_baseline": {"value": None, "status": "UNAVAILABLE"},
            "query": {"ticker_compat": "AAA", "metric": "eps", "as_of": "2026-11-13T20:00:00Z"},
            "latest_captured_snapshot": {"status": "AVAILABLE"}}}


def revisions():
    return pd.DataFrame([{"ticker": "AAA", "asof": "2026-11-12", "est_chg_30d": 2,
                          "net_up_30d": 1, "n_analysts": 2, "n_covering": 5,
                          "breadth": .5, "breadth_cov": .2}]).set_index("ticker")


class IndustryResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r, cls.m = panel()
        cls.features = feature_panel(cls.r, cls.m, basis="synthetic_fixture", min_industries=4)
        cls.labels = label_panel(cls.features, cls.r, cls.m)
        cls.start = pd.Timestamp("1985-01-01")
        cls.train = cls.labels[cls.labels.label_end < cls.start]
        cls.test = cls.labels[cls.labels.as_of >= cls.start]
        cls.model = ConditionalModel(BASE_FEATURES).fit(cls.train, prediction_start=cls.start)

    def test_input_not_mutated(self):
        before = self.r.copy()
        feature_panel(self.r, self.m, basis="synthetic_fixture", min_industries=4)
        pd.testing.assert_frame_equal(before, self.r)

    def test_prefix_invariance(self):
        cut = self.features.as_of.unique()[-5]
        small = feature_panel(self.r.loc[:cut], self.m.loc[:cut], basis="synthetic_fixture", decision_dates=pd.DatetimeIndex([cut]), min_industries=4)
        pd.testing.assert_frame_equal(small, self.features[self.features.as_of == cut].reset_index(drop=True), check_exact=False, atol=1e-12, rtol=1e-12)

    def test_future_perturbation_cannot_change_past(self):
        cut = self.features.as_of.unique()[-5]
        changed = self.r.copy(); changed.loc[changed.index > cut] *= -2
        out = feature_panel(changed, self.m, basis="synthetic_fixture", min_industries=4)
        pd.testing.assert_frame_equal(self.features[self.features.as_of <= cut].reset_index(drop=True), out[out.as_of <= cut].reset_index(drop=True))

    def test_missing_return_is_not_filled(self):
        cut = self.features.as_of.unique()[-4]
        changed = self.r.copy(); changed.loc[cut, "g0"] = np.nan
        out = feature_panel(changed, self.m, basis="synthetic_fixture", min_industries=4)
        self.assertFalse(((out.as_of == cut) & (out.industry == "g0")).any())

    def test_invalid_session_grid(self):
        with self.assertRaises(ValueError): validate_panel(self.r, self.m.iloc[1:])
        with self.assertRaises(ValueError): validate_panel(self.r.iloc[::-1], self.m.iloc[::-1])

    def test_invalid_evidence_basis(self):
        with self.assertRaises(ValueError): feature_panel(self.r, self.m, basis="historical_data_is_prospective")

    def test_return_below_minus_one_rejected(self):
        broken = self.r.copy(); broken.iloc[10, 0] = -1
        with self.assertRaises(ValueError): validate_panel(broken, self.m)

    def test_label_entry_and_compounding(self):
        row = self.labels.iloc[23]; i = self.r.index.get_loc(row.as_of)
        realized = np.prod(1 + self.r[row.industry].iloc[i + 2:i + 65]) - 1 - .002
        self.assertAlmostEqual(row.net63, realized, places=12)
        self.assertEqual(row.entry_date, self.r.index[i + 1]); self.assertEqual(row.label_end, self.r.index[i + 64])

    def test_outcome_partition(self):
        self.assertTrue((self.labels[["upside_first", "downside_first", "unresolved"]].sum(axis=1) == 1).all())
        self.assertTrue((self.labels.mae63 <= 0).all())

    def test_unfinished_horizon_excluded(self):
        self.assertTrue((self.labels.label_end <= self.r.index.max()).all())
        self.assertLess(len(self.labels), len(self.features))

    def test_model_maturity_and_probability_simplex(self):
        prediction = self.model.predict(self.test)
        self.assertTrue(np.allclose(prediction[["p_upside_first", "p_downside_first", "p_unresolved"]].sum(axis=1), 1))
        self.assertTrue(prediction.p_bad10.between(0, 1).all())
        self.assertFalse(self.model.to_dict()["financial_influence"])
        with self.assertRaises(ValueError): ConditionalModel(BASE_FEATURES).fit(self.labels, prediction_start=self.start)
        with self.assertRaises(ValueError): self.model.predict(self.train)

    def test_model_round_trip(self):
        restored = ConditionalModel.from_dict(self.model.to_dict())
        pd.testing.assert_frame_equal(self.model.predict(self.test), restored.predict(self.test))

    def test_explanation_reconstructs_estimate(self):
        explanation = self.model.explain(self.test.iloc[:3], top_n=2)
        prediction = self.model.predict(self.test.iloc[:3])
        for j, item in enumerate(explanation):
            total = item["intercept"] + item["remaining_contribution"] + sum(x["contribution"] for x in item["terms"])
            self.assertAlmostEqual(total, prediction.expected_excess63.iloc[j], places=12)

    def test_invalid_serialized_model(self):
        for key, value in [("financial_influence", True), ("scale", [0] * 4), ("mean", [float("nan")] * 4)]:
            payload = self.model.to_dict(); payload[key] = value
            with self.assertRaises(ValueError): ConditionalModel.from_dict(payload)

    def test_duplicate_training_rows_rejected(self):
        with self.assertRaises(ValueError): ConditionalModel(BASE_FEATURES).fit(pd.concat([self.train, self.train.iloc[:1]]), prediction_start=self.start)

    def test_parser_cutoff_and_missing_sentinel(self):
        text = "Fixture vintage\n\n Average Value Weighted Returns -- Daily\n,A,B\n20021230,1,-99.99\n20021231,2,3\n20030102,THIS_IS_NOT_A_NUMBER,999\n\n"
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive: archive.writestr("test.csv", text)
        frame, meta = parse_french(stream.getvalue(), cutoff="2002-12-31", kind="industry")
        self.assertEqual(len(frame), 2); self.assertAlmostEqual(frame.iloc[0, 0], .01)
        self.assertTrue(np.isnan(frame.iloc[0, 1])); self.assertEqual(meta["last"], "2002-12-31")


class IndustryK3ETests(unittest.TestCase):
    def test_observed_aggregation_and_coverage(self):
        out = aggregate_industry_expectations(membership(), {"AAA": snapshot(), "BBB": snapshot("BBB", -1)}, as_of="2026-11-13")
        group = out["groups"]["Meals"]
        self.assertEqual(group["eps_positive_share"], .5); self.assertEqual(group["median_eps_change_30d_pct"], 1)
        self.assertFalse(out["financial_influence"]); self.assertIsNone(group["normalized_k3e_revision"])
        self.assertFalse(group["all_first_seen_qualified"])

    def test_missing_not_neutral(self):
        out = aggregate_industry_expectations(membership(), {}, as_of="2026-11-13")
        self.assertIsNone(out["groups"]["Meals"]["median_eps_change_30d_pct"])
        self.assertEqual(out["groups"]["Meals"]["status"], "SPARSE_CONTEXT")

    def test_stale_and_future_exclusion(self):
        out = aggregate_industry_expectations(membership(), {"AAA": snapshot(age=11), "BBB": snapshot("BBB", source="2026-11-14")}, as_of="2026-11-13")
        self.assertEqual(out["groups"]["Meals"]["snapshot_count"], 0)

    def test_exact_cutoff_required(self):
        with self.assertRaises(ValueError): aggregate_industry_expectations(membership(), {}, as_of="2026-11-12")
        out = aggregate_industry_expectations(membership(), {"AAA": snapshot(as_of="2026-11-12")}, as_of="2026-11-13")
        self.assertEqual(out["groups"]["Meals"]["snapshot_count"], 0)

    def test_share_class_deduplication(self):
        members = membership(); members["members"][1]["issuer_id"] = "issuer-a"
        out = aggregate_industry_expectations(members, {"AAA": snapshot(), "BBB": snapshot("BBB")}, as_of="2026-11-13")
        self.assertEqual(out["groups"]["Meals"]["issuer_count"], 1); self.assertEqual(out["groups"]["Meals"]["snapshot_count"], 0)
        members["members"][0]["primary"] = True
        out = aggregate_industry_expectations(members, {"AAA": snapshot(), "BBB": snapshot("BBB")}, as_of="2026-11-13")
        self.assertEqual(out["groups"]["Meals"]["snapshot_count"], 1)

    def test_native_k3e_components_preserved(self):
        native = native_expectation()
        out = aggregate_industry_expectations(membership(), {"AAA": snapshot()}, as_of="2026-11-13", k3e_inputs={"AAA": {"expectation": native}})
        self.assertEqual(out["groups"]["Meals"]["k3e_component_states"], {"EXPECTATION_ONLY": 1, "NOT_REQUESTED": 1})
        native["semantic_payload"]["normalized_baseline"]["value"] = 4
        out = aggregate_industry_expectations(membership(), {"AAA": snapshot()}, as_of="2026-11-13", k3e_inputs={"AAA": {"expectation": native}})
        self.assertEqual(out["groups"]["Meals"]["k3e_component_states"], {"REFUSED": 1, "NOT_REQUESTED": 1})

    def test_native_evidence_does_not_depend_on_legacy_coverage(self):
        out = aggregate_industry_expectations(membership(), {}, as_of="2026-11-13", k3e_inputs={"AAA": {"expectation": native_expectation()}})
        group = out["groups"]["Meals"]
        self.assertEqual(group["snapshot_count"], 0)
        self.assertEqual(group["k3e_component_states"]["EXPECTATION_ONLY"], 1)
        self.assertEqual(len(group["k3e_components"]), 1)

    def test_native_subject_mismatch_rejected(self):
        native = native_expectation(); native["semantic_payload"]["query"]["ticker_compat"] = "OTHER"
        out = aggregate_industry_expectations(membership(), {}, as_of="2026-11-13", k3e_inputs={"AAA": {"expectation": native}})
        self.assertEqual(out["groups"]["Meals"]["k3e_component_states"]["SUBJECT_OR_CUTOFF_MISMATCH"], 1)

    def test_composition_controls_and_no_new_capture(self):
        old = aggregate_industry_expectations(membership("2026-11-12"), {"AAA": snapshot(as_of="2026-11-12", source="2026-11-11")}, as_of="2026-11-12")
        new = aggregate_industry_expectations(membership(), {"AAA": snapshot(drift=5)}, as_of="2026-11-13")
        comparison = compare_same_issuers(old, new, "Meals")
        self.assertEqual(comparison["new_capture_pairs"], 1)
        self.assertEqual(comparison["matched_change_in_reported_30d_drift_pp"], 2)

    def test_real_owner_adapter(self):
        out = from_revision_frame(membership(), revisions(), as_of="2026-11-13", sessions=[date(2026, 11, 12), date(2026, 11, 13)])
        self.assertEqual(out["groups"]["Meals"]["median_eps_change_30d_pct"], 2)

    def test_calendar_gap_and_old_source_not_fresh(self):
        with self.assertRaises(ValueError): from_revision_frame(membership(), revisions(), as_of="2026-11-13", sessions=[date(2026, 11, 11), date(2026, 11, 13)])
        out = from_revision_frame(membership(), revisions(), as_of="2026-11-13", sessions=[date(2026, 11, 13)])
        self.assertEqual(out["groups"]["Meals"]["snapshot_count"], 0)

    def test_candidate_fields_untouched(self):
        expectations = aggregate_industry_expectations(membership(), {"AAA": snapshot()}, as_of="2026-11-13")
        context = compose_industry_context([{"industry": "Meals", "as_of": "2026-11-13", "state": "improving"}], expectations, as_of="2026-11-13")
        original = [{"ticker": "AAA", "industry": "Meals", "as_of": "2026-11-13", "score": 7, "timer": "T1"}]; before = deepcopy(original)
        attached = attach_to_candidates(original, context, as_of="2026-11-13")
        self.assertEqual(original, before); self.assertEqual(attached[0]["score"], 7); self.assertEqual(attached[0]["timer"], "T1")
        self.assertFalse(attached[0]["industry_research_context"]["financial_influence"])
        with self.assertRaises(ValueError): attach_to_candidates(attached, context, as_of="2026-11-13")

    def test_bad_forecast_rejected(self):
        expectations = aggregate_industry_expectations(membership(), {}, as_of="2026-11-13")
        with self.assertRaises(ValueError): compose_industry_context([], expectations, as_of="2026-11-13", model_ref="sha:fixture", model_rows=[{"industry": "Meals", "as_of": "2026-11-13", "p_upside_first": .8, "p_downside_first": .5, "p_unresolved": 0}])

    def test_taxonomy_conflicts_not_silently_chosen(self):
        frame = pd.DataFrame([{"ticker": "AAA", "region": "USA", "gics_industry": "Meals"}, {"ticker": "AAA", "region": "USA", "gics_industry": "Other"}])
        members, mapping, diagnostic = taxonomy_membership(frame, as_of="2026-11-13", source_ref="fixture", allowed_industries={"Meals", "Other"})
        self.assertEqual(members["members"], []); self.assertEqual(mapping, {}); self.assertEqual(diagnostic["ambiguous_tickers"], ["AAA"])

    def test_native_board_consumer_preserves_every_field(self):
        board = {"as_of": "2026-11-13", "rank_by": "us_prophet_v3", "gate_go": False,
                 "buy": [{"ticker": "AAA", "score": 88, "signal": {"tier": "T1"}}], "watch": [{"ticker": "UNKNOWN", "score": 55}]}
        ranks = {"schema": "stage_industry_ranks.v1", "asof": "2026-11-13", "regions": {"USA": [{"industry_id": "Meals", "bucket": "Leading", "rank": 1}]}}
        taxonomy = pd.DataFrame([{"ticker": "AAA", "region": "USA", "gics_industry": "Meals"}])
        before = deepcopy(board)
        result = build_board_context(board, ranks, taxonomy, revisions(), source_refs={k: "fixture:" + k for k in ("board", "industry_ranks", "taxonomy", "revisions")})
        self.assertEqual(board, before); self.assertTrue(result["preserved_native_board"])
        self.assertEqual(result["coverage"], {"board_rows": 2, "matched_industry_rows": 1})
        self.assertEqual(result["board"]["buy"][0]["signal"], {"tier": "T1"})
        self.assertIsNone(result["context"]["groups"]["Meals"]["forecast"])

    def test_negative_revisions_not_automatic_veto(self):
        read = hypothesis_read({"state": "improving"}, {"status": "OBSERVED_RESEARCH_CONTEXT", "eps_drift_coverage": .8, "median_eps_change_30d_pct": -2})
        self.assertEqual(read["pattern"], "RECOVERY_DESPITE_NEGATIVE_REVISIONS")
        self.assertNotIn("buy", read); self.assertNotIn("veto", read)


if __name__ == "__main__":
    unittest.main()
